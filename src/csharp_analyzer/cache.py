"""
SQLite-based caching for analysis results.

This module caches analysis findings to avoid re-analyzing unchanged files.
Cache is invalidated when:
- File content changes (detected by hash)
- Rules change
- Cache is manually cleared
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import asdict


class AnalysisCache:
    """SQLite-based cache for storing analysis results."""
    
    def __init__(self, cache_path: str = ".csharp-analyzer/cache.db"):
        """
        Initialize cache with SQLite database.
        
        Args:
            cache_path: Path to SQLite database file
            
        Example:
            >>> cache = AnalysisCache()
            >>> # Cache initialized at .csharp-analyzer/cache.db
        """
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create database connection
        self.conn = sqlite3.connect(str(self.cache_path))
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self._init_schema()
    
    def _init_schema(self):
        """Create tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Main cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT NOT NULL,
                rules_hash TEXT NOT NULL,
                findings JSON NOT NULL,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        # Ensure metadata table has schema version
        cursor.execute(
            "INSERT OR IGNORE INTO metadata (key, value) VALUES ('schema_version', '1')"
        )
        
        self.conn.commit()
    
    def save_results(self, file_path: str, findings: List, 
                    file_hash: str, rules_hash: str) -> None:
        """
        Save analysis results to cache.
        
        Args:
            file_path: Relative path to C# file
            findings: List of Finding objects to cache
            file_hash: SHA256 hash of file content
            rules_hash: SHA256 hash of rules configuration
            
        Example:
            >>> cache = AnalysisCache()
            >>> cache.save_results(
            ...     "src/UserService.cs",
            ...     findings=[Finding(rule_id="high-complexity", ...)],
            ...     file_hash="abc123...",
            ...     rules_hash="def456..."
            ... )
        """
        cursor = self.conn.cursor()
        
        # Convert findings to JSON-serializable format
        findings_list = []
        for f in findings:
            if hasattr(f, '__dataclass_fields__'):
                # Convert Finding dataclass to dict
                finding_dict = asdict(f)
                # Convert Severity enum to string
                if hasattr(finding_dict.get('severity'), 'value'):
                    finding_dict['severity'] = finding_dict['severity'].value
                findings_list.append(finding_dict)
            else:
                findings_list.append(f)
        
        findings_json = json.dumps(findings_list)
        
        # Insert or replace (upsert)
        cursor.execute("""
            INSERT OR REPLACE INTO file_cache 
            (file_path, file_hash, rules_hash, findings, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (file_path, file_hash, rules_hash, findings_json))
        
        self.conn.commit()
    
    def get_results(self, file_path: str, rules_hash: str) -> Optional[Dict]:
        """
        Retrieve cached results for a file.
        
        Args:
            file_path: Relative path to C# file
            rules_hash: Current rules hash to validate cache
            
        Returns:
            Cache entry dict with "findings" and "file_hash", or None if not found
            
        Example:
            >>> cache = AnalysisCache()
            >>> cached = cache.get_results("src/UserService.cs", rules_hash="def456...")
            >>> if cached:
            ...     findings = cached["findings"]
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT file_hash, findings FROM file_cache 
            WHERE file_path = ? AND rules_hash = ?
        """, (file_path, rules_hash))
        
        row = cursor.fetchone()
        
        if row:
            return {
                "file_hash": row[0],
                "findings": json.loads(row[1])
            }
        
        return None
    
    def get_file_cache_entry(self, file_path: str) -> Optional[Dict]:
        """
        Get raw cache entry for a file (regardless of rules hash).
        
        Args:
            file_path: Relative path to C# file
            
        Returns:
            Cache entry dict with all fields, or None if not found
            
        Example:
            >>> cache = AnalysisCache()
            >>> entry = cache.get_file_cache_entry("src/UserService.cs")
            >>> if entry:
            ...     print(f"Cached at: {entry['analyzed_at']}")
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT file_hash, rules_hash, findings, analyzed_at, updated_at 
            FROM file_cache 
            WHERE file_path = ?
        """, (file_path,))
        
        row = cursor.fetchone()
        
        if row:
            return {
                "file_hash": row[0],
                "rules_hash": row[1],
                "findings": json.loads(row[2]),
                "analyzed_at": row[3],
                "updated_at": row[4]
            }
        
        return None
    
    def invalidate_file(self, file_path: str) -> None:
        """
        Remove cache entry for a specific file.
        
        Args:
            file_path: Relative path to C# file
            
        Example:
            >>> cache = AnalysisCache()
            >>> cache.invalidate_file("src/UserService.cs")
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM file_cache WHERE file_path = ?", (file_path,))
        self.conn.commit()
    
    def invalidate_all(self) -> None:
        """
        Clear entire cache (useful when rules change).
        
        Example:
            >>> cache = AnalysisCache()
            >>> cache.invalidate_all()  # Called when rules are updated
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM file_cache")
        self.conn.commit()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache info:
            {
                "total_cached_files": 150,
                "cache_size_kb": 512,
                "oldest_entry": "2026-05-01 10:30:00"
            }
            
        Example:
            >>> cache = AnalysisCache()
            >>> stats = cache.get_cache_stats()
            >>> print(f"Cached files: {stats['total_cached_files']}")
        """
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM file_cache")
        count = cursor.fetchone()[0]
        
        cursor.execute("SELECT MIN(analyzed_at) FROM file_cache")
        oldest = cursor.fetchone()[0]
        
        size_bytes = self.cache_path.stat().st_size if self.cache_path.exists() else 0
        
        return {
            "total_cached_files": count,
            "cache_size_kb": round(size_bytes / 1024, 2),
            "oldest_entry": oldest
        }
    
    def set_metadata(self, key: str, value: str) -> None:
        """
        Store metadata (like last analyzed commit).
        
        Args:
            key: Metadata key
            value: Metadata value
            
        Example:
            >>> cache = AnalysisCache()
            >>> cache.set_metadata("last_commit", "abc123def456...")
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO metadata (key, value) 
            VALUES (?, ?)
        """, (key, value))
        self.conn.commit()
    
    def get_metadata(self, key: str) -> Optional[str]:
        """
        Retrieve metadata value.
        
        Args:
            key: Metadata key
            
        Returns:
            Metadata value or None if not found
            
        Example:
            >>> cache = AnalysisCache()
            >>> last_commit = cache.get_metadata("last_commit")
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        """Context manager support."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.close()
