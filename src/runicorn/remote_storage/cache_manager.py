"""
Local Cache Manager

Manages local cache for remote metadata and files with SQLite indexing.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import CachedFile, RemoteStorageStats

logger = logging.getLogger(__name__)


class LocalCacheManager:
    """
    Local cache manager with SQLite indexing.
    
    Responsibilities:
    1. Manage local cache directory structure
    2. Provide fast metadata queries via SQLite
    3. Implement LRU eviction for disk space management
    4. Track cached files and their freshness
    
    Directory structure:
    cache_dir/
    ├── index.db              # SQLite index database
    ├── metadata/             # Cached metadata files
    │   ├── artifacts/        # Artifact metadata
    │   │   ├── model/
    │   │   ├── dataset/
    │   │   └── ...
    │   └── experiments/      # Experiment metadata
    └── downloads/            # Downloaded artifact files
        ├── artifact1/
        └── artifact2/
    """
    
    def __init__(self, cache_dir: Path, max_cache_size_gb: float = 10.0):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Root directory for cache storage
            max_cache_size_gb: Maximum cache size in GB (default: 10GB)
        """
        self.cache_dir = Path(cache_dir)
        self.max_cache_size_bytes = int(max_cache_size_gb * 1024 * 1024 * 1024)
        
        # Create directory structure
        self.metadata_dir = self.cache_dir / "metadata"
        self.downloads_dir = self.cache_dir / "downloads"
        self.index_db_path = self.cache_dir / "index.db"
        
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initialize database
        self._init_database()
        
        logger.info(f"Cache manager initialized: {self.cache_dir}")
    
    def _init_database(self):
        """Initialize SQLite database schema."""
        conn = self._get_connection()
        try:
            # Artifacts metadata index
            conn.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    size_bytes INTEGER DEFAULT 0,
                    num_files INTEGER DEFAULT 0,
                    created_at REAL,
                    updated_at REAL,
                    last_synced REAL,
                    metadata_path TEXT,
                    manifest_path TEXT,
                    PRIMARY KEY (name, type, version)
                )
            """)
            
            # Cached files index
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cached_files (
                    remote_path TEXT PRIMARY KEY,
                    local_path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    remote_mtime REAL NOT NULL,
                    cached_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    checksum TEXT
                )
            """)
            
            # Download tasks tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS download_tasks (
                    task_id TEXT PRIMARY KEY,
                    artifact_name TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    artifact_version INTEGER NOT NULL,
                    target_dir TEXT NOT NULL,
                    total_files INTEGER DEFAULT 0,
                    downloaded_files INTEGER DEFAULT 0,
                    total_bytes INTEGER DEFAULT 0,
                    downloaded_bytes INTEGER DEFAULT 0,
                    started_at REAL NOT NULL,
                    completed_at REAL,
                    status TEXT DEFAULT 'running',
                    error TEXT
                )
            """)
            
            # Cache statistics
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_stats (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            
            # Create indexes for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_artifacts_type 
                ON artifacts(type)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_artifacts_updated 
                ON artifacts(updated_at DESC)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cached_files_accessed 
                ON cached_files(last_accessed ASC)
            """)
            
            conn.commit()
            logger.debug("Database schema initialized")
            
        finally:
            conn.close()
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get SQLite database connection.
        
        Returns:
            Database connection with row factory configured
        """
        conn = sqlite3.connect(str(self.index_db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ==================== Artifact Metadata Management ====================
    
    def cache_artifact_metadata(
        self,
        name: str,
        type: str,
        version: int,
        metadata: Dict[str, Any],
        manifest: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Cache artifact metadata to local storage.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Artifact version
            metadata: Artifact metadata dictionary
            manifest: Optional artifact manifest dictionary
        """
        with self._lock:
            # Create metadata directory structure
            metadata_dir = self.metadata_dir / "artifacts" / type / name / f"v{version}"
            metadata_dir.mkdir(parents=True, exist_ok=True)
            
            # Save metadata.json
            metadata_path = metadata_dir / "metadata.json"
            metadata_path.write_text(
                json.dumps(metadata, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            
            # Save manifest.json if provided
            manifest_path = None
            if manifest:
                manifest_path = metadata_dir / "manifest.json"
                manifest_path.write_text(
                    json.dumps(manifest, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
            
            # Update database index
            conn = self._get_connection()
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO artifacts (
                        name, type, version, size_bytes, num_files,
                        created_at, updated_at, last_synced,
                        metadata_path, manifest_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name, type, version,
                    metadata.get("size_bytes", 0),
                    metadata.get("num_files", 0),
                    metadata.get("created_at", time.time()),
                    metadata.get("updated_at", time.time()),
                    time.time(),
                    str(metadata_path),
                    str(manifest_path) if manifest_path else None
                ))
                conn.commit()
                logger.debug(f"Cached metadata for {name}:v{version}")
            finally:
                conn.close()
    
    def get_artifact_metadata(
        self,
        name: str,
        type: str,
        version: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached artifact metadata.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Artifact version
            
        Returns:
            Metadata dictionary or None if not cached
        """
        with self._lock:
            metadata_path = (
                self.metadata_dir / "artifacts" / type / name / 
                f"v{version}" / "metadata.json"
            )
            
            if not metadata_path.exists():
                return None
            
            try:
                return json.loads(metadata_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to read metadata from {metadata_path}: {e}")
                return None
    
    def get_artifact_manifest(
        self,
        name: str,
        type: str,
        version: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached artifact manifest.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Artifact version
            
        Returns:
            Manifest dictionary or None if not cached
        """
        with self._lock:
            manifest_path = (
                self.metadata_dir / "artifacts" / type / name / 
                f"v{version}" / "manifest.json"
            )
            
            if not manifest_path.exists():
                return None
            
            try:
                return json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to read manifest from {manifest_path}: {e}")
                return None
    
    def list_artifacts(
        self,
        type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List cached artifacts (aggregated by name).
        
        Args:
            type: Optional artifact type filter
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of artifact summary dictionaries
            Each entry represents one artifact with:
            - name: Artifact name
            - type: Artifact type
            - num_versions: Total number of versions
            - latest_version: Latest version number
            - size_bytes: Size of latest version
            - created_at: Creation time of first version
            - updated_at: Update time of latest version
        """
        conn = self._get_connection()
        try:
            # Aggregate by name and type, get version stats
            if type:
                cursor = conn.execute("""
                    SELECT 
                        name,
                        type,
                        COUNT(*) as num_versions,
                        MAX(version) as latest_version,
                        MAX(size_bytes) as size_bytes,
                        MIN(created_at) as created_at,
                        MAX(updated_at) as updated_at,
                        MAX(last_synced) as last_synced
                    FROM artifacts
                    WHERE type = ?
                    GROUP BY name, type
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                """, (type, limit, offset))
            else:
                cursor = conn.execute("""
                    SELECT 
                        name,
                        type,
                        COUNT(*) as num_versions,
                        MAX(version) as latest_version,
                        MAX(size_bytes) as size_bytes,
                        MIN(created_at) as created_at,
                        MAX(updated_at) as updated_at,
                        MAX(last_synced) as last_synced
                    FROM artifacts
                    GROUP BY name, type
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            results = []
            for row in cursor.fetchall():
                artifact_dict = dict(row)
                # Convert to match ArtifactStorage.list_artifacts() format
                artifact_dict['aliases'] = {}  # Will be loaded from versions.json if needed
                results.append(artifact_dict)
            
            return results
            
        finally:
            conn.close()
    
    def list_artifact_versions(
        self,
        name: str,
        type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all cached versions of an artifact.
        
        Args:
            name: Artifact name
            type: Optional artifact type filter
            
        Returns:
            List of version information dictionaries
        """
        conn = self._get_connection()
        try:
            if type:
                cursor = conn.execute("""
                    SELECT version, size_bytes, num_files, created_at, last_synced
                    FROM artifacts
                    WHERE name = ? AND type = ?
                    ORDER BY version DESC
                """, (name, type))
            else:
                cursor = conn.execute("""
                    SELECT version, size_bytes, num_files, created_at, last_synced
                    FROM artifacts
                    WHERE name = ?
                    ORDER BY version DESC
                """, (name,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    # ==================== Cached Files Management ====================
    
    def cache_file(self, cached_file: CachedFile) -> None:
        """
        Register a cached file in the index.
        
        Args:
            cached_file: CachedFile object with file metadata
        """
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO cached_files (
                        remote_path, local_path, size_bytes, remote_mtime,
                        cached_at, last_accessed, checksum
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    cached_file.remote_path,
                    cached_file.local_path,
                    cached_file.size_bytes,
                    cached_file.remote_mtime,
                    cached_file.cached_at,
                    cached_file.last_accessed,
                    cached_file.checksum
                ))
                conn.commit()
                logger.debug(f"Cached file registered: {cached_file.remote_path}")
            finally:
                conn.close()
    
    def get_cached_file(self, remote_path: str) -> Optional[CachedFile]:
        """
        Get cached file metadata.
        
        Args:
            remote_path: Remote file path
            
        Returns:
            CachedFile object or None if not cached
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM cached_files WHERE remote_path = ?
            """, (remote_path,))
            
            row = cursor.fetchone()
            if row:
                return CachedFile.from_dict(dict(row))
            return None
            
        finally:
            conn.close()
    
    def update_file_access(self, remote_path: str) -> None:
        """
        Update last accessed time for a cached file.
        
        Args:
            remote_path: Remote file path
        """
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("""
                    UPDATE cached_files 
                    SET last_accessed = ?
                    WHERE remote_path = ?
                """, (time.time(), remote_path))
                conn.commit()
            finally:
                conn.close()
    
    # ==================== Cache Cleanup ====================
    
    def cleanup_old_files(self) -> int:
        """
        Clean up old cached files using LRU strategy.
        
        Removes least recently accessed files until cache size is within limit.
        
        Returns:
            Number of files cleaned up
        """
        with self._lock:
            current_size = self.get_cache_size()
            
            if current_size <= self.max_cache_size_bytes:
                return 0  # No cleanup needed
            
            bytes_to_free = current_size - self.max_cache_size_bytes
            cleaned_count = 0
            freed_bytes = 0
            
            conn = self._get_connection()
            try:
                # Get files ordered by last access (LRU)
                cursor = conn.execute("""
                    SELECT remote_path, local_path, size_bytes
                    FROM cached_files
                    ORDER BY last_accessed ASC
                """)
                
                for row in cursor:
                    if freed_bytes >= bytes_to_free:
                        break
                    
                    remote_path = row['remote_path']
                    local_path = Path(row['local_path'])
                    size_bytes = row['size_bytes']
                    
                    # Delete file
                    if local_path.exists():
                        try:
                            local_path.unlink()
                            freed_bytes += size_bytes
                            cleaned_count += 1
                            logger.debug(f"Cleaned up cached file: {remote_path}")
                        except Exception as e:
                            logger.error(f"Failed to delete {local_path}: {e}")
                    
                    # Remove from index
                    conn.execute("""
                        DELETE FROM cached_files WHERE remote_path = ?
                    """, (remote_path,))
                
                conn.commit()
                logger.info(
                    f"Cache cleanup: removed {cleaned_count} files, "
                    f"freed {freed_bytes / (1024*1024):.2f} MB"
                )
                
                return cleaned_count
                
            finally:
                conn.close()
    
    def get_cache_size(self) -> int:
        """
        Calculate total cache size in bytes.
        
        Returns:
            Total cache size in bytes
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT COALESCE(SUM(size_bytes), 0) as total_size
                FROM cached_files
            """)
            row = cursor.fetchone()
            return int(row['total_size']) if row else 0
        finally:
            conn.close()
    
    def clear_cache(self) -> None:
        """Clear all cached files and metadata."""
        with self._lock:
            # Clear database
            conn = self._get_connection()
            try:
                conn.execute("DELETE FROM artifacts")
                conn.execute("DELETE FROM cached_files")
                conn.execute("DELETE FROM download_tasks")
                conn.commit()
                logger.info("Database cache cleared")
            finally:
                conn.close()
            
            # Clear file system cache
            import shutil
            
            if self.metadata_dir.exists():
                shutil.rmtree(self.metadata_dir)
                self.metadata_dir.mkdir(parents=True, exist_ok=True)
            
            if self.downloads_dir.exists():
                shutil.rmtree(self.downloads_dir)
                self.downloads_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info("File system cache cleared")
    
    # ==================== Statistics ====================
    
    def get_stats(self) -> RemoteStorageStats:
        """
        Get cache statistics.
        
        Returns:
            RemoteStorageStats object with current statistics
        """
        conn = self._get_connection()
        try:
            # Count artifacts
            cursor = conn.execute("SELECT COUNT(*) as count FROM artifacts")
            artifacts_count = cursor.fetchone()['count']
            
            # Get cache size
            cache_size = self.get_cache_size()
            
            # Get last sync time
            cursor = conn.execute("""
                SELECT value FROM cache_stats WHERE key = 'last_sync'
            """)
            row = cursor.fetchone()
            last_sync = float(row['value']) if row else None
            
            return RemoteStorageStats(
                connected=False,  # Will be set by adapter
                last_sync=last_sync,
                total_artifacts=0,  # Will be set by adapter
                cached_artifacts=artifacts_count,
                cache_size_bytes=cache_size,
                remote_size_bytes=0,  # Will be set by adapter
                sync_count=0,  # Will be tracked separately
                error_count=0  # Will be tracked separately
            )
            
        finally:
            conn.close()
    
    def update_stat(self, key: str, value: str) -> None:
        """
        Update a cache statistic.
        
        Args:
            key: Statistic key
            value: Statistic value (will be converted to string)
        """
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO cache_stats (key, value, updated_at)
                    VALUES (?, ?, ?)
                """, (key, str(value), time.time()))
                conn.commit()
            finally:
                conn.close()
    
    def close(self) -> None:
        """Clean up resources."""
        # SQLite connections are closed after each operation
        # Nothing to clean up here
        logger.debug("Cache manager closed")


