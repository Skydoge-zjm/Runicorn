[English](../en/MIGRATION_GUIDE_v0.4_to_v0.5.md) | [简体中文](MIGRATION_GUIDE_v0.4_to_v0.5.md)

---

# Runicorn 0.4.x → 0.5.0 迁移指南

> **作者**: Runicorn Development Team  
> **版本**: v0.5.0  
> **最后更新**: 2025-10-25  
> **预计时间**: 30 分钟

---

## 📋 概述

Runicorn 0.5.0 引入了全新的 **Remote Viewer** 架构，替代了旧的 SSH 文件同步方式。这是一次重大升级，但向后兼容现有数据。

### 主要变化

| 方面 | 0.4.x | 0.5.0 |
|------|-------|-------|
| **远程访问** | SSH 文件同步 | Remote Viewer（VSCode Remote 风格）|
| **API 端点** | `/api/ssh/*` | `/api/remote/*` |
| **配置格式** | `ssh_config.json` | `config.yaml` (新增 remote 部分) |
| **数据格式** | 兼容 | 完全兼容，无需迁移 |
| **Python 版本** | 3.8+ | 3.8+ |

### 迁移特点

- ✅ **向后兼容**: 现有数据无需修改
- ✅ **逐步迁移**: 可以先升级再慢慢切换
- ✅ **旧 API 可用**: 0.5.0 中旧 API 仍可用（0.6.0 将移除）
- ⚠️ **Remote 需完整安装**: 远程服务器需要完整 Runicorn，不仅 SDK

---

## 🎯 谁需要迁移？

### 需要迁移
- ✅ 使用远程 SSH 同步功能的用户
- ✅ 使用 `/api/ssh/*` API 的开发者
- ✅ 有自定义集成脚本的用户

### 不需要迁移
- ✅ 仅本地使用的用户（自动升级即可）
- ✅ 不使用远程功能的用户

---

## ⚡ 快速迁移（5 分钟）

### 最小步骤

```bash
# 1. 备份数据（推荐）
runicorn export --format zip --output backup_before_v0.5.zip

# 2. 升级本地 Runicorn
pip install -U runicorn

# 3. 验证版本
runicorn --version
# 应显示: Runicorn 0.5.0

# 4. 如果使用远程功能，升级远程服务器
ssh user@remote-server "pip install -U runicorn"

# 5. 启动 Viewer
runicorn viewer

# 完成！现有数据自动兼容
```

---

## 📝 详细迁移步骤

### 步骤 1: 准备工作

#### 1.1 备份数据

**推荐备份整个数据目录**:
```bash
# Linux/macOS
tar -czf runicorn_backup_$(date +%Y%m%d).tar.gz ~/RunicornData

# 或使用导出功能
runicorn export \
  --format zip \
  --include-artifacts \
  --output backup_v0.4.zip
```

**Windows**:
```powershell
# PowerShell
Compress-Archive -Path "$env:USERPROFILE\RunicornData" `
  -DestinationPath "runicorn_backup_$(Get-Date -Format 'yyyyMMdd').zip"
```

#### 1.2 记录当前配置

```bash
# 查看当前配置
runicorn config --show > config_before_upgrade.txt

# 记录当前版本
runicorn --version >> config_before_upgrade.txt
```

#### 1.3 停止旧的同步任务（如果有）

如果你在 0.4.x 中设置了自动同步任务：

1. 打开 Viewer
2. 导航到"远程存储"或"SSH"页面
3. 停止所有活动的同步任务
4. 等待当前同步完成

---

### 步骤 2: 升级本地环境

#### 2.1 升级 Runicorn

```bash
# 使用 pip 升级
pip install --upgrade runicorn

# 如果使用虚拟环境
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate  # Windows
pip install --upgrade runicorn
```

#### 2.2 验证升级

```bash
# 检查版本
runicorn --version
# 应该显示: Runicorn 0.5.0

# 检查安装
python -c "import runicorn; print(runicorn.__version__)"
# 应该显示: 0.5.0

# 测试基本功能
runicorn config --validate
```

#### 2.3 查看变更日志

```bash
# 查看 0.5.0 的新特性
cat $(pip show runicorn | grep Location | cut -d' ' -f2)/runicorn/CHANGELOG.md
```

---

### 步骤 3: 升级远程服务器（如果使用远程功能）

#### 3.1 连接到远程服务器

```bash
# SSH 登录
ssh user@gpu-server.com

# 或批量升级多台服务器
for server in server1 server2 server3; do
  ssh user@$server "pip install -U runicorn"
done
```

#### 3.2 在远程服务器上升级

```bash
# 在远程服务器上执行

# 如果使用 conda
conda activate your-env
pip install --upgrade runicorn

# 如果使用 virtualenv
source ~/venv/bin/activate
pip install --upgrade runicorn

# 验证
runicorn --version
```

#### 3.3 确认远程环境

```bash
# 在远程服务器上
which python
python --version
runicorn --version

# 确保 Runicorn 0.5.0+ 可用
python -c "import runicorn; print(runicorn.__version__)"
```

**重要**: Remote Viewer 需要远程服务器上完整安装 Runicorn，不能只有 SDK！

---

### 步骤 4: 迁移配置

#### 4.1 理解配置变化

**旧配置 (0.4.x)**: `~/.config/runicorn/ssh_config.json`
```json
{
  "connections": [
    {
      "host": "gpu-server.com",
      "username": "user",
      "private_key_path": "~/.ssh/id_rsa"
    }
  ]
}
```

**新配置 (0.5.0)**: `~/.config/runicorn/config.yaml`
```yaml
remote:
  ssh_timeout: 30
  viewer_startup_timeout: 60
  health_check_interval: 30
  max_connections: 5
```

#### 4.2 配置迁移

**选项 1: 手动迁移（推荐）**

新版本的 Remote 连接通过 UI 配置，不再使用配置文件保存连接信息（安全考虑）。

你需要在 UI 中重新添加连接：
1. 启动 Viewer: `runicorn viewer`
2. 打开 Remote 页面
3. 手动添加 SSH 连接

**选项 2: 使用迁移脚本（如果有多个连接）**

```python
# migrate_ssh_config.py
import json
import yaml

# 读取旧配置
with open('~/.config/runicorn/ssh_config.json') as f:
    old_config = json.load(f)

# 打印迁移建议
print("请在 Web UI 中添加以下连接：")
for conn in old_config.get('connections', []):
    print(f"- 主机: {conn['host']}")
    print(f"  用户: {conn['username']}")
    print(f"  密钥: {conn.get('private_key_path', '~/.ssh/id_rsa')}")
    print()
```

#### 4.3 清理旧配置（可选）

```bash
# 备份旧配置
cp ~/.config/runicorn/ssh_config.json ~/.config/runicorn/ssh_config.json.backup

# 删除旧配置（可选）
rm ~/.config/runicorn/ssh_config.json
```

---

### 步骤 5: 使用 Remote Viewer

#### 5.1 启动本地 Viewer

```bash
runicorn viewer

# 或指定端口
runicorn viewer --port 23300
```

#### 5.2 连接远程服务器

**通过 Web UI**:

1. 打开浏览器: `http://localhost:23300`
2. 点击顶部的"Remote"按钮
3. 点击"添加连接"
4. 填写表单:
   ```
   主机名: gpu-server.com
   端口: 22
   用户名: your-username
   认证方式: SSH 密钥 / 密码
   ```
5. 点击"连接"

#### 5.3 选择环境并启动

1. 系统自动检测远程 Python 环境（2-5 秒）
2. 从列表中选择包含 Runicorn 的环境
3. 点击"启动 Remote Viewer"
4. 等待 5-10 秒
5. 自动打开新浏览器标签页

**完成！** 现在可以实时访问远程数据了。

---

### 步骤 6: 验证迁移

#### 6.1 测试基本功能

```bash
# 1. 本地 Viewer 工作正常
runicorn viewer
# 打开 http://localhost:23300，查看本地实验

# 2. 配置正确
runicorn config --validate

# 3. 数据完整
runicorn export --format json --output test_export.json
```

#### 6.2 测试 Remote Viewer（如果使用）

1. 连接到远程服务器
2. 查看实验列表
3. 打开一个实验详情
4. 查看实时日志
5. 查看指标图表

#### 6.3 性能对比

**旧方式 (SSH 同步)**:
```bash
# 首次同步可能需要几分钟到几小时
```

**新方式 (Remote Viewer)**:
```bash
# 连接时间: 5-10 秒
# 打开实验: 即时
# 查看日志: 实时流式传输
```

---

## 🔄 API 迁移

### API 端点对应表

| 功能 | 0.4.x API | 0.5.0 API | 状态 |
|------|-----------|-----------|------|
| 建立连接 | `POST /api/ssh/connect` | `POST /api/remote/connect` | 旧 API 已弃用 |
| 获取状态 | `GET /api/ssh/status` | `GET /api/remote/viewer/status` | 旧 API 已弃用 |
| 启动同步 | `POST /api/ssh/sync` | 已移除 | 不再需要同步 |
| 查询任务 | `GET /api/ssh/tasks` | 已移除 | 不再有同步任务 |
| 列出环境 | N/A | `GET /api/remote/environments` | 新增 |
| 启动 Viewer | N/A | `POST /api/remote/viewer/start` | 新增 |

### 代码迁移示例

#### 旧代码 (0.4.x)

```python
import requests

# 连接并同步
response = requests.post(
    "http://localhost:23300/api/ssh/connect",
    json={
        "host": "gpu-server.com",
        "username": "user",
        "password": "secret"
    }
)
connection_id = response.json()["connection_id"]

# 启动同步
sync_response = requests.post(
    "http://localhost:23300/api/ssh/sync",
    json={
        "connection_id": connection_id,
        "remote_dir": "/home/user/RunicornData",
        "local_dir": "~/RunicornData"
    }
)
task_id = sync_response.json()["task_id"]

# 轮询同步状态
import time
while True:
    status = requests.get(
        f"http://localhost:23300/api/ssh/tasks/{task_id}"
    ).json()
    if status["status"] in ["completed", "failed"]:
        break
    time.sleep(5)

print("同步完成，现在可以查看实验")
```

#### 新代码 (0.5.0)

```python
import requests

# 连接
response = requests.post(
    "http://localhost:23300/api/remote/connect",
    json={
        "host": "gpu-server.com",
        "port": 22,
        "username": "user",
        "auth_method": "password",
        "password": "secret"
    }
)
connection_id = response.json()["connection_id"]

# 列出环境
envs = requests.get(
    "http://localhost:23300/api/remote/environments",
    params={"connection_id": connection_id}
).json()

# 选择第一个兼容的环境
compatible_env = next(e for e in envs if e["is_compatible"])

# 启动 Remote Viewer
viewer = requests.post(
    "http://localhost:23300/api/remote/viewer/start",
    json={
        "connection_id": connection_id,
        "env_name": compatible_env["name"]
    }
).json()

print(f"Remote Viewer 已启动: {viewer['viewer_url']}")
print("可以直接访问，无需等待同步！")
```

**主要区别**:
- ✅ 无需同步步骤
- ✅ 即时访问（5-10 秒 vs 数分钟）
- ✅ 实时数据（无延迟）
- ✅ 节省本地存储

---

## 🐛 常见问题和解决方案

### 问题 1: 升级后 Viewer 无法启动

**症状**: `runicorn viewer` 报错

**解决方案**:
```bash
# 1. 检查端口是否被占用
lsof -i :23300  # Linux/macOS
netstat -ano | findstr :23300  # Windows

# 2. 尝试其他端口
runicorn viewer --port 23301

# 3. 检查配置
runicorn config --validate

# 4. 重置配置
runicorn config --reset
```

---

### 问题 2: Remote 连接失败

**症状**: 无法连接到远程服务器

**解决方案**:
```bash
# 1. 测试 SSH 连接
ssh user@remote-server

# 2. 检查远程 Runicorn 版本
ssh user@remote-server "runicorn --version"
# 必须是 0.5.0 或更高

# 3. 检查远程 Runicorn 安装
ssh user@remote-server "python -c 'import runicorn; print(runicorn.__version__)'"

# 4. 如果版本不对，升级
ssh user@remote-server "pip install -U runicorn"

# 5. 查看详细错误
runicorn viewer --log-level DEBUG
```

---

### 问题 3: 找不到兼容的远程环境

**症状**: "No compatible environments found"

**解决方案**:
```bash
# 在远程服务器上
# 1. 列出所有 Python 环境
conda env list  # 如果使用 conda
ls ~/venv/  # 如果使用 virtualenv

# 2. 在每个环境中安装 Runicorn
conda activate your-env
pip install runicorn

# 或
source ~/venv/bin/activate
pip install runicorn

# 3. 验证安装
runicorn --version
```

---

### 问题 4: 数据丢失担忧

**解答**: 数据不会丢失！

- ✅ 所有现有数据 100% 兼容
- ✅ 升级不会修改或删除任何数据
- ✅ 可以随时回退到 0.4.x

**验证数据完整性**:
```bash
# 导出并检查
runicorn export --format json --output check.json

# 查看实验数量
python -c "
import json
with open('check.json') as f:
    data = json.load(f)
    print(f'Total experiments: {len(data.get(\"experiments\", []))}')
"
```

---

### 问题 5: 旧的 API 脚本还能用吗？

**解答**: 0.5.0 中仍可用，但已弃用。

**时间线**:
- **0.5.0**: 旧 API 可用但标记为弃用
- **0.5.x**: 显示弃用警告
- **0.6.0**: 旧 API 将被移除

**建议**: 尽快迁移到新 API。

---

## 📊 性能改进

### 远程访问性能对比

| 操作 | 0.4.x (SSH 同步) | 0.5.0 (Remote Viewer) | 改进 |
|------|-----------------|---------------------|------|
| **初次连接** | 5-60 分钟 | 5-10 秒 | **360x 更快** |
| **查看新实验** | 需要重新同步 | 即时 | **实时** |
| **存储占用** | 本地副本（GB）| 零 | **100% 节省** |
| **实时性** | 5-10 分钟延迟 | 完全实时 | **零延迟** |
| **多人协作** | 容易冲突 | 无冲突 | **更可靠** |

### 本地使用性能

本地使用（无远程）性能保持不变或更好：
- ✅ V2 API (SQLite) 查询速度提升 100 倍
- ✅ 改进的缓存机制
- ✅ 优化的文件 I/O

---

## 🎓 学习新功能

### Remote Viewer 核心概念

**工作原理**:
1. 在远程服务器启动临时 Viewer（仅 127.0.0.1）
2. 通过 SSH 隧道转发端口到本地
3. 本地浏览器访问，体验与本地无异
4. 断开后自动清理远程资源

**优势**:
- 🚀 即时连接（5-10 秒）
- 💾 零本地存储占用
- 🔄 完全实时数据
- 🔒 安全（SSH 加密）
- 🧹 自动清理

### 推荐资源

- 📚 [Remote Viewer 用户指南](REMOTE_VIEWER_GUIDE.md)
- 🏗️ [Remote Viewer 架构](../../architecture/zh/REMOTE_VIEWER_ARCHITECTURE.md)
- ❓ [FAQ](../../reference/zh/FAQ.md)
- 🔧 [API 参考](../../api/zh/remote_api.md)

---

## 🔙 回退方案

如果需要回退到 0.4.x：

```bash
# 1. 卸载 0.5.0
pip uninstall runicorn

# 2. 安装 0.4.x
pip install runicorn==0.4.1

# 3. 验证
runicorn --version
```

**注意**: 
- 0.5.0 创建的数据在 0.4.x 中仍可访问
- Remote Viewer 的连接信息不会迁移回去
- 建议保留备份

---

## ✅ 迁移检查清单

完成迁移前，确保：

- [ ] 已备份所有数据
- [ ] 本地 Runicorn 升级到 0.5.0
- [ ] 远程服务器（如使用）升级到 0.5.0
- [ ] 配置已验证（`runicorn config --validate`）
- [ ] 本地 Viewer 可以正常启动
- [ ] Remote 连接测试成功（如使用）
- [ ] 可以查看现有实验
- [ ] 可以创建新实验
- [ ] API 脚本已更新（如有）
- [ ] 团队成员已通知

---

## 🆘 获取帮助

遇到问题？

**文档**:
- 📖 [完整文档](../../README.md)
- ❓ [FAQ](../../reference/zh/FAQ.md)
- 🔧 [故障排查](../../reference/zh/TROUBLESHOOTING.md)

**社区**:
- 💬 [GitHub Issues](https://github.com/Skydoge-zjm/runicorn/issues)
- 📧 Email: support@runicorn.dev

**报告问题时请包含**:
```bash
# 生成诊断报告
runicorn --version > diagnostics.txt
runicorn config --show >> diagnostics.txt
python --version >> diagnostics.txt
uname -a >> diagnostics.txt  # Linux/macOS
```

---

## 🎉 迁移完成

恭喜！你已成功迁移到 Runicorn 0.5.0。

**享受新功能**:
- 🌐 Remote Viewer（类似 VSCode Remote）
- ⚡ 即时远程访问
- 💾 零本地存储占用
- 🔄 完全实时数据
- 🎯 更好的用户体验

**反馈**: 欢迎分享你的迁移体验和建议！

---

**作者**: Runicorn Development Team  
**版本**: v0.5.0  
**最后更新**: 2025-10-25

---

**返回**: [用户指南索引](README.md) | [主文档](../../README.md)


