# Remote Viewer Tests

完整的 Remote Viewer 测试套件，分为服务器端（WSL）和客户端（Windows）测试。

## ⚠️ 重要：API 使用规范

**在编写测试脚本前，请先阅读：[API_USAGE_GUIDE.md](API_USAGE_GUIDE.md)**

标准 API 使用方式：
```python
import runicorn as rn

run = rn.init(project="test", name="exp1")   # ✅ 初始化
run.log({"param": "value"}, step=0)          # ✅ 记录配置
run.log({"loss": 0.5}, step=1)               # ✅ 记录指标
run.summary({"best_loss": 0.5})              # ✅ 记录汇总
run.finish()                                 # ✅ 完成
print(run.id)                                # ✅ 访问 ID

# ❌ 常见错误
from runicorn import Run
run = Run(...)              # ❌ 不要直接实例化 Run
print(run.run_id)           # ❌ 使用 run.id 而不是 run.run_id
```

## 目录结构

```
tests/
├── server/               # WSL 服务器端测试
│   ├── setup_test_data.py           # 创建测试数据
│   ├── start_remote_viewer.py       # 启动远程 viewer
│   ├── test_remote_viewer_basic.py  # 基础功能测试
│   └── cleanup.sh                   # 清理脚本
│
├── client/               # Windows 客户端测试
│   ├── config.json.example          # 配置文件示例
│   ├── test_ssh_connection.py       # SSH 连接测试
│   ├── test_connection_pool.py      # 连接池测试
│   ├── test_remote_viewer_connection.py  # 完整流程测试
│   ├── test_remote_viewer_api.py    # API 端点测试
│   └── run_all_tests.py             # 运行所有测试
│
└── README.md            # 本文件
```

## 快速开始

### 步骤 1：准备 WSL 环境

在 WSL 中执行：

```bash
# 1. 进入项目目录
cd /mnt/e/pycharm_project/Runicorn

# 2. 安装 runicorn（开发模式）
pip install -e .

# 3. 创建测试数据
python tests/server/setup_test_data.py

# 4. （可选）测试远程 viewer 基本功能
python tests/server/start_remote_viewer.py --port 8080
# 在另一个终端：
python tests/server/test_remote_viewer_basic.py --port 8080
```

### 步骤 2：配置客户端

在 Windows 上执行：

```powershell
# 1. 复制配置文件
cd E:\pycharm_project\Runicorn\tests\client
copy config.json.example config.json

# 2. 编辑 config.json，填入你的 WSL 信息
# 必填项：
#   - wsl_username: 你的 WSL 用户名
#   - wsl_password 或 wsl_key_path: SSH 认证方式
#   - remote_root: 测试数据路径（默认 ~/runicorn_test_data）
```

**config.json 示例：**

```json
{
  "wsl_host": "localhost",
  "wsl_port": 22,
  "wsl_username": "yourname",
  "wsl_password": null,
  "wsl_key_path": "C:/Users/YourName/.ssh/id_rsa",
  "remote_root": "/home/yourname/runicorn_test_data",
  "remote_port": 8080,
  "local_port": 18080
}
```

### 步骤 3：运行客户端测试

```powershell
# 运行单个测试
python tests/client/test_ssh_connection.py
python tests/client/test_connection_pool.py
python tests/client/test_remote_viewer_connection.py

# 或运行全部测试（推荐）
python tests/client/run_all_tests.py
```

### 步骤 4：测试 API 端点

```powershell
# 1. 启动本地 viewer（另一个终端）
python -m runicorn viewer --port 23300

# 2. 测试 Remote API
python tests/client/test_remote_viewer_api.py
```

## 测试内容

### 服务器端测试（WSL）

| 测试文件 | 功能 | 描述 |
|---------|------|------|
| `setup_test_data.py` | 数据准备 | 创建 3 个示例实验 |
| `start_remote_viewer.py` | 启动 viewer | 以 remote-mode 启动 |
| `test_remote_viewer_basic.py` | 基础测试 | Health、列表、指标查询 |

### 客户端测试（Windows）

| 测试文件 | 功能 | 测试内容 |
|---------|------|---------|
| `test_ssh_connection.py` | SSH 连接 | 连接、命令执行、SFTP、环境检查 |
| `test_connection_pool.py` | 连接池 | 连接复用、健康检查、清理 |
| `test_remote_viewer_connection.py` | 完整流程 | 启动远程 viewer、SSH 隧道、访问、清理 |
| `test_remote_viewer_api.py` | API 端点 | 测试所有 `/api/remote/*` 端点 |

## 故障排查

### 问题 1：SSH 连接失败

```
❌ SSH connection failed: ...
```

**解决方案：**
- 检查 WSL SSH 服务是否运行：`sudo service ssh status`
- 启动 SSH 服务：`sudo service ssh start`
- 检查防火墙设置
- 验证认证信息（用户名、密码或密钥）

### 问题 2：runicorn 未安装

```
❌ Runicorn not installed on remote
```

**解决方案：**
```bash
# 在 WSL 中
cd /mnt/e/pycharm_project/Runicorn
pip install -e .
```

### 问题 3：测试数据不存在

```
⚠️ Test data directory not found
```

**解决方案：**
```bash
# 在 WSL 中
python tests/server/setup_test_data.py
```

### 问题 4：端口已被占用

```
❌ Address already in use
```

**解决方案：**
```bash
# 查找占用端口的进程
lsof -i:8080
# 或
netstat -ano | findstr :8080

# 杀掉进程
kill <PID>
```

### 问题 5：隧道连接失败

```
❌ Cannot connect to remote viewer
```

**解决方案：**
- 检查远程 viewer 是否启动：`ps aux | grep runicorn`
- 检查远程端口是否监听：`netstat -tuln | grep 8080`
- 增加等待时间（tunnel 建立需要几秒）
- 检查防火墙规则

## 清理测试环境

### WSL 端清理

```bash
# 使用清理脚本
cd /mnt/e/pycharm_project/Runicorn
bash tests/server/cleanup.sh

# 或手动清理
pkill -f "runicorn viewer"
rm -rf ~/runicorn_test_data
rm -f /tmp/runicorn_viewer_*.log
```

### Windows 端清理

无需特殊清理，测试会自动断开连接和清理会话。

## 测试覆盖范围

✅ **已覆盖：**
- SSH 连接与认证（密码、密钥、Agent）
- SSH 连接池与复用
- 远程命令执行
- SFTP 文件操作
- 远程 viewer 启动与管理
- SSH 隧道建立
- Remote Viewer API 端点
- 会话管理与清理

⏳ **待测试（Phase 4）：**
- 前端 UI 集成
- 多会话并发
- 长时间稳定性
- 网络中断恢复
- 性能压力测试

## 下一步

测试通过后，可以：

1. **提交代码**
   ```bash
   git add tests/
   git commit -m "test: add Remote Viewer test suite"
   ```

2. **继续开发 Phase 4**
   - 前端 Remote Viewer UI
   - 会话管理界面
   - 远程路径选择器

3. **文档更新**
   - 更新用户文档
   - 添加 Remote Viewer 使用指南

---

**测试愉快！** 🚀
