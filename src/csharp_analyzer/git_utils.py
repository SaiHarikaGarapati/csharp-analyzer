"""
Git utilities for tracking file changes and metadata.

This module provides wrappers around GitPython to:
- Get list of changed files since a reference point
- Calculate file hashes for change detection
- Retrieve commit metadata
- Initialize git tracking
"""

import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from git import Repo, GitCommandError
from datetime import datetime


class GitUtils:
    """Wrapper around GitPython for git operations."""
    
    def __init__(self, repo_path: str):
        """
        Initialize GitUtils with a repository path.
        
        Args:
            repo_path: Path to git repository root
            
        Raises:
            ValueError: If path is not a valid git repository
        """
        try:
            self.repo = Repo(repo_path)
            self.repo_path = Path(repo_path)
        except Exception as e:
            raise ValueError(f"Invalid git repository: {repo_path}") from e
    
    def get_changed_files(self, since: str = "HEAD~1", 
                         until: str = "HEAD") -> List[str]:
        """
        Get list of changed C# files between two references.
        
        Args:
            since: Starting commit/branch reference (default: previous commit)
            until: Ending commit/branch reference (default: current HEAD)
            
        Returns:
            List of relative paths to changed .cs files
            
        Example:
            >>> git = GitUtils(".")
            >>> git.get_changed_files("main", "develop")
            ["src/UserService.cs", "tests/UserServiceTests.cs"]
        """
        try:
            # Get diff between two references
            diffs = self.repo.commit(since).diff(until)
            
            changed_files = []
            for diff in diffs:
                # diff.b_path is the target file path (after the change)
                file_path = diff.b_path or diff.a_path
                
                # Filter only C# files
                if file_path and file_path.endswith(".cs"):
                    changed_files.append(file_path)
            
            return changed_files
        
        except GitCommandError as e:
            raise ValueError(f"Invalid git reference: {since}..{until}") from e
    
    def get_unstaged_changes(self) -> List[str]:
        """
        Get list of unstaged (modified but not committed) C# files.
        
        Returns:
            List of relative paths to modified .cs files
            
        Example:
            >>> git = GitUtils(".")
            >>> git.get_unstaged_changes()
            ["src/UserService.cs"]
        """
        unstaged = []
        
        # Get untracked and modified files
        for item in self.repo.index.diff(None):
            file_path = item.a_path
            if file_path and file_path.endswith(".cs"):
                unstaged.append(file_path)
        
        return unstaged
    
    def get_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA256 hash of a file's content.
        
        Used to detect if a file has actually changed (by content, not just timestamp).
        
        Args:
            file_path: Path to file (relative to repo root)
            
        Returns:
            SHA256 hash of file content
            
        Example:
            >>> git = GitUtils(".")
            >>> hash1 = git.get_file_hash("src/UserService.cs")
            >>> # After editing the file
            >>> hash2 = git.get_file_hash("src/UserService.cs")
            >>> hash1 != hash2  # True if content changed
        """
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            return ""
        
        sha256 = hashlib.sha256()
        with open(full_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def get_commit_info(self, ref: str = "HEAD") -> Dict[str, str]:
        """
        Get metadata about a specific commit.
        
        Args:
            ref: Git reference (commit, branch, tag)
            
        Returns:
            Dictionary with commit info:
            {
                "hash": "abc123...",
                "author": "John Doe",
                "message": "Initial commit",
                "timestamp": "2026-05-04 10:30:00",
                "files_changed": 5
            }
            
        Example:
            >>> git = GitUtils(".")
            >>> info = git.get_commit_info("HEAD")
            >>> print(info["message"])
        """
        try:
            commit = self.repo.commit(ref)
            
            return {
                "hash": commit.hexsha[:7],  # Short hash
                "author": commit.author.name,
                "message": commit.message.strip(),
                "timestamp": datetime.fromtimestamp(commit.committed_date).isoformat(),
                "files_changed": len(commit.stats.files)
            }
        except GitCommandError as e:
            raise ValueError(f"Invalid git reference: {ref}") from e
    
    def get_branch_name(self) -> str:
        """
        Get current branch name.
        
        Returns:
            Current branch name (e.g., "main", "develop")
            
        Example:
            >>> git = GitUtils(".")
            >>> git.get_branch_name()
            "main"
        """
        try:
            return self.repo.active_branch.name
        except TypeError:
            # Detached HEAD state
            return self.repo.head.commit.hexsha[:7]
    
    def get_tags(self) -> List[str]:
        """
        Get all git tags in repository.
        
        Returns:
            List of tag names sorted chronologically
            
        Example:
            >>> git = GitUtils(".")
            >>> git.get_tags()
            ["v0.1.0", "v0.2.0", "v0.3.0"]
        """
        try:
            # Sort by commit date (newest first)
            tags = sorted(
                self.repo.tags,
                key=lambda t: t.commit.committed_date,
                reverse=True
            )
            return [tag.name for tag in tags]
        except Exception:
            return []
    
    def is_clean(self) -> bool:
        """
        Check if repository has uncommitted changes.
        
        Returns:
            True if all changes are committed, False otherwise
            
        Example:
            >>> git = GitUtils(".")
            >>> git.is_clean()
            True  # No uncommitted changes
        """
        return not self.repo.is_dirty() and not self.repo.untracked_files
    
    def get_last_commit_hash(self) -> str:
        """
        Get hash of HEAD commit.
        
        Returns:
            Full commit hash of HEAD
            
        Example:
            >>> git = GitUtils(".")
            >>> git.get_last_commit_hash()
            "abc123def456..."
        """
        return self.repo.head.commit.hexsha
