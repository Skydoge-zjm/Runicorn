"""
Environment tracking for Runicorn.
Captures Python dependencies, Git state, and system information.
"""
from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentInfo:
    """Container for environment information."""
    python_version: str
    platform: str
    platform_details: Dict[str, str]
    pip_packages: Optional[List[str]]
    conda_packages: Optional[List[str]]
    conda_env: Optional[str]
    git_info: Optional[Dict[str, str]]
    env_variables: Dict[str, str]
    gpu_info: Optional[List[Dict[str, Any]]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def save(self, path: Path) -> None:
        """Save environment info to JSON file."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Environment info saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save environment info: {e}")


class EnvironmentCapture:
    """Capture environment information for reproducibility."""
    
    def __init__(self, working_dir: Optional[Path] = None):
        """
        Initialize environment capture.
        
        Args:
            working_dir: Working directory for Git detection
        """
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
    
    def capture_all(self) -> EnvironmentInfo:
        """Capture all environment information."""
        return EnvironmentInfo(
            python_version=self.get_python_version(),
            platform=self.get_platform(),
            platform_details=self.get_platform_details(),
            pip_packages=self.get_pip_packages(),
            conda_packages=self.get_conda_packages(),
            conda_env=self.get_conda_env(),
            git_info=self.get_git_info(),
            env_variables=self.get_env_variables(),
            gpu_info=self.get_gpu_info()
        )
    
    def get_python_version(self) -> str:
        """Get Python version."""
        return sys.version
    
    def get_platform(self) -> str:
        """Get platform information."""
        return f"{platform.system()} {platform.release()} ({platform.machine()})"
    
    def get_platform_details(self) -> Dict[str, str]:
        """Get detailed platform information."""
        return {
            "system": platform.system(),
            "node": platform.node(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_implementation": platform.python_implementation(),
            "python_compiler": platform.python_compiler()
        }
    
    def get_pip_packages(self) -> Optional[List[str]]:
        """Get list of installed pip packages."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "freeze"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                packages = [line.strip() for line in result.stdout.splitlines() 
                          if line.strip() and not line.startswith("#")]
                logger.debug(f"Captured {len(packages)} pip packages")
                return packages
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.debug(f"Failed to get pip packages: {e}")
        return None
    
    def get_conda_packages(self) -> Optional[List[str]]:
        """Get list of conda packages if in conda environment."""
        if not self._is_conda_env():
            return None
        
        try:
            result = subprocess.run(
                ["conda", "list", "--export"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                packages = [line.strip() for line in result.stdout.splitlines()
                          if line.strip() and not line.startswith("#")]
                logger.debug(f"Captured {len(packages)} conda packages")
                return packages
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.debug(f"Failed to get conda packages: {e}")
        return None
    
    def get_conda_env(self) -> Optional[str]:
        """Get current conda environment name."""
        # Check CONDA_DEFAULT_ENV first
        conda_env = os.environ.get("CONDA_DEFAULT_ENV")
        if conda_env:
            return conda_env
        
        # Check if we're in a conda environment
        conda_prefix = os.environ.get("CONDA_PREFIX")
        if conda_prefix:
            return Path(conda_prefix).name
        
        return None
    
    def _is_conda_env(self) -> bool:
        """Check if running in conda environment."""
        return bool(os.environ.get("CONDA_PREFIX") or 
                   os.environ.get("CONDA_DEFAULT_ENV"))
    
    def get_git_info(self) -> Optional[Dict[str, str]]:
        """Get Git repository information."""
        git_info = {}
        
        try:
            # Check if in a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                timeout=5
            )
            
            if result.returncode != 0:
                return None
            
            # Get current commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                timeout=5
            )
            if result.returncode == 0:
                git_info["commit"] = result.stdout.strip()
            
            # Get current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                timeout=5
            )
            if result.returncode == 0:
                git_info["branch"] = result.stdout.strip()
            
            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                timeout=5
            )
            if result.returncode == 0:
                git_info["has_changes"] = bool(result.stdout.strip())
                if git_info["has_changes"]:
                    # Count changed files
                    changed_files = result.stdout.strip().splitlines()
                    git_info["changed_files_count"] = len(changed_files)
            
            # Get remote URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                timeout=5
            )
            if result.returncode == 0:
                git_info["remote"] = result.stdout.strip()
            
            # Get last commit message
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=%B"],
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                timeout=5
            )
            if result.returncode == 0:
                git_info["last_commit_message"] = result.stdout.strip()
            
            # Get last commit author
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=%an <%ae>"],
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                timeout=5
            )
            if result.returncode == 0:
                git_info["last_commit_author"] = result.stdout.strip()
            
            logger.debug(f"Captured git info: {git_info}")
            return git_info
            
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.debug(f"Git info capture failed: {e}")
            return None
    
    def get_env_variables(self, filter_keys: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Get relevant environment variables.
        
        Args:
            filter_keys: List of environment variable keys to include.
                        If None, uses default ML-related keys.
        
        Returns:
            Dictionary of environment variables
        """
        if filter_keys is None:
            # Default ML/DL related environment variables
            filter_keys = [
                "CUDA_VISIBLE_DEVICES",
                "CUDA_HOME",
                "CUDNN_VERSION",
                "NCCL_VERSION",
                "PYTORCH_VERSION",
                "TF_VERSION",
                "KERAS_BACKEND",
                "JAX_PLATFORM_NAME",
                "OMP_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
                "PYTHONPATH",
                "LD_LIBRARY_PATH",
                "DYLD_LIBRARY_PATH",
                "PATH",
                "VIRTUAL_ENV",
                "CONDA_DEFAULT_ENV",
                "CONDA_PREFIX",
                "RUNICORN_DIR",
                "WANDB_MODE",
                "MLFLOW_TRACKING_URI"
            ]
        
        env_vars = {}
        for key in filter_keys:
            value = os.environ.get(key)
            if value:
                # Truncate very long values (like PATH)
                if len(value) > 500:
                    value = value[:497] + "..."
                env_vars[key] = value
        
        return env_vars
    
    def get_gpu_info(self) -> Optional[List[Dict[str, Any]]]:
        """Get GPU information if available."""
        try:
            # Try nvidia-smi for NVIDIA GPUs
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,name,memory.total,memory.free,utilization.gpu,temperature.gpu", 
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                gpus = []
                for line in result.stdout.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 6:
                        gpus.append({
                            "index": int(parts[0]),
                            "name": parts[1],
                            "memory_total_mb": float(parts[2]),
                            "memory_free_mb": float(parts[3]),
                            "utilization_percent": float(parts[4]),
                            "temperature_c": float(parts[5])
                        })
                return gpus
        except (subprocess.SubprocessError, FileNotFoundError, ValueError):
            pass
        
        # Try to detect through Python libraries
        try:
            import torch
            if torch.cuda.is_available():
                gpus = []
                for i in range(torch.cuda.device_count()):
                    props = torch.cuda.get_device_properties(i)
                    gpus.append({
                        "index": i,
                        "name": props.name,
                        "memory_total_mb": props.total_memory / (1024 * 1024),
                        "compute_capability": f"{props.major}.{props.minor}"
                    })
                return gpus
        except ImportError:
            pass
        
        return None
    
    def capture_code_snapshot(self, code_dir: Path, output_dir: Path,
                            extensions: List[str] = None) -> bool:
        """
        Capture a snapshot of code files.
        
        Args:
            code_dir: Directory containing code
            output_dir: Directory to save snapshot
            extensions: File extensions to include (default: .py, .yaml, .json)
        
        Returns:
            True if successful
        """
        if extensions is None:
            extensions = ['.py', '.yaml', '.yml', '.json', '.toml', '.cfg', '.ini']
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            snapshot_info = {
                "source_dir": str(code_dir),
                "timestamp": platform.python_compiler(),
                "files": []
            }
            
            for root, _, files in os.walk(code_dir):
                for file in files:
                    if any(file.endswith(ext) for ext in extensions):
                        file_path = Path(root) / file
                        rel_path = file_path.relative_to(code_dir)
                        
                        # Copy file to snapshot
                        dest_path = output_dir / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as src:
                                content = src.read()
                            with open(dest_path, 'w', encoding='utf-8') as dst:
                                dst.write(content)
                            
                            snapshot_info["files"].append(str(rel_path))
                        except Exception as e:
                            logger.warning(f"Failed to snapshot {file_path}: {e}")
            
            # Save snapshot info
            info_path = output_dir / "snapshot_info.json"
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(snapshot_info, f, indent=2)
            
            logger.info(f"Code snapshot saved to {output_dir} ({len(snapshot_info['files'])} files)")
            return True
            
        except Exception as e:
            logger.error(f"Code snapshot failed: {e}")
            return False


def capture_for_run(run_dir: Path, working_dir: Optional[Path] = None) -> EnvironmentInfo:
    """
    Capture environment for a run and save to run directory.
    
    Args:
        run_dir: Run directory
        working_dir: Working directory for Git detection
    
    Returns:
        Captured environment info
    """
    capture = EnvironmentCapture(working_dir)
    env_info = capture.capture_all()
    
    # Save to run directory
    env_path = run_dir / "environment.json"
    env_info.save(env_path)
    
    return env_info
