[English](README.md) | [简体中文](README_zh.md)

---

# Runicorn 文档

**版本**: v0.5.0  
**最后更新**: 2025-10-25

---

## 📚 文档结构

```
docs/
├── guides/                 # 用户指南与教程
├── reference/              # 技术参考（配置、CLI、FAQ）
├── architecture/           # 架构文档
├── releases/               # 发布说明与历史
├── api/                    # REST API 文档
├── user-guide/             # 用户指南网站 (MkDocs)
└── assets/                 # 图片与截图
```

---

## 🎯 快速导航

### 面向最终用户

📖 **[用户指南网站](user-guide/)** - 完整使用文档
- 安装和设置
- Python SDK 教程
- CLI 命令
- Web 界面指南

**从这里开始**: [guides/zh/QUICKSTART.md](guides/zh/QUICKSTART.md) - 5分钟快速开始

---

### 面向开发者/集成者

🔌 **[API 文档](api/)** - REST API 参考
- 完整端点文档  
- 请求/响应 schema
- 代码示例 (cURL, Python, JavaScript)
- Postman collection

**从这里开始**: [api/zh/README.md](api/zh/README.md) - API 概览

---

### 面向贡献者

🤝 **贡献指南** - 查看 [../CONTRIBUTING.md](../CONTRIBUTING.md)

**技术文档**:
- [reference/zh/ARCHITECTURE.md](reference/zh/ARCHITECTURE.md) - 系统架构
- [reference/zh/SECURITY_AUDIT_REPORT.md](reference/zh/SECURITY_AUDIT_REPORT.md) - 安全指南
- [api/zh/](api/zh/) - API 实现参考

---

## 📖 按类别浏览文档

### 指南 (快速开始)

| 文档 | 描述 | 受众 |
|------|------|------|
| [QUICKSTART.md](guides/zh/QUICKSTART.md) | 5分钟快速开始 | 所有用户 |
| [REMOTE_VIEWER_GUIDE.md](guides/zh/REMOTE_VIEWER_GUIDE.md) | ⭐ Remote Viewer 使用指南（v0.5.0）| 用户 |
| [ARTIFACTS_GUIDE.md](guides/zh/ARTIFACTS_GUIDE.md) | 模型版本控制指南 | 用户 |
| [MIGRATION_GUIDE_v0.4_to_v0.5.md](guides/zh/MIGRATION_GUIDE_v0.4_to_v0.5.md) | ⭐ 迁移指南 0.4→0.5 | 用户 |
| [DEMO_EXAMPLES_GUIDE.md](guides/zh/DEMO_EXAMPLES_GUIDE.md) | 示例代码讲解 | 用户 |

### 架构文档

| 文档 | 描述 | 受众 |
|------|------|------|
| [SYSTEM_OVERVIEW.md](architecture/zh/SYSTEM_OVERVIEW.md) | 系统概述（含 v0.5.0 架构）| 架构师，贡献者 |
| [REMOTE_VIEWER_ARCHITECTURE.md](architecture/zh/REMOTE_VIEWER_ARCHITECTURE.md) | ⭐ Remote Viewer 架构（v0.5.0）| 架构师，开发者 |
| [COMPONENT_ARCHITECTURE.md](architecture/zh/COMPONENT_ARCHITECTURE.md) | 组件架构 | 开发者 |
| [STORAGE_DESIGN.md](architecture/zh/STORAGE_DESIGN.md) | 存储设计 | 开发者 |
| [DATA_FLOW.md](architecture/zh/DATA_FLOW.md) | 数据流 | 开发者 |
| [API_DESIGN.md](architecture/zh/API_DESIGN.md) | API 设计 | 后端开发者 |
| [FRONTEND_ARCHITECTURE.md](architecture/zh/FRONTEND_ARCHITECTURE.md) | 前端架构 | 前端开发者 |
| [DEPLOYMENT.md](architecture/zh/DEPLOYMENT.md) | 部署架构 | 运维 |
| [DESIGN_DECISIONS.md](architecture/zh/DESIGN_DECISIONS.md) | 设计决策 | 架构师 |

### 参考 (技术)

| 文档 | 描述 | 受众 |
|------|------|------|
| [CONFIGURATION.md](reference/zh/CONFIGURATION.md) | ⭐ 配置参考（v0.5.0）| 所有用户 |
| [CLI_REFERENCE.md](reference/zh/CLI_REFERENCE.md) | ⭐ CLI 命令参考（v0.5.0）| 所有用户 |
| [FAQ.md](reference/zh/FAQ.md) | ⭐ 常见问题（v0.5.0）| 所有用户 |
| [RATE_LIMIT_CONFIGURATION.md](reference/zh/RATE_LIMIT_CONFIGURATION.md) | 速率限制配置 | 开发者 |

### 发布 (版本历史)

| 文档 | 描述 |
|------|------|
| [RELEASE_NOTES_v0.5.0.md](releases/zh/RELEASE_NOTES_v0.5.0.md) | ⭐ v0.5.0 发布说明（Remote Viewer）|
| [RELEASE_NOTES_v0.4.0.md](releases/zh/RELEASE_NOTES_v0.4.0.md) | v0.4.0 发布说明 |

### API 文档

查看 [api/zh/README.md](api/zh/README.md) 获取完整 REST API 文档。

### 用户指南网站

查看 [user-guide/](user-guide/) 获取基于 MkDocs 的用户文档网站。

**部署到 GitHub Pages**: 查看 user-guide 文档

---

## 🗂️ 文档概览

| 类别 | 位置 | 文件数 | 用途 |
|------|------|--------|------|
| **用户指南** | guides/ | 6 | 快速开始, Remote Viewer, 迁移指南 |
| **技术参考** | reference/ | 6 | 配置, CLI, FAQ, 速率限制 |
| **架构文档** | architecture/ | 9 | 系统设计, Remote Viewer 架构 |
| **发布信息** | releases/ | 3+ | 版本历史, 变更日志 |
| **API 文档** | api/ | 13 | REST API 参考（含 Remote API）|
| **用户指南网站** | user-guide/ | 7+ | MkDocs 网站源文件 |
| **资源** | assets/ | 3+ | 图片和截图 |

---

## 🚀 开始使用

### 我是用户

1. **快速开始**: [guides/zh/QUICKSTART.md](guides/zh/QUICKSTART.md)
2. **完整指南**: [user-guide/](user-guide/) (网站)
3. **示例**: [guides/zh/DEMO_EXAMPLES_GUIDE.md](guides/zh/DEMO_EXAMPLES_GUIDE.md)

### 我是开发者

1. **API 概览**: [api/zh/README.md](api/zh/README.md)
2. **快速参考**: [api/zh/QUICK_REFERENCE.md](api/zh/QUICK_REFERENCE.md)
3. **Postman**: [api/runicorn_api.postman_collection.json](api/runicorn_api.postman_collection.json)

### 我是贡献者

1. **架构**: [reference/zh/ARCHITECTURE.md](reference/zh/ARCHITECTURE.md)
2. **贡献指南**: [../CONTRIBUTING.md](../CONTRIBUTING.md)
3. **安全**: [reference/zh/SECURITY_AUDIT_REPORT.md](reference/zh/SECURITY_AUDIT_REPORT.md)

---

## 📦 其他资源

### 示例

位于 `../examples/`:
- `quickstart_demo.py` - 最小示例
- `complete_workflow_demo.py` - 完整工作流
- `test_artifacts.py` - Artifacts 使用
- `remote_storage_demo.py` - 远程同步

查看 [guides/zh/DEMO_EXAMPLES_GUIDE.md](guides/zh/DEMO_EXAMPLES_GUIDE.md) 了解详情。

---

## 🔄 变更日志

版本历史请查看:
- **主变更日志**: `../CHANGELOG.md` - 面向用户的变更
- **开发归档**: [releases/zh/CHANGELOG_ARCHIVE.md](releases/zh/CHANGELOG_ARCHIVE.md) - 技术细节

---

## 🆘 需要帮助？

- 📖 搜索文档
- ❓ 查看 [user-guide/docs/reference/faq.md](user-guide/docs/reference/faq.md)
- 🐛 [报告问题](https://github.com/yourusername/runicorn/issues)
- 💬 [提问](https://github.com/yourusername/runicorn/discussions)

---

## 📊 文档状态

| 类别 | 完成度 | 状态 |
|------|--------|------|
| API 文档（含 Remote）| 100% | ✅ 完成 |
| 架构文档（含 Remote）| 100% | ✅ 完成 |
| 参考文档（配置/CLI/FAQ）| 100% | ✅ 完成 |
| 用户指南（含迁移）| 90% | 🔄 近完成 |
| 用户指南网站 | 40% | 🔄 进行中 |
| 教程 | 30% | 🔄 增长中 |

---

**最后更新**: 2025-10-25  
**维护者**: Runicorn 文档团队  
**v0.5.0 亮点**: Remote Viewer（VSCode Remote 风格）、完整的配置/CLI/FAQ 参考

