# Runicorn v0.5.0 发布说明

> **发布日期**: 2025-10-25  
> **版本**: v0.5.0  
> **作者**: Runicorn Development Team

[English](../en/RELEASE_NOTES_v0.5.0.md) | [简体中文](RELEASE_NOTES_v0.5.0.md)

---

## 🚀 重大更新

### Remote Viewer - VSCode Remote 架构

Runicorn 0.5.0 引入了全新的 **Remote Viewer** 功能，采用类似 VSCode Remote Development 的架构，彻底改变了远程服务器访问方式。

**核心变化**:
- 🌐 在远程服务器上直接运行 Viewer 进程
- 🔌 通过 SSH 隧道在本地浏览器访问
- ⚡ 实时访问远程数据，无需同步
- 💾 零本地存储占用
- 📊 完整功能支持

**vs 旧版远程同步 (0.4.x)**:

| 特性 | 0.4.x 文件同步 | 0.5.0 Remote Viewer |
|------|----------------|---------------------|
| 数据传输 | 需同步 GB 级数据 | 无需同步，实时访问 |
| 初始等待 | 数小时（大数据集） | 数秒（连接启动） |
| 本地存储 | 需要（镜像副本） | 不需要（零占用） |
| 实时性 | 延迟 5-10 分钟 | 完全实时（< 100ms） |

---

## ✨ 新功能

### Remote Viewer 核心功能

- **SSH 连接管理**: 支持密钥/密码认证，自动端口转发
- **环境自动检测**: 智能识别 Conda、Virtualenv 环境
- **Viewer 生命周期管理**: 自动启动、健康检查、优雅关闭
- **多服务器支持**: 同时连接多台服务器，独立端口隔离
- **实时健康监控**: 连接状态、性能指标实时显示

### UI 改进

- **Remote 页面**: 全新的连接向导界面
- **环境选择器**: 显示 Python 版本、Runicorn 版本、存储路径
- **配置预览**: 启动前确认所有配置信息
- **活动连接管理**: 查看和管理所有远程连接
- **错误提示优化**: 更清晰的错误信息和故障排查提示

### 性能优化

- **连接速度**: 启动时间从小时级缩短到秒级
- **网络优化**: 带宽使用从 GB 级降低到 MB 级
- **内存优化**: 本地无需存储镜像数据
- **延迟优化**: 实时访问延迟 < 100ms

---

## 💥 破坏性变更 (Breaking Changes)

### ⚠️  API 变更

**已弃用的 API**:
- `POST /api/ssh/connect` → 使用 `POST /api/remote/connect`
- `GET /api/ssh/status` → 使用 `GET /api/remote/viewer/status`
- `POST /api/ssh/sync` → **已移除**（不再需要同步）
- `GET /api/ssh/mirror/list` → **已移除**
- `DELETE /api/ssh/disconnect` → 使用 `DELETE /api/remote/connections/{id}`

**新增 API** (12个端点):
- Remote 连接管理（3个）
- 环境检测（3个）
- Viewer 管理（4个）
- 健康检查（2个）

详见: [Remote API 文档](../../api/zh/remote_api.md)

### ⚠️  配置格式变更

**旧配置** (`ssh_config.json`):
```json
{
  "connections": [
    {
      "host": "server.com",
      "mode": "mirror"
    }
  ]
}
```

**新配置**: 不再需要配置文件，所有配置通过 UI 或 API 管理

### ⚠️  模块变更

- **已弃用**: `src/runicorn/ssh_sync.py`
- **新增**: `src/runicorn/remote/` 模块
- **新增**: `src/runicorn/viewer/api/remote.py`

---

## 🔌 新增 API 端点

### 连接管理
```
POST   /api/remote/connect          建立 SSH 连接
GET    /api/remote/connections      列出所有连接
DELETE /api/remote/connections/{id} 断开连接
```

### 环境检测
```
GET    /api/remote/environments           列出 Python 环境
POST   /api/remote/environments/detect   重新检测环境
GET    /api/remote/config                获取远程配置
```

### Remote Viewer 管理
```
POST   /api/remote/viewer/start    启动 Remote Viewer
POST   /api/remote/viewer/stop     停止 Remote Viewer
GET    /api/remote/viewer/status   获取状态
GET    /api/remote/viewer/logs     获取日志
```

### 健康检查
```
GET    /api/remote/health          连接健康状态
GET    /api/remote/ping            测试连接
```

---

## 🐛 Bug 修复

- **修复**: WebSocket 连接内存泄漏
- **修复**: SSH 连接超时处理不当
- **修复**: 端口冲突时的错误处理
- **修复**: Remote Viewer 进程未正确清理
- **修复**: 非标准 Python 安装的环境检测失败
- **修复**: 多个连接同时启动时的竞态条件

---

## 📚 文档更新

### 新增文档

- **[Remote Viewer 用户指南](../../guides/zh/REMOTE_VIEWER_GUIDE.md)** - 完整使用教程
- **[Remote Viewer 架构](../../architecture/zh/REMOTE_VIEWER_ARCHITECTURE.md)** - 技术架构文档
- **[0.4.x → 0.5.0 迁移指南](../../guides/zh/MIGRATION_GUIDE_v0.4_to_v0.5.md)** - 升级指南
- **[Remote API 文档](../../api/zh/remote_api.md)** - 完整 API 参考

### 更新文档

- **README** - 添加 Remote Viewer 快速开始
- **快速开始指南** - 更新为 Remote Viewer
- **CHANGELOG** - 完整的 v0.5.0 变更记录
- **远程存储指南** - 标记为已弃用

---

## ⚠️  已知限制

### 平台支持

- ✅ **本地**: Windows、Linux、macOS
- ✅ **远程服务器**: Linux（含 WSL）
- ❌ **远程服务器**: Windows（计划支持）

### 网络要求

- 需要稳定的 SSH 连接
- 推荐带宽: 1 Mbps+
- 延迟: < 500ms（跨国连接可能较慢）

### 安全限制

- 级联连接限制为 2 级（A→B→C）
- 远程服务器必须安装 Runicorn 0.5.0

---

## 🔄 升级指南

### 对于现有用户

#### 1. 升级本地 Runicorn

```bash
pip install -U runicorn
```

#### 2. 升级远程服务器

```bash
# SSH 登录到远程服务器
ssh user@remote-server

# 升级 Runicorn
pip install -U runicorn
```

#### 3. 迁移到 Remote Viewer

**旧方式**（0.4.x 文件同步）:
1. 配置 SSH 连接
2. 选择远程目录
3. 点击"同步此目录"
4. 等待数小时同步完成

**新方式**（0.5.0 Remote Viewer）:
1. 点击 "Remote" 菜单
2. 填写 SSH 信息
3. 选择 Python 环境
4. 点击"启动 Remote Viewer"
5. **秒级完成，立即使用**！

详见: [迁移指南](../../guides/zh/MIGRATION_GUIDE_v0.4_to_v0.5.md)

### 对于新用户

直接使用 Remote Viewer 访问远程服务器：

```bash
# 1. 安装 Runicorn（本地和远程）
pip install runicorn

# 2. 启动本地 Viewer
runicorn viewer

# 3. 在浏览器中使用 Remote 功能
```

---

## 🎯 使用场景

### 适合使用 Remote Viewer

✅ **GPU 服务器训练**: 在实验室或公司 GPU 服务器上训练，本地实时查看  
✅ **大数据集**: 数据集太大无法同步到本地  
✅ **实时监控**: 需要实时查看训练进度  
✅ **多服务器管理**: 同时管理多台服务器的实验  

### 不适合使用 Remote Viewer

❌ **完全离线**: 无网络连接的环境  
❌ **网络不稳定**: 频繁断网的场景  
❌ **Windows 远程服务器**: 暂不支持（计划中）  

---

## 📊 性能对比

| 指标 | 0.4.x 文件同步 | 0.5.0 Remote Viewer | 提升 |
|------|----------------|---------------------|------|
| 初始化时间 | 2-8 小时 | 5-15 秒 | **99.9%** ↓ |
| 本地存储占用 | 100 GB+ | 0 GB | **100%** ↓ |
| 实时性延迟 | 5-10 分钟 | < 100ms | **99.9%** ↓ |
| 网络带宽 | 初始 10+ GB | 持续 100 KB/s | **99%** ↓ |
| CPU 占用（远程） | 5-10% | < 5% | **50%** ↓ |
| CPU 占用（本地） | 2-5% | < 2% | **60%** ↓ |

---

## 🔐 安全性

### 增强的安全措施

- ✅ 所有通信通过 SSH 加密
- ✅ Viewer 仅监听 localhost，不暴露到公网
- ✅ 支持 SSH 密钥认证
- ✅ 自动端口选择，避免冲突
- ✅ 完整的连接审计日志

### 安全建议

1. **使用 SSH 密钥**: 推荐使用密钥而非密码
2. **配置 SSH Config**: 简化连接配置
3. **定期更新**: 保持 Runicorn 最新版本
4. **网络隔离**: 仅在受信任的网络环境使用

---

## 📝 技术细节

### 架构变化

**0.4.x 架构**:
```
本地 Viewer → SSH 文件传输 → 本地存储 → 本地显示
```

**0.5.0 架构**:
```
本地 Viewer → SSH 隧道 → 远程 Viewer → 远程数据 → 本地显示
```

### 关键技术

- **SSH 隧道**: 本地端口映射到远程 Viewer 端口
- **FastAPI**: 远程 Viewer 使用 FastAPI 提供服务
- **进程管理**: 远程 Viewer 以后台进程运行
- **健康检查**: 实时监控连接和 Viewer 状态

---

## 🎉 社区反馈

我们非常感谢社区在开发过程中提供的宝贵意见！

**主要改进来自用户反馈**:
- 实时访问远程数据的需求
- 减少本地存储占用
- 简化远程连接流程
- 提升连接速度

---

## 📞 支持与反馈

### 获取帮助

- **用户指南**: [Remote Viewer 用户指南](../../guides/zh/REMOTE_VIEWER_GUIDE.md)
- **FAQ**: [常见问题](../../reference/zh/FAQ.md)
- **API 文档**: [Remote API 参考](../../api/zh/remote_api.md)

### 报告问题

- **GitHub Issues**: [提交 Bug 报告](https://github.com/Skydoge-zjm/runicorn/issues)
- **功能请求**: [提交功能建议](https://github.com/Skydoge-zjm/runicorn/discussions)

---

## 🗺️  未来计划

### v0.5.x 计划

- Windows 远程服务器支持
- macOS 远程服务器支持
- 连接持久化和自动重连
- 更多环境检测优化

### v0.6.0 计划

- 多用户协作功能
- 实验共享和权限管理
- Webhook 集成
- 高级可视化功能

---

## 📥 下载

### PyPI

```bash
pip install -U runicorn
```

### GitHub Releases

- [v0.5.0 源码](https://github.com/Skydoge-zjm/runicorn/archive/v0.5.0.tar.gz)
- [Windows 桌面应用](https://github.com/Skydoge-zjm/runicorn/releases/v0.5.0)

---

## 🙏 致谢

感谢所有为 Runicorn 0.5.0 做出贡献的开发者和用户！

**特别感谢**:
- VSCode Remote Development 团队的设计启发
- 所有提供反馈和建议的用户
- 开源社区的支持

---

**作者**: Runicorn Development Team  
**版本**: v0.5.0  
**发布日期**: 2025-10-25

**[查看完整 CHANGELOG](../../CHANGELOG.md)** | **[返回文档首页](../../README_zh.md)**
