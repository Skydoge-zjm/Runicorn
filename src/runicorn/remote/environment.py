"""
Remote Environment Detection

Detects Python interpreters and conda/venv environments on remote servers.
Inspired by VSCode Remote Python detection strategy.
"""
from __future__ import annotations

import logging
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PythonEnvironment:
    """Represents a detected Python environment."""
    name: str
    type: str  # 'system', 'conda', 'venv', 'virtualenv'
    python_path: str
    version: str
    env_path: Optional[str] = None
    is_default: bool = False


class RemoteEnvironmentDetector:
    """
    Detects Python environments on remote servers.
    
    Detection strategy (similar to VSCode Remote):
    1. Find conda installations
    2. List conda environments
    3. Find system Python
    4. Find venv/virtualenv environments (future)
    """
    
    # Common conda installation paths
    CONDA_PATHS = [
        "~/anaconda3/bin/conda",
        "~/miniconda3/bin/conda",
        "~/anaconda/bin/conda",
        "~/miniconda/bin/conda",
        "/opt/anaconda3/bin/conda",
        "/opt/miniconda3/bin/conda",
        "/usr/local/anaconda3/bin/conda",
        "/usr/local/miniconda3/bin/conda",
        "$CONDA_PREFIX/bin/conda",
    ]
    
    # Shell init files that might contain conda setup
    SHELL_INIT_FILES = [
        "~/.bashrc",
        "~/.bash_profile",
        "~/.zshrc",
        "~/.profile",
    ]
    
    def __init__(self, connection):
        """
        Initialize detector with SSH connection.
        
        Args:
            connection: SSHConnection instance
        """
        self.connection = connection
        self._conda_path: Optional[str] = None
        self._conda_root: Optional[str] = None
    
    def detect_all_environments(self) -> List[PythonEnvironment]:
        """
        Detect all available Python environments.
        
        Returns:
            List of detected Python environments
        """
        environments = []
        
        # 1. Find conda and its environments
        conda_envs = self._detect_conda_environments()
        environments.extend(conda_envs)
        
        # 2. Add system Python if not already included
        if not any(env.type == 'system' for env in environments):
            system_python = self._detect_system_python()
            if system_python:
                environments.append(system_python)
        
        logger.info(f"Detected {len(environments)} Python environments")
        return environments
    
    def _find_conda(self) -> Optional[str]:
        """
        Find conda executable on remote server.
        
        Strategy:
        1. Try 'which conda' (if in PATH)
        2. Search common installation paths
        3. Parse shell init files for conda setup
        
        Returns:
            Path to conda executable, or None if not found
        """
        if self._conda_path:
            return self._conda_path
        
        # Method 1: Check if conda is in PATH
        stdout, _, exit_code = self.connection.exec_command("which conda")
        if exit_code == 0 and stdout.strip():
            self._conda_path = stdout.strip()
            logger.info(f"Found conda in PATH: {self._conda_path}")
            return self._conda_path
        
        # Method 2: Try common conda paths
        for conda_path in self.CONDA_PATHS:
            # Expand home directory
            expanded_path = conda_path.replace("~", "$HOME")
            test_cmd = f'test -f {expanded_path} && echo "exists"'
            stdout, _, exit_code = self.connection.exec_command(test_cmd)
            
            if exit_code == 0 and stdout.strip() == "exists":
                self._conda_path = expanded_path
                logger.info(f"Found conda at: {self._conda_path}")
                return self._conda_path
        
        # Method 3: Parse shell init files for conda initialization
        conda_path = self._find_conda_from_shell_init()
        if conda_path:
            self._conda_path = conda_path
            logger.info(f"Found conda from shell init: {self._conda_path}")
            return self._conda_path
        
        logger.warning("Conda not found on remote server")
        return None
    
    def _find_conda_from_shell_init(self) -> Optional[str]:
        """
        Parse shell initialization files to find conda setup.
        
        Returns:
            Path to conda executable if found
        """
        for init_file in self.SHELL_INIT_FILES:
            # Try to read the init file
            expanded_file = init_file.replace("~", "$HOME")
            stdout, _, exit_code = self.connection.exec_command(f"cat {expanded_file}")
            
            if exit_code != 0:
                continue
            
            content = stdout
            
            # Look for conda initialization patterns
            # Pattern 1: __conda_setup="$(...)"
            match = re.search(r'__conda_setup="\$\(['"'"']([^'"'"']+)/bin/conda['"'"']', content)
            if match:
                conda_root = match.group(1)
                return f"{conda_root}/bin/conda"
            
            # Pattern 2: export PATH="...conda.../bin:$PATH"
            match = re.search(r'export PATH="([^"]*conda[^"]*)/bin', content)
            if match:
                conda_root = match.group(1)
                return f"{conda_root}/bin/conda"
            
            # Pattern 3: source /path/to/conda/etc/profile.d/conda.sh
            match = re.search(r'source ([^/\s]*)/etc/profile\.d/conda\.sh', content)
            if match:
                conda_root = match.group(1)
                return f"{conda_root}/bin/conda"
        
        return None
    
    def _detect_conda_environments(self) -> List[PythonEnvironment]:
        """
        Detect all conda environments.
        
        Returns:
            List of conda environments
        """
        conda_path = self._find_conda()
        if not conda_path:
            return []
        
        # Get list of conda environments
        stdout, stderr, exit_code = self.connection.exec_command(
            f"{conda_path} info --envs"
        )
        
        if exit_code != 0:
            logger.error(f"Failed to list conda environments: {stderr}")
            return []
        
        environments = []
        lines = stdout.strip().split('\n')
        
        for line in lines:
            # Skip comments and empty lines
            if line.startswith('#') or not line.strip():
                continue
            
            parts = line.split()
            if len(parts) < 2:
                continue
            
            env_name = parts[0]
            is_default = '*' in parts
            env_path = parts[-1]  # Last part is always the path
            
            # Get Python version
            python_version = self._get_python_version_in_env(conda_path, env_name, env_path)
            
            if python_version:
                environments.append(PythonEnvironment(
                    name=env_name,
                    type='conda',
                    python_path=f"{env_path}/bin/python",
                    version=python_version,
                    env_path=env_path,
                    is_default=is_default
                ))
        
        return environments
    
    def _get_python_version_in_env(
        self, 
        conda_path: str, 
        env_name: str, 
        env_path: str
    ) -> Optional[str]:
        """
        Get Python version in a specific conda environment.
        
        Args:
            conda_path: Path to conda executable
            env_name: Environment name
            env_path: Environment path
            
        Returns:
            Python version string or None
        """
        # Method 1: Use conda run
        stdout, stderr, exit_code = self.connection.exec_command(
            f"{conda_path} run -n {env_name} python --version"
        )
        
        # Check both stdout and stderr (Python version can be in either)
        version_output = stdout.strip() if stdout.strip() else stderr.strip()
        if exit_code == 0 and version_output:
            return version_output
        
        # Method 2: Direct path to python
        python_path = f"{env_path}/bin/python"
        stdout, stderr, exit_code = self.connection.exec_command(
            f"{python_path} --version"
        )
        
        version_output = stdout.strip() if stdout.strip() else stderr.strip()
        if exit_code == 0 and version_output:
            return version_output
        
        return "Unknown"
    
    def _detect_system_python(self) -> Optional[PythonEnvironment]:
        """
        Detect system Python installation.
        
        Returns:
            System Python environment or None
        """
        # Try python3 first, then python
        for python_cmd in ['python3', 'python']:
            stdout, _, exit_code = self.connection.exec_command(
                f"which {python_cmd}"
            )
            
            if exit_code != 0:
                continue
            
            python_path = stdout.strip()
            
            # Get version
            stdout, stderr, exit_code = self.connection.exec_command(
                f"{python_path} --version"
            )
            
            if exit_code == 0:
                version = stdout.strip() if stdout.strip() else stderr.strip()
                return PythonEnvironment(
                    name='system',
                    type='system',
                    python_path=python_path,
                    version=version,
                    is_default=True
                )
        
        return None
    
    def get_python_command_for_env(self, env_name: str) -> Optional[str]:
        """
        Get the command to run Python in a specific environment.
        
        Args:
            env_name: Environment name
            
        Returns:
            Command string to run Python, or None if not found
        """
        if env_name == 'system':
            return 'python3'
        
        # For conda environments, find conda first
        conda_path = self._find_conda()
        if not conda_path:
            return None
        
        # Get environment path
        stdout, _, exit_code = self.connection.exec_command(
            f"{conda_path} info --envs | grep '^{env_name} '"
        )
        
        if exit_code != 0 or not stdout.strip():
            return None
        
        parts = stdout.strip().split()
        if len(parts) >= 2:
            env_path = parts[-1]
            return f"{env_path}/bin/python"
        
        return None
