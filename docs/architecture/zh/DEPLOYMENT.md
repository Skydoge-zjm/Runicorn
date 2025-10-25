[English](../en/DEPLOYMENT.md) | [简体中文](DEPLOYMENT.md)

---

# 部署架构

**文档类型**: 架构  
**目的**: 记录部署选项和生产考虑

---

## 部署选项

Runicorn 支持多种部署场景：

1. **本地开发** - 单用户，本地机器
2. **共享服务器** - 团队通过网络访问
3. **桌面应用** - 原生 Windows 应用
4. **远程训练 + 本地查看** - SSH 同步

---

## 本地开发部署

### 架构

```
┌─────────────────────────────────┐
│   开发者机器                     │
│                                 │
│   ┌─────────────────────────┐  │
│   │ Python 进程             │  │
│   │ - SDK（训练代码）       │  │
│   │ - 写入本地文件          │  │
│   └─────────────────────────┘  │
│                                 │
│   ┌─────────────────────────┐  │
│   │ Runicorn Viewer         │  │
│   │ - FastAPI 服务器        │  │
│   │ - 在 127.0.0.1 上服务   │  │
│   └─────────────────────────┘  │
│                                 │
│   ┌─────────────────────────┐  │
│   │ 浏览器                  │  │
│   │ - React UI              │  │
│   │ - localhost:23300       │  │
│   └─────────────────────────┘  │
│                                 │
│   存储: ./RunicornData         │
└─────────────────────────────────┘
```

### 设置

```bash
# 安装
pip install runicorn

# 配置存储
runicorn config --set-user-root "E:\RunicornData"

# 启动 viewer
runicorn viewer

# 打开浏览器
http://127.0.0.1:23300
```

### 特点

- ✅ **简单**: 一个命令启动
- ✅ **私密**: 无网络暴露
- ✅ **快速**: 无网络延迟
- ⚠️ **单用户**: 无并发访问

---

## 共享服务器部署

### 架构

```
┌────────────────────────────────────────────────┐
│         实验室服务器 (Linux/Windows)            │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │ Runicorn Viewer（后台服务）              │ │
│  │ - 绑定到 0.0.0.0:23300                   │ │
│  │ - 为团队成员服务                         │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  存储: /data/runicorn（共享）                 │
└────────────────┬───────────────────────────────┘
                 │
         网络（局域网）
                 │
     ┌───────────┼───────────┐
     │           │           │
┌────▼────┐ ┌────▼────┐ ┌───▼─────┐
│ 用户 1  │ │ 用户 2  │ │ 用户 3  │
│ 浏览器  │ │ 浏览器  │ │ 浏览器  │
└─────────┘ └─────────┘ └─────────┘
```

### 设置

**在服务器上**:
```bash
# 安装
pip install runicorn

# 配置共享存储
export RUNICORN_DIR="/data/runicorn"

# 作为服务启动（systemd）
sudo systemctl start runicorn-viewer

# 或在 screen/tmux 中运行
screen -S runicorn
runicorn viewer --host 0.0.0.0 --port 23300
```

**Systemd 服务** (`/etc/systemd/system/runicorn-viewer.service`):
```ini
[Unit]
Description=Runicorn Viewer Service
After=network.target

[Service]
Type=simple
User=mllab
Environment="RUNICORN_DIR=/data/runicorn"
ExecStart=/usr/local/bin/runicorn viewer --host 0.0.0.0 --port 23300
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**用户访问**:
```
http://服务器IP:23300
```

### 特点

- ✅ **团队访问**: 多用户
- ✅ **共享存储**: 所有人看到相同实验
- ✅ **集中化**: 单一数据源
- ⚠️ **无认证**: 信任网络（使用防火墙/VPN）
- ⚠️ **并发写入**: SQLite 处理，但需监控

---

## 桌面应用部署

### 架构

```
┌─────────────────────────────────────┐
│   Windows 桌面应用（Tauri）          │
│                                     │
│  ┌────────────────────────────────┐│
│  │ Tauri 封装（Rust）             ││
│  │ - 原生窗口                     ││
│  │ - 自动启动 Python 后端         ││
│  │ - 嵌入式 Web 视图              ││
│  └────────────────────────────────┘│
│                                     │
│  ┌────────────────────────────────┐│
│  │ Python Sidecar                 ││
│  │ - Runicorn viewer 子进程       ││
│  │ - 在随机端口运行               ││
│  └────────────────────────────────┘│
│                                     │
│  ┌────────────────────────────────┐│
│  │ React UI（打包）               ││
│  │ - 预编译前端                   ││
│  │ - 在 webview 中加载            ││
│  └────────────────────────────────┘│
│                                     │
│  存储: 用户配置                    │
└─────────────────────────────────────┘
```

### 安装

**从 GitHub Releases**:
1. 下载 `Runicorn_Desktop_vX.Y.Z_x64-setup.exe`
2. 运行安装程序
3. 从开始菜单启动 "Runicorn Desktop"

### 从源代码构建

**前置要求**:
- Node.js 18+
- Rust (稳定版)
- Python 3.8+
- NSIS（用于安装程序）

**构建**:
```powershell
cd desktop/tauri
.\build_release.ps1 -Bundles nsis
```

**输出**: 
```
desktop/tauri/src-tauri/target/release/bundle/nsis/
└── Runicorn_Desktop_0.4.0_x64-setup.exe
```

### 特点

- ✅ **原生感觉**: Windows 应用，非浏览器
- ✅ **自动启动**: 后端自动启动
- ✅ **离线**: 无需网络
- ✅ **轻量**: ~10MB 安装程序（vs Electron 100MB+）
- ⚠️ **仅 Windows**: 桌面应用目前

---

## Remote Viewer 部署（v0.5.0）

### 架构

```
┌──────────────────────┐   SSH Tunnel   ┌─────────────────────┐
│   远程服务器         │◄──────────────►│   本地机器          │
│   (Linux, GPU)       │                │   (Windows/Mac)     │
│                      │                │                     │
│  训练进程            │                │  本地 Viewer        │
│  - 写入存储          │                │  - 启动连接         │
│  - ~/RunicornData    │                │  - 端口转发         │
│                      │                │                     │
│  Remote Viewer       │                │  浏览器             │
│  - 临时进程          │                │  - localhost:8081   │
│  - 127.0.0.1:23300   │◄───隧道────────│  - 实时访问         │
│  - 读取本地数据      │                │                     │
│                      │                │                     │
│  完整 Runicorn 安装  │                │  完整安装           │
└──────────────────────┘                └─────────────────────┘

工作流程：
1. 用户在本地 Viewer 配置 SSH 连接
2. 自动检测远程 Python 环境
3. 在远程服务器启动临时 Viewer
4. 通过 SSH 隧道转发端口
5. 用户浏览器访问远程数据（透明）
```

### 设置

**在远程服务器上**（训练）:
```bash
# 安装 Runicorn（需要完整安装）
pip install runicorn

# 在训练脚本中
import runicorn as rn

run = rn.init(
    project="training",
    storage="~/RunicornData"  # 或任意路径
)

# 训练代码...
rn.log({"loss": 0.1})
rn.finish()
```

**在本地机器上**（查看）:
```bash
# 1. 安装 Runicorn
pip install runicorn

# 2. 启动本地 viewer
runicorn viewer

# 3. 在 Web UI 连接远程服务器:
#    - 点击 "Remote" 按钮
#    - 输入 SSH 凭据:
#      * 主机: gpu-server.university.edu
#      * 端口: 22
#      * 用户名: researcher
#      * 认证: SSH 密钥或密码
#    
# 4. 系统自动:
#    ✓ 检测远程 Python 环境
#    ✓ 选择包含 Runicorn 的环境
#    ✓ 启动远程 Viewer
#    ✓ 建立 SSH 隧道
#    ✓ 打开新浏览器标签页
#
# 5. 实时访问远程数据！
#    - 无需文件同步
#    - 实时查看实验
#    - 低延迟（~50-100ms）
```

### 对比旧方案（SSH 文件同步）

| 特性 | 旧方案（SSH 同步）| Remote Viewer (v0.5.0) |
|------|------------------|------------------------|
| **数据传输** | 需要同步大量文件 | 无需同步，直接访问 |
| **等待时间** | 首次同步几分钟 | 即时连接（5-10秒）|
| **本地存储** | 占用大量空间 | 零占用 |
| **实时性** | 需要重新同步 | 完全实时 |
| **网络带宽** | 高（传输模型等）| 低（仅元数据）|
| **多人协作** | 容易冲突 | 无冲突 |
| **体验** | 类似本地 | 类似本地 |

### 特点

- ✅ **零同步**: 无需文件传输，直接访问
- ✅ **即时连接**: 5-10 秒内可用
- ✅ **低延迟**: 增加 50-100ms 延迟（可接受）
- ✅ **节省空间**: 本地无需存储
- ✅ **实时**: 训练中的数据即时可见
- ✅ **自动清理**: 断开连接后自动清理
- ✅ **安全**: SSH 加密，无额外端口暴露
- ⚠️ **需要 SSH**: 服务器必须允许 SSH 访问
- ⚠️ **远程需要完整安装**: 远程服务器必须安装 Runicorn（不仅 SDK）

---

## 生产考虑

### 安全

**本地/开发**:
- 无需认证（仅 localhost）
- 防火墙防止外部访问

**共享服务器**:
- ⚠️ **无内置认证** - 依赖网络安全
- **建议**:
  - 使用防火墙（仅允许内部 IP）
  - 使用 VPN 进行远程访问
  - 使用 SSH 隧道: `ssh -L 23300:localhost:23300 server`

**未来**: v0.5+ 计划支持 API 密钥认证

---

### 性能调优

**对于大型部署（10,000+ 实验）**:

1. **专门使用 V2 API**
   - 前端: 始终查询 `/api/v2/experiments`
   - 避免 V1 文件扫描端点

2. **调整 SQLite 设置**:
```python
# 在 src/runicorn/storage/backends.py
PRAGMA cache_size=20000;  # 增加缓存（默认：10000）
```

3. **增加连接池**:
```python
# 在 ConnectionPool.__init__
pool_size=20  # 默认：10
```

4. **定期维护**:
```sql
-- 清理数据库（回收空间）
VACUUM;

-- 分析用于查询优化
ANALYZE;
```

---

### 扩展策略

**垂直扩展**（单机）:
- ✅ 测试至 500,000 个实验
- 增加 RAM 以获得更大缓存
- SSD 以获得更快 I/O
- 更多 CPU 核心用于并发请求

**水平扩展**（未来）:
- 目前不支持（单个 SQLite 文件）
- 未来: 读副本，分片
- 替代: 每个团队多个独立实例

---

### 备份策略

**自动化备份**:
```bash
# 每日备份脚本
#!/bin/bash
DATE=$(date +%Y%m%d)
runicorn export --out /backups/runicorn_$DATE.tar.gz

# 保留最近 30 天
find /backups -name "runicorn_*.tar.gz" -mtime +30 -delete
```

**数据库备份**（SQLite）:
```bash
# 在线备份（viewer 运行时）
sqlite3 $RUNICORN_DIR/runicorn.db ".backup /backups/runicorn_$DATE.db"
```

---

### 监控

**健康检查**:
```bash
# 监控 API 可用性
curl http://localhost:23300/api/health

# 预期: {"status": "ok", "version": "0.4.0"}
```

**磁盘使用**:
```bash
# 监控存储增长
du -sh $RUNICORN_DIR

# 监控去重效果
runicorn artifacts --action stats
```

**性能**:
```bash
# 检查查询时间（应 <100毫秒）
curl http://localhost:23300/api/v2/experiments?per_page=50

# 在浏览器 DevTools → Network 标签中监控
```

---

### 故障排查

**Viewer 无法启动**:
```bash
# 检查端口可用性
lsof -i :23300  # Linux/Mac
netstat -ano | findstr :23300  # Windows

# 检查 Python 版本
python --version  # 必须是 3.8+

# 检查安装
pip list | grep runicorn
```

**数据库锁定**:
```bash
# 优雅停止 viewer
pkill -INT runicorn  # 或 Ctrl+C

# 等待 5 秒
sleep 5

# 重启
runicorn viewer
```

**查询慢**:
```bash
# 检查是否使用 V1 API（慢）
# 解决方案: 确保前端使用 V2 API

# 或: 重建索引
sqlite3 runicorn.db "REINDEX;"
```

---

## 部署检查清单

### 部署前

- [ ] 已安装 Python 3.8+
- [ ] 足够的磁盘空间（估算: 实验数 × 10MB + 模型）
- [ ] 网络可访问（如果共享部署）
- [ ] 防火墙已配置（如适用）
- [ ] 备份策略已就位

### 部署后

- [ ] 健康检查通过
- [ ] 存储目录可写
- [ ] 用户可以访问 UI
- [ ] 实验正确显示
- [ ] 备份已测试
- [ ] 监控已配置

---

**相关文档**: [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) | [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md)

**返回**: [架构索引](README.md)

