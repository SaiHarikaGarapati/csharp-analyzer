"""
Incremental analysis engine combining git changes and caching.

This module orchestrates:
1. Detect changed files using Git
2. Check cache for unchanged files
3. Analyze only changed files
4. Combine cached and fresh findings
5. Update cache with new results
"""

import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from .git_utils import GitUtils
from .cache import AnalysisCache
from .rules import RulesEngine


class IncrementalAnalyzer:
    """
    Incremental analyzer that combines git tracking and caching.
    
    Usage:
        >>> incremental = IncrementalAnalyzer(".")
        >>> findings = incremental.analyze(since="main", until="HEAD")
        >>> print(f"Found {len(findings)} issues (with caching)")
    """
    
    def __init__(self, repo_path: str = ".", 
                 cache_path: str = ".csharp-analyzer/cache.db",
                 rules_directory: Optional[str] = None):
        """
        Initialize incremental analyzer.
        
        Args:
            repo_path: Path to git repository
            cache_path: Path to SQLite cache database
            rules_directory: Path to rules YAML directory
            
        Raises:
            ValueError: If repo_path is not a valid git repository
        """
        self.repo_path = Path(repo_path)
        self.git = GitUtils(str(self.repo_path))
        self.cache = AnalysisCache(cache_path)
        self.rules_engine = RulesEngine(rules_directory)
        self._rules_hash = self._calculate_rules_hash()
    
    def _calculate_rules_hash(self) -> str:
        """
        Calculate hash of current rules configuration.
        
        Used to invalidate cache when rules change.
        
        Returns:
            SHA256 hash of rules
        """
        # Combine all rule IDs and configs
        rule_str = ""
        for rule in self.rules_engine.rules:
            rule_str += f"{rule.id}:{rule.type.value}:{rule.config}"
        
        return hashlib.sha256(rule_str.encode()).hexdigest()
    
    def analyze(self, since: str = "HEAD~1", until: str = "HEAD",
               use_cache: bool = True, unstaged: bool = False) -> List:
        """
        Analyze only changed files, using cache for unchanged files.
        
        Args:
            since: Git reference for comparison start
            until: Git reference for comparison end
            use_cache: Whether to use cached results
            unstaged: If True, analyze unstaged changes instead of committed
            
        Returns:
            List of Finding objects (from both fresh analysis and cache)
            
        Example:
            >>> incremental = IncrementalAnalyzer(".")
            >>> findings = incremental.analyze(since="main")
            >>> print(f"Found {len(findings)} issues")
        """
        # Step 1: Get changed files
        if unstaged:
            changed_files = self.git.get_unstaged_changes()
        else:
            changed_files = self.git.get_changed_files(since, until)
        
        if not changed_files:
            print("ℹ️  No C# files changed")
            return []
        
        print(f"📝 Found {len(changed_files)} changed files")
        
        # Step 2: Analyze each file
        all_findings = []
        cache_hits = 0
        cache_misses = 0
        
        for file_path in changed_files:
            full_path = self.repo_path / file_path
            
            if not full_path.exists():
                # File was deleted
                self.cache.invalidate_file(file_path)
                continue
            
            # Calculate file hash
            file_hash = self.git.get_file_hash(file_path)
            
            # Try to get from cache
            if use_cache:
                cached = self.cache.get_results(file_path, self._rules_hash)
                
                if cached and cached["file_hash"] == file_hash:
                    # Cache hit - file unchanged
                    cache_hits += 1
                    all_findings.extend(cached["findings"])
                    continue
            
            # Cache miss - analyze file
            cache_misses += 1
            try:
                code = full_path.read_text(encoding='utf-8')
                findings = self.rules_engine.analyze(code, file_path)
                
                # Save to cache
                if use_cache:
                    self.cache.save_results(
                        file_path,
                        findings,
                        file_hash,
                        self._rules_hash
                    )
                
                all_findings.extend(findings)
            
            except Exception as e:
                print(f"⚠️  Error analyzing {file_path}: {e}")
        
        # Step 3: Print cache statistics
        if use_cache:
            print(f"✓ Cache: {cache_hits} hits, {cache_misses} misses")
        
        return all_findings
    
    def analyze_unstaged(self, use_cache: bool = True) -> List:
        """
        Analyze unstaged (modified but not committed) files.
        
        Args:
            use_cache: Whether to use cached results
            
        Returns:
            List of Finding objects
            
        Example:
            >>> incremental = IncrementalAnalyzer(".")
            >>> findings = incremental.analyze_unstaged()
            >>> print(f"Found {len(findings)} issues in unstaged changes")
        """
        return self.analyze(unstaged=True, use_cache=use_cache)
    
    def analyze_branch_diff(self, base_branch: str = "main",
                           current_branch: Optional[str] = None,
                           use_cache: bool = True) -> List:
        """
        Analyze changes between two branches (e.g., for pull requests).
        
        Args:
            base_branch: Base branch to compare against
            current_branch: Current branch (default: HEAD)
            use_cache: Whether to use cached results
            
        Returns:
            List of Finding objects
            
        Example:
            >>> incremental = IncrementalAnalyzer(".")
            >>> findings = incremental.analyze_branch_diff("main", "feature/new-auth")
            >>> print(f"PR introduces {len(findings)} issues")
        """
        current = current_branch or "HEAD"
        return self.analyze(since=base_branch, until=current, use_cache=use_cache)
    
    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache info
            
        Example:
            >>> incremental = IncrementalAnalyzer(".")
            >>> stats = incremental.get_cache_stats()
            >>> print(f"Cache size: {stats['cache_size_kb']} KB")
        """
        return self.cache.get_cache_stats()
    
    def clear_cache(self) -> None:
        """
        Clear entire cache (useful when rules change).
        
        Example:
            >>> incremental = IncrementalAnalyzer(".")
            >>> incremental.clear_cache()
        """
        self.cache.invalidate_all()
        print("✓ Cache cleared")
    
    def save_checkpoint(self, commit_hash: Optional[str] = None) -> None:
        """
        Save a checkpoint (for tracking last analysis).
        
        Args:
            commit_hash: Commit hash to save (default: current HEAD)
            
        Example:
            >>> incremental = IncrementalAnalyzer(".")
            >>> incremental.analyze(since="main")
            >>> incremental.save_checkpoint()  # Mark as analyzed
        """
        if not commit_hash:
            commit_hash = self.git.get_last_commit_hash()
        
        self.cache.set_metadata("last_analyzed_commit", commit_hash)
        self.cache.set_metadata("last_analyzed_at", datetime.now().isoformat())
    
    def get_last_checkpoint(self) -> Optional[Tuple[str, str]]:
        """
        Get last analysis checkpoint.
        
        Returns:
            Tuple of (commit_hash, timestamp) or None if no checkpoint
            
        Example:
            >>> incremental = IncrementalAnalyzer(".")
            >>> last_hash, last_time = incremental.get_last_checkpoint()
            >>> print(f"Last analyzed: {last_hash} at {last_time}")
        """
        commit_hash = self.cache.get_metadata("last_analyzed_commit")
        timestamp = self.cache.get_metadata("last_analyzed_at")
        
        if commit_hash and timestamp:
            return (commit_hash, timestamp)
        
        return None
    
    def __enter__(self):
        """Context manager support."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.cache.close()
