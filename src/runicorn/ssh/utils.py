"""
SSH/SFTP Utility Functions

Provides optimized and hardened operations for SFTP interactions.
"""
from __future__ import annotations

import logging
import posixpath
import stat as statmod
from typing import Any, Dict, List, Optional, Tuple
import paramiko

logger = logging.getLogger(__name__)


class SFTPEntry:
    """
    SFTP directory entry with cached attributes.
    
    Avoids the N+1 stat problem by using listdir_attr.
    """
    
    def __init__(self, name: str, attrs: paramiko.SFTPAttributes):
        """
        Initialize entry from SFTP attributes.
        
        Args:
            name: File/directory name
            attrs: SFTP attributes from listdir_attr
        """
        self.name = name
        self.size = attrs.st_size if attrs.st_size else 0
        self.mtime = attrs.st_mtime if attrs.st_mtime else 0
        self.mode = attrs.st_mode if attrs.st_mode else 0
        self.is_dir = statmod.S_ISDIR(self.mode) if self.mode else False
        self.is_file = statmod.S_ISREG(self.mode) if self.mode else False
        self._attrs = attrs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "name": self.name,
            "type": "directory" if self.is_dir else "file",
            "size": self.size,
            "mtime": self.mtime,
        }
    
    @property
    def attrs(self) -> paramiko.SFTPAttributes:
        """Get underlying SFTP attributes."""
        return self._attrs


def sftp_listdir_with_attrs(
    sftp: paramiko.SFTPClient,
    path: str,
    include_hidden: bool = False
) -> List[SFTPEntry]:
    """
    List directory with attributes in a single call.
    
    This replaces the N+1 pattern of:
        names = sftp.listdir(path)
        for name in names:
            attrs = sftp.stat(posixpath.join(path, name))
    
    With a single listdir_attr call that returns attributes for all entries.
    
    Args:
        sftp: Active SFTP client
        path: Remote directory path
        include_hidden: Include hidden files/directories (starting with '.')
        
    Returns:
        List of SFTPEntry objects with cached attributes
        
    Raises:
        IOError: If directory doesn't exist or permission denied
    """
    try:
        attrs_list = sftp.listdir_attr(path)
        entries = []
        
        for attrs in attrs_list:
            name = attrs.filename
            
            # Skip . and .. entries
            if name in ('.', '..'):
                continue
            
            # Skip hidden files if requested
            if not include_hidden and name.startswith('.'):
                continue
            
            entries.append(SFTPEntry(name, attrs))
        
        logger.debug(f"Listed {len(entries)} entries in {path} (single call)")
        return entries
        
    except IOError as e:
        logger.error(f"Failed to list directory {path}: {e}")
        raise


def resolve_sftp_home(sftp: paramiko.SFTPClient, path: str) -> str:
    """
    Resolve home directory (~) in SFTP path without exec_command.
    
    This replaces:
        stdin, stdout, stderr = ssh.exec_command("echo $HOME")
        home = stdout.read().decode().strip()
    
    With:
        home = sftp.normalize("~")
    
    Args:
        sftp: Active SFTP client
        path: Path that may contain ~
        
    Returns:
        Resolved absolute path
    """
    if not path or not path.startswith('~'):
        return path
    
    try:
        # Use SFTP's normalize() to resolve home directory
        # This is more efficient and doesn't require an SSH channel
        if path == '~' or path == '~/':
            resolved = sftp.normalize('.')
        elif path.startswith('~/'):
            # Resolve home first, then join with rest of path
            home = sftp.normalize('.')
            rest = path[2:]  # Remove '~/'
            resolved = posixpath.join(home, rest)
        else:
            # Path like ~user/ - SFTP may not support this
            # Try normalize directly
            resolved = sftp.normalize(path)
        
        logger.debug(f"Resolved {path} -> {resolved}")
        return resolved
        
    except Exception as e:
        logger.warning(f"Failed to resolve home in {path}: {e}")
        # Fallback: return as-is
        return path


def sftp_walk(
    sftp: paramiko.SFTPClient,
    path: str,
    max_depth: Optional[int] = None,
    skip_dirs: Optional[List[str]] = None,
    include_hidden: bool = False
) -> List[Tuple[str, List[SFTPEntry], List[SFTPEntry]]]:
    """
    Recursively walk SFTP directory tree, similar to os.walk.
    
    Args:
        sftp: Active SFTP client
        path: Starting directory path
        max_depth: Maximum recursion depth (None = unlimited)
        skip_dirs: List of directory names to skip (e.g., ['artifacts', '.cache'])
        include_hidden: Include hidden files/directories
        
    Returns:
        List of (dirpath, subdirs, files) tuples where subdirs and files are SFTPEntry objects
    """
    if skip_dirs is None:
        skip_dirs = []
    
    results = []
    
    def _walk_recursive(current_path: str, current_depth: int):
        """Internal recursive walker."""
        # Check depth limit
        if max_depth is not None and current_depth > max_depth:
            return
        
        try:
            entries = sftp_listdir_with_attrs(sftp, current_path, include_hidden)
        except IOError:
            logger.warning(f"Cannot access directory: {current_path}")
            return
        
        subdirs = []
        files = []
        
        for entry in entries:
            if entry.is_dir:
                # Skip directories in skip list
                if entry.name in skip_dirs:
                    logger.debug(f"Skipping directory: {entry.name}")
                    continue
                subdirs.append(entry)
            else:
                files.append(entry)
        
        # Add current level
        results.append((current_path, subdirs, files))
        
        # Recurse into subdirectories
        for subdir in subdirs:
            subdir_path = posixpath.join(current_path, subdir.name)
            _walk_recursive(subdir_path, current_depth + 1)
    
    _walk_recursive(path, 0)
    return results


def get_sftp_file_hash(
    sftp: paramiko.SFTPClient,
    path: str,
    offset: int = 0,
    length: Optional[int] = None,
    algorithm: str = 'sha256'
) -> Optional[str]:
    """
    Compute hash of remote file (or portion of it).
    
    Useful for verifying append-only file integrity (tail_hash).
    
    Args:
        sftp: Active SFTP client
        path: Remote file path
        offset: Start offset for hashing (default: 0 = start of file)
        length: Number of bytes to hash (None = to end of file)
        algorithm: Hash algorithm ('sha256', 'md5', etc.)
        
    Returns:
        Hex digest of hash, or None if failed
    """
    import hashlib
    
    try:
        hasher = hashlib.new(algorithm)
        
        with sftp.open(path, 'rb') as f:
            f.seek(offset)
            
            bytes_read = 0
            chunk_size = 64 * 1024  # 64KB chunks
            
            while True:
                # Determine chunk size to read
                if length is not None:
                    remaining = length - bytes_read
                    if remaining <= 0:
                        break
                    read_size = min(chunk_size, remaining)
                else:
                    read_size = chunk_size
                
                chunk = f.read(read_size)
                if not chunk:
                    break
                
                hasher.update(chunk)
                bytes_read += len(chunk)
        
        digest = hasher.hexdigest()
        logger.debug(f"Computed {algorithm} hash of {path}[{offset}:{offset+bytes_read}] = {digest[:16]}...")
        return digest
        
    except Exception as e:
        logger.error(f"Failed to compute hash of {path}: {e}")
        return None


def sftp_file_tail_hash(
    sftp: paramiko.SFTPClient,
    path: str,
    tail_size: int = 4096,
    algorithm: str = 'sha256'
) -> Optional[str]:
    """
    Compute hash of the last N bytes of a file (tail hash).
    
    Used for verifying append-only files without reading the entire file.
    
    Args:
        sftp: Active SFTP client
        path: Remote file path
        tail_size: Number of bytes from end to hash (default: 4KB)
        algorithm: Hash algorithm
        
    Returns:
        Hex digest of tail hash, or None if failed
    """
    try:
        # Get file size
        stat_info = sftp.stat(path)
        file_size = stat_info.st_size
        
        if file_size <= tail_size:
            # File is smaller than tail_size, hash entire file
            return get_sftp_file_hash(sftp, path, 0, file_size, algorithm)
        else:
            # Hash last tail_size bytes
            offset = file_size - tail_size
            return get_sftp_file_hash(sftp, path, offset, tail_size, algorithm)
            
    except Exception as e:
        logger.error(f"Failed to compute tail hash of {path}: {e}")
        return None
