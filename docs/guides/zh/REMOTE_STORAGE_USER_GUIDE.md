[English](../en/REMOTE_STORAGE_USER_GUIDE.md) | [简体中文](REMOTE_STORAGE_USER_GUIDE.md)

---

> ⚠️  **已弃用 (Deprecated in v0.5.0)**  
>
> 此文档描述的远程同步功能（基于文件传输）在 v0.5.0 中已被弃用。  
> 请使用新的 **Remote Viewer** 功能：
>
> - [Remote Viewer 用户指南](REMOTE_VIEWER_GUIDE.md)
> - [Remote API 文档](../../api/zh/remote_api.md)
> - [Remote Viewer 架构文档](../../architecture/zh/REMOTE_VIEWER_ARCHITECTURE.md)
> - [0.4.x → 0.5.0 迁移指南](MIGRATION_GUIDE_v0.4_to_v0.5.md)

---

# Runicorn 远程存储使用指南（历史参考）

## 历史摘要

Remote Storage 是较早期的一套远程访问思路，目标是在不完整同步远端数据的前提下，让用户：

1. 通过 SSH 连接远端机器
2. 把 metadata 同步到本地缓存
3. 在本地浏览缓存后的 artifacts
4. 需要时再按需下载文件

这套模型和当前版本的 **Remote Viewer** 主路径不同。当前版本围绕 `/api/remote/*` 的连接、环境探测、known hosts、saved connections 和 viewer session 生命周期工作，而不是围绕“同步 + 缓存 + 下载任务”工作。

## 为什么它被替换

旧模型的主要局限是：

- 用户心智模型复杂，需要区分远端元数据、本地缓存和按需下载文件
- 文档、UI 和后台任务容易围绕同步状态膨胀
- 对“实时访问远端数据”这个目标来说，Remote Viewer 更直接

因此自 `v0.5.0` 起，主远程工作流迁移到 Remote Viewer。

## 历史设计中曾出现的能力

下面这些只用于帮助理解旧术语和旧设计，不代表当前版本主路径仍公开这些能力：

- 远端 metadata 同步
- 本地缓存后的 artifact 浏览
- 按需下载文件
- 旧式远程模式 / 本地模式切换
- cache 管理和下载任务管理
- 一些历史性的 `/api/remote/*` 设计草案

如果你正在查找当前版本是否支持某个接口或按钮，请不要以本页为准，应以当前主文档为准：

- [docs/api/zh/remote_api.md](../../api/zh/remote_api.md)
- [docs/architecture/zh/REMOTE_VIEWER_ARCHITECTURE.md](../../architecture/zh/REMOTE_VIEWER_ARCHITECTURE.md)

## 迁移说明

如果你之前使用的是这套旧模型，可以按下面的映射迁移：

### 旧目标：连接远端并浏览数据

改为：

- 在 Remote Viewer 页面配置连接
- 使用 `saved connections` 保存服务器和 profile
- 用 `connect` / `viewer/start` 建立当前会话

### 旧目标：同步 metadata 后离线浏览

改为：

- 优先使用 Remote Viewer 直接访问远端数据
- 如需保留连接配置或复用环境选择，使用当前 saved server / profile 模型

### 旧目标：依赖旧式 remote storage API

改为：

- 停止把历史 remote storage 路由当作当前 API 参考
- 迁移到 [../../api/zh/remote_api.md](../../api/zh/remote_api.md) 中已核实存在的 `/api/remote/*` 路由

## 当前应查看的文档

- 用户操作： [REMOTE_VIEWER_GUIDE.md](REMOTE_VIEWER_GUIDE.md)
- API 参考： [../../api/zh/remote_api.md](../../api/zh/remote_api.md)
- 架构说明： [../../architecture/zh/REMOTE_VIEWER_ARCHITECTURE.md](../../architecture/zh/REMOTE_VIEWER_ARCHITECTURE.md)
- 迁移背景： [MIGRATION_GUIDE_v0.4_to_v0.5.md](MIGRATION_GUIDE_v0.4_to_v0.5.md)

## 边界说明

本页保留的唯一目的，是帮助读者理解：

- 仓库里为什么还会出现 “Remote Storage” 这个历史名词
- 旧版本用户该迁移到哪里
- 为什么当前主文档已经转向 Remote Viewer

本页不再承担：

- 当前版本操作手册
- 当前 API 参考
- 当前 UI 功能说明

---

**状态**: 历史参考页  
**当前主路径**: Remote Viewer
