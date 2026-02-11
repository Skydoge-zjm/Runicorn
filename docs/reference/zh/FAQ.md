[English](../en/FAQ.md) | [简体中文](FAQ.md)

---

# Runicorn 常见问题（FAQ）

**文档类型**: 参考  
**版本**: v0.5.3  
**最后更新**: 2025-11-28

---

## 目录

- [基础问题](#基础问题)
- [安装和配置](#安装和配置)
- [Remote Viewer（v0.5.0）](#remote-viewer-v050)
- [数据管理](#数据管理)
- [性能问题](#性能问题)
- [故障排查](#故障排查)
- [高级使用](#高级使用)

---

## 基础问题

### Q1: Runicorn 是什么？

**A**: Runicorn 是一个轻量级的机器学习实验追踪工具，提供：
- 🚀 零配置实验追踪
- 📊 实时可视化仪表板
- 🗄️ 高性能数据存储（SQLite + 文件）
- 🔄 Artifact 版本控制
- 🌐 Remote Viewer（类似 VSCode Remote）
- 🔒 100% 本地，保护隐私

---

### Q2: Runicorn 与 W&B、MLflow 有什么区别？

**A**: 

| 特性 | W&B | MLflow | Runicorn |
|------|-----|--------|----------|
| **部署** | 云端 SaaS | 需要服务器 | 本地零配置 |
| **隐私** | 数据在云端 | 可自托管 | 100% 本地 |
| **成本** | $50+/用户/月 | 免费开源 | 免费开源 |
| **安装** | 注册账号 | 配置服务器 | `pip install` |
| **Remote** | 云端访问 | 需配置 | VSCode Remote 风格 |

**适合场景**:
- ✅ 个人研究者或小团队
- ✅ 对数据隐私有要求
- ✅ 不想依赖外部服务
- ✅ 需要远程服务器访问

---

### Q3: Runicorn 支持哪些 ML 框架？

**A**: Runicorn 是框架无关的，支持：
- ✅ PyTorch
- ✅ TensorFlow / Keras
- ✅ JAX
- ✅ scikit-learn
- ✅ Hugging Face Transformers
- ✅ 任何 Python 代码

**示例**:
```python
import runicorn as rn
import torch

run = rn.init(project="training", name="experiment-1")

for epoch in range(10):
    # 你的训练代码
    loss = train_one_epoch()
    
    # 记录指标
    run.log({"loss": loss, "epoch": epoch})

run.finish()
```

---

## 安装和配置

### Q4: 如何安装 Runicorn？

**A**: 
```bash
# 基本安装
pip install runicorn

# 从源码安装
git clone https://github.com/Skydoge-zjm/runicorn.git
cd runicorn
pip install -e .

# 验证安装
runicorn --version
```

**系统要求**:
- Python 3.8+
- Windows / Linux / macOS

---

### Q5: 如何配置存储路径？

**A**: 三种方式：

**方法 1：命令行**
```bash
runicorn viewer --storage-root /data/experiments
```

**方法 2：环境变量**
```bash
export RUNICORN_USER_ROOT_DIR=/data/experiments
runicorn viewer
```

**方法 3：配置文件**
```yaml
# ~/.config/runicorn/config.yaml
storage:
  user_root_dir: /data/experiments
```

---

### Q6: 如何更改 Viewer 端口？

**A**: 

```bash
# 方法 1: 命令行
runicorn viewer --port 8080

# 方法 2: 环境变量
export RUNICORN_VIEWER_PORT=8080
runicorn viewer

# 方法 3: 配置文件
viewer:
  port: 8080
```

---

## Remote Viewer（v0.5.0）

### Q7: Remote Viewer 和旧的远程同步有什么区别？

**A**: 完全不同的架构！

| 特性 | 旧版本 (0.4.x) | Remote Viewer (0.5.0) |
|------|----------------|---------------------|
| **架构** | SSH 文件同步 | VSCode Remote 风格 |
| **数据位置** | 本地副本 | 远程服务器 |
| **同步时间** | 数分钟到数小时 | 5-10 秒连接 |
| **存储需求** | 大（本地副本）| 零（无本地存储）|
| **实时性** | 延迟 5-10 分钟 | 完全实时 |
| **体验** | 需要等待同步 | 即时访问 |

**工作原理**:
1. 在远程服务器启动临时 Viewer（仅 127.0.0.1）
2. 通过 SSH 隧道转发端口到本地
3. 本地浏览器访问，体验与本地无异
4. 无需文件传输，直接读取远程数据

---

### Q8: Remote Viewer 有哪些要求？

**A**: 

**本地机器**:
- ✅ Python 3.8+
- ✅ Runicorn 0.5.0+
- ✅ SSH 客户端（系统自带）

**远程服务器**:
- ✅ Linux 或 WSL
- ✅ Python 3.8+
- ✅ **Runicorn 0.5.0+（完整安装）**
- ✅ SSH 服务器运行

**网络**:
- ✅ 稳定的 SSH 连接
- ✅ SSH 端口访问权限（通常是 22）

**注意**: 远程服务器必须完整安装 Runicorn，不能只有 SDK！

---

### Q9: 如何使用 Remote Viewer？

**A**: 

**步骤 1：确保远程安装 Runicorn**
```bash
# SSH 登录到远程服务器
ssh user@gpu-server.com

# 安装 Runicorn
pip install runicorn

# 验证
runicorn --version  # 应显示 0.5.0+
```

**步骤 2：在本地启动 Viewer**
```bash
runicorn viewer
```

**步骤 3：连接远程服务器**
1. 打开浏览器: `http://localhost:23300`
2. 点击 "Remote" 按钮
3. 填写 SSH 信息:
   - 主机：`gpu-server.com`
   - 用户名：`your-username`
   - 认证方式：选择"SSH 密钥"或"密码"
4. 点击"连接"

**步骤 4：选择环境并启动**
- 系统自动检测远程 Python 环境
- 选择包含 Runicorn 的环境
- 点击"启动 Remote Viewer"
- 系统自动打开新标签页

**完成！** 现在可以实时查看远程数据了。

---

### Q10: Remote Viewer 支持 Windows 远程服务器吗？

**A**: 目前不支持，仅支持 Linux 和 WSL。

**当前支持**:
- ✅ Linux（Ubuntu, CentOS, Debian 等）
- ✅ WSL (Windows Subsystem for Linux)

**不支持**:
- ❌ Windows 原生服务器
- ❌ macOS 服务器（计划中）

**为什么**: Remote Viewer 依赖 Linux 特定的功能（进程管理、端口监听等）。

**Windows 用户的替代方案**:
1. 使用 WSL2 作为远程服务器
2. 等待未来版本支持（在路线图中）

---

### Q11: 可以同时连接多台服务器吗？

**A**: 可以！每个连接使用不同的本地端口。

**示例**:
```
本地 Viewer (localhost:23300)
├── GPU Server 1 → localhost:8081
├── GPU Server 2 → localhost:8082
└── GPU Server 3 → localhost:8083
```

**使用方式**:
1. 连接第一台服务器 → 自动分配 `localhost:8081`
2. 连接第二台服务器 → 自动分配 `localhost:8082`
3. 以此类推...

**限制**: 默认最多 5 个并发连接（可在配置中调整）

---

### Q12: 断开连接后数据会丢失吗？

**A**: 不会！数据始终在远程服务器上。

**断开连接时**:
1. SSH 隧道关闭
2. 远程 Viewer 进程停止
3. 临时文件自动清理

**重新连接时**:
- 数据完整保留
- 重新连接即可继续访问
- 无需重新同步

**数据位置**: 始终在远程服务器的 `~/RunicornData`（或配置的路径）

---

### Q13: Remote Viewer 安全吗？

**A**: 是的，非常安全！

**安全措施**:
- ✅ **SSH 加密**: 所有通信通过 SSH 加密
- ✅ **本地监听**: 远程 Viewer 只监听 `127.0.0.1`，不对外暴露
- ✅ **无公网暴露**: 不开放额外端口到公网
- ✅ **SSH 密钥支持**: 推荐使用 SSH 密钥认证
- ✅ **密码不存储**: 密码仅在内存中，不持久化
- ✅ **自动清理**: 断开后自动清理远程资源

**最佳实践**:
1. 使用 SSH 密钥而非密码
2. 配置 SSH Keep-alive
3. 仅在可信网络中使用
4. 定期更新 Runicorn

---

### Q14: Remote Viewer 性能如何？

**A**: 性能优秀，接近本地体验。

**延迟测试**（实际测量）:

| 网络环境 | 延迟增加 | 体验 |
|---------|---------|------|
| 局域网 | +20-50ms | 几乎无感知 |
| 同城 | +50-100ms | 流畅 |
| 跨省 | +100-300ms | 良好 |
| 跨国 | +300-500ms | 可接受 |

**带宽使用**:
- 空闲时: < 1 KB/s
- 浏览实验列表: ~50-100 KB/s
- 查看实时图表: ~100-500 KB/s
- 下载模型文件: 全速（取决于网络）

**CPU 使用**:
- 远程服务器: < 5%
- 本地机器: < 2%

---

## 数据管理

### Q15: 实验数据存储在哪里？

**A**: 

**默认位置**:
- Linux/macOS: `~/RunicornData`
- Windows: `%USERPROFILE%\RunicornData`

**数据结构**:
```
RunicornData/
├── runicorn.db              # SQLite 数据库
├── project1/
│   └── experiment1/
│       └── runs/
│           └── 20251025_143022_abc123/
│               ├── meta.json
│               ├── summary.json
│               ├── events.jsonl
│               ├── logs.txt
│               └── media/
└── artifacts/               # Artifact 存储
    └── model/
        └── my-model/
            └── v1/
```

---

### Q16: 如何备份数据？

**A**: 三种方法：

**方法 1：使用 export 命令**
```bash
runicorn export \
  --format zip \
  --include-artifacts \
  --output backup_$(date +%Y%m%d).zip
```

**方法 2：直接复制目录**
```bash
# 备份整个数据目录
tar -czf runicorn_backup.tar.gz ~/RunicornData

# 或使用 rsync
rsync -av ~/RunicornData/ /backup/runicorn/
```

**方法 3：自动备份**
```yaml
# config.yaml
storage:
  auto_backup: true
  backup_interval_hours: 24
  max_backups: 7
```

---

### Q17: 如何清理旧数据？

**A**: 

**清理僵尸实验**:
```bash
runicorn clean --zombie
```

**清理超过 30 天的数据**:
```bash
runicorn clean --older-than 30
```

**清理临时文件和缓存**:
```bash
runicorn clean --temp --cache
```

**预览清理**:
```bash
runicorn clean --zombie --dry-run
```

---

### Q18: Artifacts 去重如何工作？

**A**: Runicorn 使用基于内容的去重（Content-Addressable Storage）。

**工作原理**:
1. 计算文件 SHA256 哈希
2. 检查去重池是否已存在
3. 如存在，创建硬链接（零拷贝）
4. 如不存在，复制文件到去重池

**效果**:
- 节省 50-90% 存储空间
- 预训练模型共享权重
- 多个检查点去重

**示例**:
```
不去重: 10 个模型检查点 = 10 GB
去重后: 10 个模型检查点 = 1.5 GB (节省 85%)
```

---

## 性能问题

### Q19: 为什么实验列表加载很慢？

**A**: 可能是使用了 V1 API（文件扫描）。

**解决方案：启用 V2 API（SQLite）**

**检查当前 API 版本**:
```bash
runicorn config --show | grep "Database"
```

**启用 V2 API**:
```yaml
# config.yaml
storage:
  use_database: true
```

**性能对比**:
- V1 (1000 个实验): ~5-10 秒
- V2 (1000 个实验): ~50 毫秒
- **提升 100 倍！**

---

### Q20: WebSocket 连接频繁断开怎么办？

**A**: 

**增加超时时间**:
```yaml
# config.yaml
performance:
  websocket_timeout: 600  # 10 分钟
```

**检查网络稳定性**:
```bash
# 测试连接稳定性
ping -c 100 remote-server.com
```

**使用 SSH Keep-alive**:
```yaml
# config.yaml
remote:
  ssh_keepalive_interval: 30  # 30 秒
```

---

## 故障排查

### Q21: 连接远程服务器失败怎么办？

**A**: 按顺序排查：

**1. 测试 SSH 连接**
```bash
ssh user@remote-server
```
如果失败，检查：
- 主机名或 IP 是否正确
- SSH 服务是否运行
- 防火墙规则
- 网络连接

**2. 检查远程 Runicorn**
```bash
ssh user@remote-server "runicorn --version"
```
应输出 `Runicorn 0.5.0` 或更高版本

**3. 检查 Python 环境**
```bash
ssh user@remote-server "which python"
ssh user@remote-server "python --version"
```

**4. 查看详细错误**
```bash
# 本地启动 Debug 模式
runicorn viewer --log-level DEBUG
```

**5. 查看远程日志**
```bash
ssh user@remote-server "cat /tmp/runicorn_viewer_*.log"
```

---

### Q22: Viewer 启动失败怎么办？

**A**: 

**错误: "Port already in use"**
```bash
# 检查端口占用
lsof -i :23300  # Linux/macOS
netstat -ano | findstr :23300  # Windows

# 使用其他端口
runicorn viewer --port 23301
```

**错误: "Permission denied"**
```bash
# 检查目录权限
ls -la ~/RunicornData

# 修复权限
chmod -R 755 ~/RunicornData
```

**错误: "Database locked"**
```bash
# 检查是否有其他 Viewer 实例
ps aux | grep "runicorn viewer"

# 杀死其他实例
killall runicorn  # Linux/macOS
taskkill /F /IM runicorn.exe  # Windows
```

---

### Q23: 如何查看详细日志？

**A**: 

**启动 Debug 模式**:
```bash
runicorn viewer --log-level DEBUG
```

**查看日志文件**:
```bash
# Linux/macOS
tail -f ~/.config/runicorn/logs/runicorn.log

# Windows
type %APPDATA%\Runicorn\logs\runicorn.log
```

**查看远程 Viewer 日志**:
```bash
ssh user@remote-server \
  "tail -f /tmp/runicorn_viewer_*.log"
```

---

## 高级使用

### Q24: 如何在 Jupyter Notebook 中使用？

**A**: 

```python
import runicorn as rn

# 初始化（在第一个单元格）
run = rn.init(project="research", name="experiment-1")

# 记录指标（任意单元格）
run.log({"loss": 0.5, "accuracy": 0.9})

# 记录图片
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [4, 5, 6])
run.log_image("plot", fig)

# 完成（最后一个单元格）
run.finish()
```

**自动捕获输出**:
```python
# 捕获 cell 输出
run = rn.init(project="notebook", capture_output=True)
```

---

### Q25: 如何集成到训练脚本中？

**A**: 

**基本集成**:
```python
import runicorn as rn

def train():
    # 初始化
    run = rn.init(project="training", name="resnet-50")
    
    # 记录超参数
    run.config.update({
        "learning_rate": 0.001,
        "batch_size": 32,
        "epochs": 100
    })
    
    try:
        for epoch in range(100):
            # 训练
            train_loss = train_one_epoch()
            val_loss = validate()
            
            # 记录指标
            run.log({
                "train/loss": train_loss,
                "val/loss": val_loss,
                "epoch": epoch
            }, step=epoch)
            
            # 保存检查点
            torch.save(model.state_dict(), f"checkpoint_{epoch}.pth")
            
        run.finish(status="success")
    except Exception as e:
        run.finish(status="failed", error=str(e))
        raise

if __name__ == "__main__":
    train()
```

---

### Q26: 如何使用 Artifact 版本控制？

**A**: 

**创建 Artifact**:
```python
import runicorn as rn

run = rn.init(project="training")

# 训练模型...

# 创建 Artifact
artifact = rn.Artifact(
    name="my-model",
    type="model",
    description="ResNet-50 trained on ImageNet"
)

# 添加文件
artifact.add_file("model.pth")
artifact.add_file("config.json")

# 记录 Artifact（自动版本化）
run.log_artifact(artifact)

run.finish()
```

**使用 Artifact**:
```python
run = rn.init(project="inference")

# 加载最新版本
artifact = run.use_artifact("my-model:latest")

# 或加载特定版本
artifact = run.use_artifact("my-model:v3")

# 下载并使用
model_path = artifact.download()
model = torch.load(f"{model_path}/model.pth")

run.finish()
```

---

### Q27: 如何从 0.4.x 迁移到 0.5.0？

**A**: 参考 [迁移指南](../../guides/zh/MIGRATION_GUIDE_v0.4_to_v0.5.md)

**快速步骤**:

1. **升级 Runicorn**:
   ```bash
   pip install -U runicorn
   ```

2. **远程服务器也升级**:
   ```bash
   ssh user@remote "pip install -U runicorn"
   ```

3. **停止旧的同步任务**

4. **使用新的 Remote Viewer**

**注意**: 旧的数据仍然兼容，无需迁移！

---

## 获取帮助

### Q28: 在哪里获取帮助？

**A**: 

**文档**:
- 📚 [用户指南](../../guides/zh/)
- 🔧 [API 参考](../../api/zh/)
- 🏗️ [架构文档](../../architecture/zh/)

**社区**:
- 💬 GitHub Issues: https://github.com/Skydoge-zjm/runicorn/issues
- 📧 Email: support@runicorn.dev
- 🐦 Twitter: @runicorn

**诊断信息**:
```bash
# 生成诊断报告
runicorn config --show > diagnosis.txt
runicorn --version >> diagnosis.txt
```

---

### Q29: 如何报告 Bug？

**A**: 

**报告 Bug 前**:
1. 搜索已存在的 Issues
2. 尝试重现问题
3. 收集诊断信息

**提交 Issue 时包含**:
```markdown
## 环境信息
- OS: Ubuntu 22.04
- Python: 3.10.12
- Runicorn: 0.5.0

## 问题描述
简洁描述问题...

## 重现步骤
1. 执行命令: `runicorn viewer`
2. 打开浏览器...
3. 点击 Remote...

## 预期行为
应该...

## 实际行为
但是...

## 日志
```
[粘贴相关日志]
```
```

---

### Q30: 如何贡献代码？

**A**: 欢迎贡献！

参考 [贡献指南](../../../CONTRIBUTING.md)

**快速开始**:
```bash
# 1. Fork 仓库
# 2. 克隆到本地
git clone https://github.com/Skydoge-zjm/runicorn.git
cd runicorn

# 3. 安装开发依赖
pip install -e ".[dev]"

# 4. 创建分支
git checkout -b feature/my-feature

# 5. 编写代码和测试
pytest tests/

# 6. 提交 Pull Request
```

---

**没有找到答案？** 

查看 [完整文档](../../README.md) 或 [提交 Issue](https://github.com/Skydoge-zjm/runicorn/issues/new)

---

**返回**: [参考文档索引](README.md) | [主文档](../../README.md)


