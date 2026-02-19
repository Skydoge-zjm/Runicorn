# Client-Side Tests (Windows)

这些脚本在 Windows 上运行，测试与 WSL 服务器的 Remote Viewer 连接。

## 准备工作

1. 确保 WSL 服务器已设置好：
```bash
# 在 WSL 中
cd /mnt/e/pycharm_project/Runicorn
python tests/server/setup_test_data.py
python tests/server/start_remote_viewer.py
```

2. 配置 SSH 连接信息（创建 `tests/client/config.json`）：
```json
{
  "wsl_host": "localhost",
  "wsl_port": 22,
  "wsl_username": "your_wsl_username",
  "wsl_password": "your_password_or_null",
  "wsl_key_path": "C:/Users/YourName/.ssh/id_rsa",
  "remote_root": "/home/your_wsl_username/runicorn_test_data"
}
```

## 测试脚本

- `test_ssh_connection.py` - 测试 SSH 连接
- `test_connection_pool.py` - 测试连接池
- `test_remote_viewer_connection.py` - 测试 Remote Viewer 完整流程
- `test_remote_viewer_api.py` - 测试 Remote API 端点
- `test_tunnel.py` - 测试 SSH 隧道
