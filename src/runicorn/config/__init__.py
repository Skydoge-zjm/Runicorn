"""Unified configuration package for Runicorn.

All public symbols are re-exported here so that existing imports like
``from runicorn.config import load_user_config`` continue to work.
"""
from .paths import (
    _config_root_dir,
    get_config_file_path,
    get_rnconfig_file_path,
    get_registry_dir,
    get_connections_file_path,
    get_known_hosts_file_path,
)
from .user_config import (
    load_user_config,
    save_user_config,
    get_user_root_dir,
    set_user_root_dir,
)
from .connections import (
    load_saved_connections,
    save_connections,
    save_ssh_connections,
    get_ssh_connections,
    add_ssh_connection,
    remove_ssh_connection,
)
from .rate_limits import get_rate_limit_config, save_rate_limit_config
from .rnconfig import get_effective_rnconfig, load_effective_rnconfig
from .registry import get_config, clear_registry_cache

__all__ = [
    # paths
    "_config_root_dir",
    "get_config_file_path",
    "get_rnconfig_file_path",
    "get_registry_dir",
    "get_connections_file_path",
    "get_known_hosts_file_path",
    # user config
    "load_user_config",
    "save_user_config",
    "get_user_root_dir",
    "set_user_root_dir",
    # connections
    "load_saved_connections",
    "save_connections",
    "save_ssh_connections",
    "get_ssh_connections",
    "add_ssh_connection",
    "remove_ssh_connection",
    # rate limits
    "get_rate_limit_config",
    "save_rate_limit_config",
    # rnconfig
    "get_effective_rnconfig",
    "load_effective_rnconfig",
    # registry
    "get_config",
    "clear_registry_cache",
]
