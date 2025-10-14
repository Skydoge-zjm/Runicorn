[English](../en/README.md) | [简体中文](README.md)

---

# Runicorn 架构文档

**版本**: v0.4.0  
**最后更新**: 2025-10-14  
**目标受众**: 开发者、贡献者、架构师

---

## 概述

本目录包含 Runicorn 系统的全面架构文档。这些文档解释了实现背后的**设计**和**为什么**，补充了用户指南（如何使用）和 API 文档（存在哪些端点）。

---

## 架构文档

### 系统设计

- **[SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)** - 高层系统架构
  - 整体架构图
  - 技术栈及理由
  - 核心原则和设计目标
  - 系统边界

- **[COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md)** - 组件分解
  - SDK 层设计
  - Viewer/API 层设计
  - 存储层设计
  - 组件交互

### 数据与存储

- **[DATA_FLOW.md](DATA_FLOW.md)** - 数据处理管道
  - 实验生命周期
  - 指标记录流程
  - Artifact 存储流程
  - 序列图

- **[STORAGE_DESIGN.md](STORAGE_DESIGN.md)** - 存储架构
  - 混合 SQLite + 文件方法
  - 数据库 schema 设计
  - 去重算法
  - 性能特征

### 应用层

- **[API_DESIGN.md](API_DESIGN.md)** - API 层架构
  - V1 vs V2 设计理由
  - 路由组织
  - 服务层模式
  - 错误处理策略

- **[FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md)** - 前端设计
  - React 应用结构
  - 状态管理
  - 组件层级
  - 性能优化

### 部署与决策

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - 部署选项
  - 本地部署
  - 服务器部署
  - 桌面应用（Tauri）
  - 扩展策略

- **[DESIGN_DECISIONS.md](DESIGN_DECISIONS.md)** - 技术决策
  - 为什么选择 SQLite 而非 PostgreSQL
  - 为什么选择 Python + FastAPI
  - 为什么选择 React + Ant Design
  - 权衡考虑

---

## 如何使用本文档

### 新贡献者

**推荐阅读顺序**:
1. 从 [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) 开始 - 理解整体
2. 阅读 [COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md) - 理解组件如何配合
3. 根据贡献重点深入特定领域

### 系统架构师

**重点关注**:
- [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) - 整体设计
- [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) - 选择背后的理由
- [DEPLOYMENT.md](DEPLOYMENT.md) - 生产考虑

### 后端开发者

**重点关注**:
- [COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md) - 后端组件
- [STORAGE_DESIGN.md](STORAGE_DESIGN.md) - 存储实现
- [API_DESIGN.md](API_DESIGN.md) - API 层设计
- [DATA_FLOW.md](DATA_FLOW.md) - 数据处理

### 前端开发者

**重点关注**:
- [FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md) - React 应用设计
- [DATA_FLOW.md](DATA_FLOW.md) - 数据如何流向 UI
- [API_DESIGN.md](API_DESIGN.md) - API 消费模式

---

## 相关文档

- **用户指南**: [../guides/](../guides/) - 如何使用 Runicorn
- **API 文档**: [../api/](../api/) - REST API 参考
- **参考文档**: [../reference/](../reference/) - 技术参考资料

---

## 为架构文档做贡献

为架构文档做贡献时：

1. **专注于设计，而非使用** - 解释"为什么"和"如何工作"，而非"如何使用"
2. **包含图表** - 使用 Mermaid 或 ASCII 艺术进行可视化解释
3. **解释权衡** - 记录考虑的替代方案以及为何被拒绝
4. **保持更新** - 当架构发生重大变化时更新

---

**返回主文档**: [../../README.md](../../README.md)


