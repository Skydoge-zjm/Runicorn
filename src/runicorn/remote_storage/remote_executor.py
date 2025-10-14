"""
Remote Command Executor

Executes management operations on remote server via SSH.
"""
from __future__ import annotations

import json
import logging
import textwrap
import time
import uuid
from typing import Any, Dict, List, Optional

import paramiko

from .models import RemoteOperation
from .metadata_sync import MetadataSyncService

logger = logging.getLogger(__name__)


class RemoteCommandExecutor:
    """
    Remote command executor for artifact management operations.
    
    Responsibilities:
    1. Execute operations on remote server (delete, tag, alias, etc.)
    2. Validate operations before execution
    3. Track operation history
    4. Trigger metadata sync after operations
    
    Security:
    - Sanitize all inputs to prevent command injection
    - Validate paths to prevent traversal attacks
    - Use Python scripts for complex operations (safer than shell)
    """
    
    def __init__(
        self,
        ssh_session: paramiko.SSHClient,
        remote_root: str,
        metadata_sync: MetadataSyncService
    ):
        """
        Initialize remote command executor.
        
        Args:
            ssh_session: Active SSH session
            remote_root: Remote storage root directory
            metadata_sync: Metadata sync service (for post-operation sync)
        """
        self.ssh_session = ssh_session
        self.remote_root = remote_root.rstrip('/')
        self.metadata_sync = metadata_sync
        
        # Operation history
        self._operations: Dict[str, RemoteOperation] = {}
    
    def delete_artifact_version(
        self,
        name: str,
        type: str,
        version: int,
        soft_delete: bool = True
    ) -> bool:
        """
        Delete an artifact version on remote server.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Version number
            soft_delete: If True, soft delete (create .deleted marker)
            
        Returns:
            True if operation succeeded
            
        Raises:
            ValueError: If parameters are invalid
        """
        # Validate inputs
        self._validate_artifact_params(name, type, version)
        
        # Create operation record
        op_id = str(uuid.uuid4())
        operation = RemoteOperation(
            operation_id=op_id,
            operation_type="delete_artifact_version",
            artifact_name=name,
            artifact_type=type,
            artifact_version=version,
            parameters={"soft_delete": soft_delete}
        )
        self._operations[op_id] = operation
        
        try:
            if soft_delete:
                success = self._soft_delete_artifact(name, type, version)
            else:
                success = self._hard_delete_artifact(name, type, version)
            
            if success:
                operation.complete({"deleted": True})
                
                # Sync metadata after operation
                self.metadata_sync._sync_artifact_versions(
                    type, name,
                    f"{self.remote_root}/artifacts/{type}/{name}"
                )
                
                logger.info(
                    f"{'Soft' if soft_delete else 'Hard'} deleted "
                    f"{name}:v{version} on remote server"
                )
            else:
                operation.fail("Operation returned failure")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete {name}:v{version}: {e}")
            operation.fail(str(e))
            return False
    
    def _soft_delete_artifact(self, name: str, type: str, version: int) -> bool:
        """
        Soft delete artifact by creating .deleted marker.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Version number
            
        Returns:
            True if successful
        """
        # Sanitize inputs for command (already validated)
        name_safe = name.replace("'", "\\'")
        type_safe = type.replace("'", "\\'")
        
        # Construct Python script to execute remotely
        script = textwrap.dedent(f"""
            import json
            import time
            from pathlib import Path
            
            try:
                version_dir = Path('{self.remote_root}/artifacts/{type_safe}/{name_safe}/v{version}')
                
                if not version_dir.exists():
                    print('ERROR: Version directory not found')
                    exit(1)
                
                # Create .deleted marker
                deleted_marker = version_dir / '.deleted'
                deleted_data = {{
                    'deleted_at': time.time(),
                    'deleted_by': 'remote_user',
                    'version': {version},
                    'artifact_name': '{name_safe}'
                }}
                
                deleted_marker.write_text(json.dumps(deleted_data, indent=2))
                print('OK')
                
            except Exception as e:
                print(f'ERROR: {{e}}')
                exit(1)
        """)
        
        return self._execute_python_script(script)
    
    def _hard_delete_artifact(self, name: str, type: str, version: int) -> bool:
        """
        Permanently delete artifact version.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Version number
            
        Returns:
            True if successful
        """
        # Sanitize inputs
        name_safe = name.replace("'", "\\'")
        type_safe = type.replace("'", "\\'")
        
        script = textwrap.dedent(f"""
            import shutil
            from pathlib import Path
            
            try:
                version_dir = Path('{self.remote_root}/artifacts/{type_safe}/{name_safe}/v{version}')
                
                if not version_dir.exists():
                    print('ERROR: Version directory not found')
                    exit(1)
                
                # Permanently delete
                shutil.rmtree(version_dir)
                print('OK')
                
            except Exception as e:
                print(f'ERROR: {{e}}')
                exit(1)
        """)
        
        return self._execute_python_script(script)
    
    def set_artifact_alias(
        self,
        name: str,
        type: str,
        version: int,
        alias: str
    ) -> bool:
        """
        Set an alias for an artifact version on remote server.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Version number
            alias: Alias name (e.g., "production", "latest")
            
        Returns:
            True if operation succeeded
        """
        # Validate inputs
        self._validate_artifact_params(name, type, version)
        self._validate_alias(alias)
        
        # Create operation record
        op_id = str(uuid.uuid4())
        operation = RemoteOperation(
            operation_id=op_id,
            operation_type="set_alias",
            artifact_name=name,
            artifact_type=type,
            artifact_version=version,
            parameters={"alias": alias}
        )
        self._operations[op_id] = operation
        
        try:
            # Sanitize inputs
            name_safe = name.replace("'", "\\'")
            type_safe = type.replace("'", "\\'")
            alias_safe = alias.replace("'", "\\'")
            
            script = textwrap.dedent(f"""
                import json
                import time
                from pathlib import Path
                
                try:
                    versions_file = Path('{self.remote_root}/artifacts/{type_safe}/{name_safe}/versions.json')
                    
                    if not versions_file.exists():
                        print('ERROR: Artifact not found')
                        exit(1)
                    
                    # Read versions index
                    data = json.loads(versions_file.read_text(encoding='utf-8'))
                    
                    # Update alias
                    if 'aliases' not in data:
                        data['aliases'] = {{}}
                    
                    data['aliases']['{alias_safe}'] = {version}
                    data['updated_at'] = time.time()
                    
                    # Save atomically
                    import tempfile
                    temp_fd, temp_path = tempfile.mkstemp(
                        dir=versions_file.parent,
                        prefix='.versions_',
                        suffix='.json.tmp'
                    )
                    
                    import os
                    os.close(temp_fd)
                    
                    Path(temp_path).write_text(json.dumps(data, indent=2, ensure_ascii=False))
                    Path(temp_path).replace(versions_file)
                    
                    print('OK')
                    
                except Exception as e:
                    print(f'ERROR: {{e}}')
                    exit(1)
            """)
            
            success = self._execute_python_script(script)
            
            if success:
                operation.complete({"alias": alias, "version": version})
                
                # Sync metadata after operation
                self.metadata_sync._sync_artifact_versions(
                    type, name,
                    f"{self.remote_root}/artifacts/{type}/{name}"
                )
                
                logger.info(f"Set alias '{alias}' → {name}:v{version}")
            else:
                operation.fail("Operation returned failure")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to set alias for {name}:v{version}: {e}")
            operation.fail(str(e))
            return False
    
    def add_artifact_tags(
        self,
        name: str,
        type: str,
        version: int,
        tags: List[str]
    ) -> bool:
        """
        Add tags to an artifact version on remote server.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Version number
            tags: List of tags to add
            
        Returns:
            True if operation succeeded
        """
        # Validate inputs
        self._validate_artifact_params(name, type, version)
        
        if not tags or not isinstance(tags, list):
            raise ValueError("Tags must be a non-empty list")
        
        # Sanitize tags
        for tag in tags:
            if not isinstance(tag, str) or not tag.strip():
                raise ValueError(f"Invalid tag: {tag}")
        
        # Create operation record
        op_id = str(uuid.uuid4())
        operation = RemoteOperation(
            operation_id=op_id,
            operation_type="add_tags",
            artifact_name=name,
            artifact_type=type,
            artifact_version=version,
            parameters={"tags": tags}
        )
        self._operations[op_id] = operation
        
        try:
            # Sanitize inputs
            name_safe = name.replace("'", "\\'")
            type_safe = type.replace("'", "\\'")
            tags_json = json.dumps(tags)
            
            script = textwrap.dedent(f"""
                import json
                import time
                from pathlib import Path
                
                try:
                    metadata_file = Path('{self.remote_root}/artifacts/{type_safe}/{name_safe}/v{version}/metadata.json')
                    
                    if not metadata_file.exists():
                        print('ERROR: Metadata not found')
                        exit(1)
                    
                    # Read metadata
                    data = json.loads(metadata_file.read_text(encoding='utf-8'))
                    
                    # Add tags (avoid duplicates)
                    if 'tags' not in data:
                        data['tags'] = []
                    
                    new_tags = {tags_json}
                    for tag in new_tags:
                        if tag not in data['tags']:
                            data['tags'].append(tag)
                    
                    data['updated_at'] = time.time()
                    
                    # Save atomically
                    import tempfile
                    temp_fd, temp_path = tempfile.mkstemp(
                        dir=metadata_file.parent,
                        prefix='.metadata_',
                        suffix='.json.tmp'
                    )
                    
                    import os
                    os.close(temp_fd)
                    
                    Path(temp_path).write_text(json.dumps(data, indent=2, ensure_ascii=False))
                    Path(temp_path).replace(metadata_file)
                    
                    print('OK')
                    
                except Exception as e:
                    print(f'ERROR: {{e}}')
                    exit(1)
            """)
            
            success = self._execute_python_script(script)
            
            if success:
                operation.complete({"tags": tags})
                
                # Sync metadata after operation
                self.metadata_sync._sync_artifact_versions(
                    type, name,
                    f"{self.remote_root}/artifacts/{type}/{name}"
                )
                
                logger.info(f"Added tags {tags} to {name}:v{version}")
            else:
                operation.fail("Operation returned failure")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to add tags to {name}:v{version}: {e}")
            operation.fail(str(e))
            return False
    
    def _execute_python_script(self, script: str) -> bool:
        """
        Execute a Python script on remote server.
        
        Args:
            script: Python script to execute
            
        Returns:
            True if script executed successfully (printed 'OK')
            
        Raises:
            RuntimeError: If SSH execution fails
        """
        # Execute via SSH
        # Use heredoc to avoid quote escaping issues
        try:
            # Escape script for heredoc (replace $ with \$)
            script_safe = script.replace('$', '\\$')
            
            command = f"""cd {self.remote_root} && python3 << 'RUNICORN_SCRIPT_EOF'
{script_safe}
RUNICORN_SCRIPT_EOF
"""
            
            stdin, stdout, stderr = self.ssh_session.exec_command(
                command,
                timeout=30
            )
            
            # Read output
            exit_status = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode('utf-8').strip()
            stderr_text = stderr.read().decode('utf-8').strip()
            
            # Check result
            if exit_status == 0 and stdout_text == 'OK':
                return True
            else:
                error_msg = stderr_text or stdout_text or "Unknown error"
                logger.error(f"Remote script failed: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"SSH command execution failed: {e}")
            raise RuntimeError(f"Failed to execute remote command: {e}") from e
    
    def _validate_artifact_params(self, name: str, type: str, version: int):
        """
        Validate artifact parameters.
        
        Args:
            name: Artifact name
            type: Artifact type
            version: Version number
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not name or not isinstance(name, str):
            raise ValueError("Artifact name must be a non-empty string")
        
        # Check for path traversal attempts
        if '..' in name or '/' in name or '\\' in name:
            raise ValueError(f"Invalid artifact name (path traversal detected): {name}")
        
        if not type or not isinstance(type, str):
            raise ValueError("Artifact type must be a non-empty string")
        
        if type not in ['model', 'dataset', 'config', 'code', 'custom']:
            raise ValueError(f"Invalid artifact type: {type}")
        
        if not isinstance(version, int) or version < 1:
            raise ValueError(f"Version must be a positive integer, got: {version}")
    
    def _validate_alias(self, alias: str):
        """
        Validate alias name.
        
        Args:
            alias: Alias name
            
        Raises:
            ValueError: If alias is invalid
        """
        if not alias or not isinstance(alias, str):
            raise ValueError("Alias must be a non-empty string")
        
        # Check for invalid characters
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']
        if any(c in alias for c in invalid_chars):
            raise ValueError(f"Alias contains invalid characters: {alias}")
    
    def get_operation_history(
        self,
        limit: int = 100
    ) -> List[RemoteOperation]:
        """
        Get operation history.
        
        Args:
            limit: Maximum number of operations to return
            
        Returns:
            List of recent operations
        """
        operations = sorted(
            self._operations.values(),
            key=lambda op: op.started_at,
            reverse=True
        )
        return operations[:limit]
    
    def test_connection(self) -> bool:
        """
        Test remote connection by executing a simple command.
        
        Returns:
            True if connection is working
        """
        try:
            stdin, stdout, stderr = self.ssh_session.exec_command(
                "echo 'OK'",
                timeout=10
            )
            
            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode('utf-8').strip()
            
            return exit_status == 0 and output == 'OK'
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def verify_remote_structure(self) -> Dict[str, bool]:
        """
        Verify remote storage structure exists.
        
        Returns:
            Dictionary with verification results
        """
        results = {}
        
        # Check artifacts directory
        results['artifacts_exists'] = self._remote_path_exists(
            f"{self.remote_root}/artifacts"
        )
        
        # Check for at least one artifact type
        if results['artifacts_exists']:
            for type_name in ['model', 'dataset', 'config']:
                type_path = f"{self.remote_root}/artifacts/{type_name}"
                if self._remote_path_exists(type_path):
                    results[f'has_{type_name}'] = True
                    break
        
        # Check for projects
        results['has_experiments'] = False
        try:
            items = self.ssh_session.exec_command(
                f"ls -1 {self.remote_root} 2>/dev/null | head -10",
                timeout=10
            )[1].read().decode('utf-8').split('\n')
            
            for item in items:
                if item and item not in ['artifacts', 'sweeps', 'runicorn.db']:
                    results['has_experiments'] = True
                    break
        except Exception:
            pass
        
        return results
    
    def _remote_path_exists(self, remote_path: str) -> bool:
        """
        Check if a path exists on remote server.
        
        Args:
            remote_path: Remote path to check
            
        Returns:
            True if path exists
        """
        try:
            stdin, stdout, stderr = self.ssh_session.exec_command(
                f"test -e {remote_path} && echo 'EXISTS'",
                timeout=10
            )
            
            output = stdout.read().decode('utf-8').strip()
            return output == 'EXISTS'
            
        except Exception as e:
            logger.debug(f"Failed to check path {remote_path}: {e}")
            return False


