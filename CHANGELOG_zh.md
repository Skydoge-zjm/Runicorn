# 更新日志

记录本项目的所有重要变更。

## [0.4.0] - 2025-10-03

### 🎉 重大新功能：模型与数据版本控制（Artifacts）

#### 核心功能
- **新增**: 完整的 Artifacts 系统 - 为模型、数据集提供版本控制
- **新增**: `rn.Artifact()` 类 - 创建版本化资产
- **新增**: `run.log_artifact()` - 保存 artifact 并自动分配版本号
- **新增**: `run.use_artifact()` - 加载特定版本的 artifact
- **新增**: 自动版本号管理（v1, v2, v3...）
- **新增**: 别名系统（latest, production 等）

#### 智能存储
- **新增**: 内容去重存储 - 基于 SHA256 哈希
- **新增**: 硬链接优化 - 相同文件只存储一次（节省 50-90% 空间）
- **新增**: 去重池机制 - 智能检测和共享相同内容
- **新增**: 原子性写入 - 防止数据损坏

#### 血缘追踪
- **新增**: 自动血缘追踪 - 记录 artifact 依赖关系
- **新增**: LineageTracker - 构建完整依赖图
- **新增**: 循环依赖检测 - 防止无限递归
- **新增**: 可视化血缘图 - ECharts 交互式图形

#### Web UI
- **新增**: Artifacts 管理页面 - 列表、搜索、统计
- **新增**: Artifact 详情页面 - 版本历史、文件列表、元数据
- **新增**: 血缘关系可视化 - 图形化显示依赖链路
- **新增**: 存储统计面板 - 显示去重效果和空间节省

#### CLI 工具
- **新增**: `runicorn artifacts` 命令
  - `--action list` - 列出所有 artifacts
  - `--action versions` - 查看版本历史
  - `--action info` - 查看详细信息
  - `--action delete` - 删除版本
  - `--action stats` - 存储统计

#### API 端点
- **新增**: `GET /api/artifacts` - 列出 artifacts
- **新增**: `GET /api/artifacts/{name}/versions` - 版本列表
- **新增**: `GET /api/artifacts/{name}/v{version}` - 详细信息
- **新增**: `GET /api/artifacts/{name}/v{version}/files` - 文件列表
- **新增**: `GET /api/artifacts/{name}/v{version}/lineage` - 血缘图
- **新增**: `GET /api/artifacts/stats` - 存储统计
- **新增**: `DELETE /api/artifacts/{name}/v{version}` - 删除版本

#### 国际化
- **新增**: 60+ Artifacts 相关翻译（中英文完整支持）

### 🔧 代码质量改进

#### 性能优化
- **新增**: 指标数据缓存机制 - API 响应速度提升 10-20 倍
- **改进**: 进程状态检查优化 - 只检查运行中的实验
- **新增**: 递归深度限制 - 防止过度遍历

#### 代码重构
- **重构**: 去重函数 - 拆分为单一职责的子函数
- **新增**: 原子性 JSON 写入 - 防止崩溃时数据损坏
- **新增**: 循环依赖检测 - visited 集合追踪

#### 安全性
- **新增**: 三层路径遍历防护
- **新增**: 输入验证 - run_id、batch_size、版本号
- **新增**: 路径长度检查 - Windows 兼容

#### 用户体验
- **改进**: UI 设计系统 - 统一的 designTokens
- **改进**: 图表控件布局 - 自动换行，防止重叠
- **新增**: 骨架屏加载 - 平滑的加载体验
- **改进**: 错误消息 - 更友好和详细

#### 代码清理
- **移除**: 所有 console.log - 使用统一的 logger
- **新增**: React.memo 优化 - 减少不必要的重渲染
- **修复**: WebSocket 内存泄漏 - 支持大日志文件

### 🐛 Bug 修复
- **修复**: SDK 异步调用混乱 - 可能导致数据丢失
- **修复**: Stage 竖线与图例重叠
- **修复**: 多列模式文字重叠
- **修复**: Windows 文件锁问题 - SQLite 连接管理
- **修复**: 31+ 架构、安全、性能问题

### 📚 文档
- **新增**: `docs/ARTIFACTS_GUIDE.md` - 完整的 Artifacts 使用指南
- **新增**: `examples/user_workflow_demo.py` - 完整工作流演示
- **新增**: `examples/realistic_ml_project/` - 真实项目示例
- **新增**: `tests/TESTING_GUIDE.md` - 测试指南
- **新增**: 35+ 测试用例

### ⚠️ 已知限制
- Windows 测试环境可能遇到临时文件清理问题（不影响功能使用）
- 跨盘符时硬链接会 fallback 到复制（建议使用同一盘符）
- Windows 路径长度限制（约 240 字符）

---

## [0.3.1] - 2025-09-26

### 🏗️ 架构现代化

#### 代码重构
- **新增**: 模块化架构 - viewer.py拆分为专业模块，提升可维护性
- **新增**: 服务层抽象，业务逻辑清晰分离
- **新增**: 增强的错误处理和日志记录系统
- **新增**: `rn.log_text()` 模块级API，统一文本日志接口

#### 高性能存储系统
- **新增**: SQLite + 文件混合存储架构，查询性能提升10倍以上
- **新增**: 自动从文件存储迁移到混合存储，无用户感知
- **新增**: 高级查询功能 - 过滤、分页、搜索、排序
- **新增**: V2 API端点（`/api/v2/experiments`、`/api/v2/analytics`）提供增强性能
- **新增**: 实时分析和系统健康监控

#### 开发者体验
- **改进**: 完全向后兼容 - 现有代码无需修改即可享受性能提升
- **改进**: 增强的WebSocket日志流，支持完整内容传输
- **新增**: 自动创建`runicorn.db`数据库文件用于高性能查询

## [0.3.0] - 2025-09-25

### 🎯 主要新功能

#### 通用最佳指标系统
- **新增**: `rn.set_primary_metric(metric_name, mode="max|min")` - 设置任意指标为主要指标
- **新增**: 训练过程中自动追踪最优值
- **新增**: 实验列表中显示最佳指标名称和数值
- **破坏性变更**: 移除硬编码的 `best_val_acc_top1` 字段，使用通用系统

#### 软删除和回收站
- **新增**: 安全的实验删除 - 文件保留，可恢复
- **新增**: 回收站界面管理已删除的实验
- **新增**: 批量恢复和永久删除功能
- **新增**: 使用 `.deleted` 标记文件实现软删除

#### 智能状态检测
- **新增**: 自动检测崩溃/中断的实验
- **新增**: 使用 `psutil` 进行进程存活检查
- **新增**: 后台状态检查任务（30秒间隔）
- **新增**: Web界面手动状态检查按钮
- **新增**: 支持 `interrupted` 状态（Ctrl+C处理）

### 🎨 界面和用户体验改进

#### 设置界面
- **新增**: 分栏设置界面（外观/布局/数据/性能）
- **新增**: 颜色、背景、效果的实时预览
- **新增**: 全面的自定义选项
- **新增**: 性能设置（自动刷新间隔、图表高度）

#### 响应式设计增强
- **新增**: 不同屏幕尺寸的自适应图表布局
- **新增**: 基于窗口宽度的智能列切换
- **新增**: 移动设备友好的控件和布局
- **改进**: 图表标题定位，防止重叠



## [0.2.7] - 2025-09-17

### 新增
- 语言选项：
  - 支持切换中英文。


## [0.2.6] - 2025-09-14

### 新增
- 远程同步（SSH 实时镜像）：
  - UI 新增「Remote」菜单，可通过 SSH 连接远程 Linux 服务器、浏览目录，并启动/停止将远程 runs 实时镜像到本地存储。
  - 新增后端接口：`POST /api/ssh/connect`、`GET /api/ssh/listdir`、`POST /api/ssh/mirror/start`、`POST /api/ssh/mirror/stop`、`GET /api/ssh/mirror/list`。
- 文档：明确“离线导入（UI 上传 .zip/.tar.gz）需要可选依赖 `python-multipart`”，并提供安装指引。

### 变更
- Viewer：即使未安装 `python-multipart`，服务也能正常启动；仅当调用“离线导入”接口时返回 `503` 并提示安装依赖。
- 桌面端（Windows）：提升启动鲁棒性与使用体验（无需用户手动干预）。

## [0.2.1] - 2025-09-09

### 修复
- 后端：`POST /api/config/user_root_dir` 正确解析 JSON body；设置数据目录时的错误提示更友好，并在设置后立即生效。
- Windows：支持在路径中展开环境变量（例如 `%USERPROFILE%`）。
- 增加轻量服务调试日志（写入 `%APPDATA%/Runicorn/server_debug.log`）。

### 变更
- 构建：`desktop/tauri/build_release.ps1` 在构建 sidecar 前会同步 `web/frontend/dist` 到 `src/runicorn/webui`，以携带最新 UI。
- 文档：新增桌面应用使用说明及“设置 → 数据目录”流程。

### 桌面端
- NSIS 安装器（Tauri）集成并自动启动本地后端。首次运行可在设置中选择可写的数据目录。

## [0.2.0] - 2025-09-08

### 新增
- 用户级存储根与项目/实验层级：`user_root_dir/<project>/<name>/runs/<run_id>/...`。
- 新增 CLI：`runicorn config` 用于设置与查看全局 `user_root_dir`。
- Viewer 层级发现 API：
  - `GET /api/projects`
  - `GET /api/projects/{project}/names`
  - `GET /api/projects/{project}/names/{name}/runs`
- 前端：
  - 运行列表增加 Project/Name 筛选。
  - 运行详情支持同一实验的多次运行叠加展示（多曲线对比）。

### 变更
- `runicorn viewer` 在未显式传入 `--storage` 时，优先使用全局用户配置，其次回退到 `./.runicorn`。
- `/api/runs` 与 `/api/runs/{id}` 响应增加 `project` 与 `name` 字段。

### 兼容性
- 保持对旧版目录结构 `./.runicorn/runs/<run_id>/` 的兼容。

## [0.1.x]
- 初始公开版本：本地只读 Viewer、步/时间指标、实时日志（WebSocket）、可选 GPU 面板。
