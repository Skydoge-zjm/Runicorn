# Server-Side Tests (WSL)

这些脚本应在 WSL 环境中运行，用于模拟远程服务器。

## 准备工作

1. 在 WSL 中安装 runicorn（开发模式）：
```bash
cd /mnt/e/pycharm_project/Runicorn
pip install -e .
```

2. 准备测试数据：
```bash
python tests/server/setup_test_data.py
```

3. 启动远程 viewer（remote-mode）：
```bash
python tests/server/start_remote_viewer.py
```

## 测试脚本

- `setup_test_data.py` - 创建测试实验数据
- `start_remote_viewer.py` - 启动远程 viewer（模拟）
- `test_remote_viewer_basic.py` - 基本功能测试
- `cleanup.sh` - 清理测试数据和进程
