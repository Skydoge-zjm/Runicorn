# Runicorn 前端改进开发计划

**来源**: `docs/future/comparision_frontend/final_review_synthesis.md`
**创建日期**: 2026-02-22
**前端路径**: `web/frontend/src/`

---

## 总览

共 4 个 Sprint，预计总工时 7-11 天。每个 Sprint 独立可交付，不依赖后续 Sprint。

- **Sprint 0** — 零成本高收益（半天）：改默认值 + CSS 降噪 + Bug 修复
- **Sprint 1** — 组件替换（1-2 天）：fancy 组件简化 + 动画配置精简
- **Sprint 2** — 核心 UX 修复（2-3 天）：URL 状态化 + 对比系统统一 + 组件拆分
- **Sprint 3** — 架构优化（3-5 天）：虚拟滚动 + Tab 布局 + React Query + 可访问性

---

## Sprint 0：零成本高收益（半天）

目标：用户立即感受到「专业工具」的视觉变化，零功能回归。

### S0-1. 修改默认设置值

**文件**: `App.tsx` (第33-65行 `defaultSettings`)

修改项：
- `glass: true` → `glass: false`
- `backgroundType: 'gradient'` → `backgroundType: 'color'`
- `backgroundColor: '#0b1220'` → `backgroundColor: '#F8F9FA'`

验证：启动应用后默认无渐变背景、无毛玻璃效果、背景为浅灰纯色。Settings 中仍可手动切换回渐变/玻璃。

### S0-2. 表格样式降噪

**文件**: `styles/enhanced-table.css`

删除以下规则（保留文件，不删除文件本身）：
- 第13-21行：渐变表头 `.ant-table-thead > tr > th` 的 `linear-gradient` background
- 第24-28行：暗色模式表头渐变
- 第38-48行：hover 蓝光 glow（`linear-gradient` background + `box-shadow` 的 `inset` + 蓝色外发光）
- 第91-94行：分页器 hover 的 `translateY(-2px)` + `box-shadow`
- 第96-99行：分页器 active 的紫色渐变 `linear-gradient(135deg, #667eea, #764ba2)`
- 第101-103行：分页器 active 项的白色文字

保留以下规则：
- 第7-10行：表格圆角基础样式
- 第31-35行：表格行 cursor + transition 基础
- 第51-58行：选中行样式 + 左侧主色指示线
- 第60-69行：单元格 padding
- 第71-79行：loading overlay blur
- 第82-84行：分页器 margin
- 第86-89行：分页器基础圆角
- 第106-127行：自定义 scrollbar 样式

替换 hover 效果为简洁版：
```css
.enhanced-table .ant-table-tbody > tr:hover {
  background: rgba(0, 0, 0, 0.02) !important;
}
```
暗色模式补充：
```css
.enhanced-table.dark-mode .ant-table-tbody > tr:hover {
  background: rgba(255, 255, 255, 0.04) !important;
}
```

验证：表格 hover 仅有轻微背景色变化，无蓝光 glow；分页器无渐变、无抬升动画。

### S0-3. 移除 Confetti 效果

**步骤**：

1. **删除 hook 文件**: `hooks/useSuccessConfetti.tsx` 整个文件删除
2. **清理 ExperimentPage.tsx 中的引用**:
   - 删除 import: `import { useSuccessConfetti } from '../hooks/useSuccessConfetti'`
   - 删除实例化: `const { trigger: triggerConfetti, ConfettiComponent } = useSuccessConfetti()` (约第165行)
   - 删除所有 `triggerConfetti()` 调用（第360行 `handleBatchDeleteByPath`、第440行 `handleDelete` 的 onOk 回调中）
   - 删除 JSX 中的 `{ConfettiComponent}` 渲染

验证：删除操作后只显示 `message.success`，无粒子动画。

### S0-4. 修复单行删除状态时序 Bug

**文件**: `pages/ExperimentPage.tsx`

**问题**: Actions 列单行删除先 `setSelectedRowKeys([record.run_id])` 再调 `handleDelete()`，但 handleDelete 读取旧 state。

**修复方案**: 修改 `handleDelete` 签名，支持显式传入 runIds：
```typescript
const handleDelete = useCallback((explicitRunIds?: string[]) => {
    const idsToDelete = explicitRunIds || selectedRowKeys
    if (idsToDelete.length === 0) { ... }
    // 后续逻辑用 idsToDelete 替代 selectedRowKeys
}, [selectedRowKeys, ...])
```
单行删除时直接 `handleDelete([record.run_id])`，不再先 setSelectedRowKeys。

验证：单行删除按钮点击后正确弹出确认框，确认后正确删除该行。

### S0-5. 修复/隐藏 Add Runs 无效入口

**文件**: `pages/ExperimentPage.tsx`

**问题**: `addRunsModalOpen` (第153行) 只被置 true，无对应 Modal。

**方案（短期）**: 在 CompareRunsPanel 中隐藏 "+ Add runs" 按钮，或将其注释掉。同时清理 `addRunsModalOpen` 状态定义。

**方案（长期，Sprint 2）**: 在对比模式 URL 状态化后，"Add runs" 可跳转回列表页并保持对比状态，天然解决此问题。

验证：对比面板中不再显示无效的 "Add runs" 按钮。

---

## Sprint 1：组件替换（1-2 天）

目标：减少 ~500 行代码，消除 framer-motion 在叶子组件中的使用。

### S1-1. 替换 AnimatedStatusBadge

**删除文件**: `components/fancy/AnimatedStatusBadge.tsx`

**替换方案**: 在所有引用处直接使用 antd 原生 `Tag` 组件：

```tsx
import { Tag } from 'antd'
import { SyncOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined } from '@ant-design/icons'

// 替代 <AnimatedStatusBadge status={status} />
function StatusTag({ status }: { status: string }) {
  const s = status.toLowerCase()
  const label = status.charAt(0).toUpperCase() + status.slice(1)
  switch (s) {
    case 'running':     return <Tag icon={<SyncOutlined spin />} color="processing">{label}</Tag>
    case 'finished':    return <Tag icon={<CheckCircleOutlined />} color="success">{label}</Tag>
    case 'failed':      return <Tag icon={<CloseCircleOutlined />} color="error">{label}</Tag>
    case 'interrupted': return <Tag icon={<ClockCircleOutlined />} color="warning">{label}</Tag>
    default:            return <Tag>{label}</Tag>
  }
}
```

可以将此组件放在 `components/StatusTag.tsx` 中统一引用。

**涉及文件**：
- `pages/ExperimentPage.tsx` — 表格 status 列
- `pages/RunDetailPage.tsx` — 顶部信息卡 status 展示
- `components/CompareRunsPanel.tsx` — run 卡片状态

逐一替换 `<AnimatedStatusBadge status={...} />` 为 `<StatusTag status={...} />`，然后删除旧文件和旧 import。

验证：各状态显示为色彩淮底 + 彩色文字的 Tag，running 状态图标旋转，无 spring 弹入/pulse 动画。

### S1-2. 替换 FancyStatCard

**删除文件**: `components/fancy/FancyStatCard.tsx`

**替换方案**: 在 `ExperimentPage.tsx` 中将四张 FancyStatCard 替换为一行水平 `Statistic` 组：

```tsx
import { Statistic, Space } from 'antd'
// 四个统计数字水平排列，占用 ~48px 高度而非原来的 ~160px
<Space size={32} style={{ marginBottom: 16 }}>
  <Statistic title="Total" value={stats.total} />
  <Statistic title="Running" value={stats.running}
    valueStyle={{ color: token.colorPrimary }} />
  <Statistic title="Finished" value={stats.finished}
    valueStyle={{ color: token.colorSuccess }} />
  <Statistic title="Failed" value={stats.failed}
    valueStyle={{ color: token.colorError }} />
</Space>
```

统计栏可点击设置 statusFilter（原方案建议的「统计栏可交互」）：给每个 Statistic 包裹 `<div onClick={() => setStatusFilter('running')}>`。

**涉及文件**：`pages/ExperimentPage.tsx`（统计栏区域）、`pages/RemoteViewerPage.tsx`（如有使用）

验证：统计栏为紧凑的数字+标签，无渐变底色、无 shimmer、无 count-up 动画。点击统计数字可触发过滤。

### S1-3. 替换 FancyEmpty

**删除文件**: `components/fancy/FancyEmpty.tsx`

**替换方案**: 在所有引用处使用 antd 原生 `Empty`：

```tsx
import { Empty, Button } from 'antd'

<Empty
  image={Empty.PRESENTED_IMAGE_SIMPLE}
  description={description}
>
  {actionText && onAction && (
    <Button type="primary" onClick={onAction}>{actionText}</Button>
  )}
</Empty>
```

**涉及文件**：全局搜索 `FancyEmpty` 引用，逐一替换。

验证：空状态显示 antd 原生插图 + 描述文字 + 可选 CTA 按钮，无 SVG 旋转/浮动动画。

### S1-4. 简化 FancyMetricCard

**文件**: `components/fancy/FancyMetricCard.tsx`（不删除，原地修改）

修改 3 处：
1. **第37行**: `initial={{ opacity: 0, y: 20 }}` → 删除 initial 和 animate，改用普通 `<div>`
2. **第39行**: `whileHover={config.hoverEffect}` → 删除，或改为 CSS `transition: box-shadow 0.15s; &:hover { translateY(-1px) }`
3. **第89行**: `background: linear-gradient(...)` headStyle → 删除 headStyle 中的 background 和 borderBottom 渐变

同时将 `motion.div` 改为普通 `div`，移除 `framer-motion` import。

验证：指标图表卡片无渐变 header、无入场位移动画、hover 时仅有微小阴影变化。

### S1-5. 精简 animation_config 目录

**目录**: `config/animation_config/`

**删除文件**：
- `common.ts`
- `components.ts`
- `experiments.ts`
- `remote.ts`
- `run_detail.ts`

**保留并重命名**：
- `colors.ts` → 重命名为 `chartColors.ts`，仅保留图表系列色板（删除 `gradients`、`status`、`semantic`、`text`、`backgrounds`、`shadows` 等与 antd token 重复的定义）

**更新 index.ts**：删除已移除文件的 import 和 re-export，仅保留 `chartColors` 导出。

**处理引用**：全局搜索以下 import 并处理：
- `componentAnimationConfig` → 已在 S1-1/S1-3/S1-4 中消除
- `runDetailPageConfig` → S1-4 中 FancyMetricCard 简化后不再需要
- `experimentsPageConfig` → 检查 ExperimentPage 中是否有引用，如有则内联化
- `remotePageConfig` → 检查 RemoteViewerPage 中的引用
- `colorConfig` → 替换为 `chartColors` import

验证：`config/animation_config/` 目录下仅剩 `index.ts` 和 `chartColors.ts`。全局无 import 报错。

### S1-6. 修复 CompareCharts 指标显隐重置 Bug

**文件**: `components/CompareChartsView.tsx` (第64-66行)

**当前代码**：
```ts
useEffect(() => {
    setVisibleMetrics(new Set(commonMetrics))
}, [commonMetrics])
```

**修复为**：
```ts
useEffect(() => {
    setVisibleMetrics(prev => {
        const next = new Set(prev)
        // 新增的指标默认可见
        for (const m of commonMetrics) {
            if (!prev.has(m) && !removedByUser.current.has(m)) {
                next.add(m)
            }
        }
        // 已不存在的指标移除
        for (const m of prev) {
            if (!commonMetrics.includes(m)) {
                next.delete(m)
                removedByUser.current.delete(m)
            }
        }
        return next
    })
}, [commonMetrics])
```

同时需要加一个 `removedByUser` ref 记录用户主动取消勾选的指标，在 `toggleMetric` 中维护。

验证：在对比模式下取消勾选某个指标，等待自动刷新后，该指标仍保持取消状态。

---

## Sprint 2：核心 UX 修复（2-3 天）

目标：解决真实的交互缺陷和架构问题。

### S2-1. 对比模式 URL 状态化

**文件**: `pages/ExperimentPage.tsx`

**当前问题**: `compareMode` 为 React state（第147行），浏览器返回时丢失。

**实现方案**:
1. 使用 `useSearchParams` 读写 URL 参数
2. 对比模式通过 `?compare=id1,id2,...` 表示
3. 进入对比时 `setSearchParams({ compare: ids.join(',') })`
4. 退出对比时 `searchParams.delete('compare')`
5. 页面加载时从 URL 解析 compare 参数恢复状态

```typescript
const [searchParams, setSearchParams] = useSearchParams()
const compareIdsFromUrl = searchParams.get('compare')?.split(',').filter(Boolean) || []
const compareMode = compareIdsFromUrl.length >= 2
```

移除原有的 `const [compareMode, setCompareMode] = useState(false)`，改用派生计算。

**同步更新**: `CompareRunsPanel` 的 "Back" 按钮需调用 `setSearchParams` 清除 compare 参数。

验证：选择 2 个 run 点击 Compare → URL 变为 `/?compare=id1,id2` → 进入某个 run 详情 → 浏览器返回 → 对比模式正确恢复。

### S2-2. 移除 RunDetailPage 叠加对比系统

**文件**: `pages/RunDetailPage.tsx`

**删除内容**（约 ~150 行）：
- 状态：`availableProjects`、`selectedProject`、`availableExperiments`、`selectedExperiment`、`runsInExperiment`、`selectedRunIds`、`overlayKeys`、`overlayMetricsMap` （第74-90行）
- 副作用：初始化对比状态（第160-181行）、加载 experiments（第183-200+行）、叠加指标刷新
- UI：整个 `<Collapse>` / `<Card title={compare.title}>` 叠加对比区块
- 仅用于此功能的 API 导入：`listRunsByName`、`listNames`、`listProjects`（如其他地方不用）

**新增**：在顶部信息卡右上角加 "Compare with..." 按钮：
```tsx
<Button
  icon={<LineChartOutlined />}
  onClick={() => navigate(`/?compare=${id}`)}
>
  {t('run.compare_with')}
</Button>
```

验证：RunDetailPage 无叠加对比面板。点击 "Compare with..." 跳转到 ExperimentPage 并自动进入对比模式。

### S2-3. 拆分 ExperimentPage God Component

**文件**: `pages/ExperimentPage.tsx` (~1360 行) → 拆分为多个 hooks 和子组件

**新建文件**：

1. **`hooks/useExperimentData.ts`**
   - 迁移：`fetchRuns`、`stats` 计算、`projects` 提取、`autoRefresh` 轮询逻辑、`handleStatusCheck`
   - 返回：`{ runs, loading, stats, projects, fetchRuns, statusCheckLoading, handleStatusCheck }`

2. **`hooks/useExperimentFilters.ts`**
   - 迁移：`searchText`、`projectFilter`、`statusFilter`、`selectedTreePath`、`sortedInfo`、`pageSize`、过滤后的 `filteredRuns` 计算逻辑
   - 返回：`{ searchText, setSearchText, projectFilter, setProjectFilter, ... , filteredRuns }`

3. **`hooks/useCompareMode.ts`**
   - 迁移：`compareRunInfos`、`compareMetrics`、`compareRunLabels`、`compareLoading`、`visibleRunIds`、`handleCompare`、加载对比数据的逻辑
   - 结合 S2-1 的 URL 状态化方案
   - 返回：`{ compareMode, compareRunInfos, ... , enterCompare, exitCompare }`

4. **`hooks/useInlineEditing.ts`**
   - 迁移：`editingRunId`、`editingAlias`、`aliasUpdateLoading`、`handleAliasEdit/Save/Cancel`、tag 编辑相关状态和回调
   - 返回：`{ editingRunId, editingAlias, handleAliasEdit, handleAliasSave, ... }`

5. **`components/FilterToolbar.tsx`** — 筛选栏 UI 拆为子组件
6. **`components/StatsBar.tsx`** — 统计栏 UI 拆为子组件（复用 S1-2 的 Statistic 方案）

**原则**: 纯重构，不改行为。拆分后 ExperimentPage 应降至 ~400 行以下。

验证：所有现有功能不变（搜索、过滤、排序、分页、对比、内联编辑、删除、导出）。

### S2-4. LogsViewer 主题跟随

**文件**: `components/LogsViewer.tsx`

**当前问题**: 模块级单例 `ansiConverter`（第29-44行）硬编码深色配色。

**实现方案**：
1. 创建两个 AnsiToHtml 实例：
```typescript
const darkConverter = new AnsiToHtml({ fg: '#e6e9ef', bg: '#0d1117', ... })
const lightConverter = new AnsiToHtml({ fg: '#374151', bg: '#F8F9FA', colors: { /* 调暗适配浅底 */ } })
```
2. 组件内通过 `useSettings` 获取 `isDark`，选择对应的 converter
3. 容器背景色通过 CSS 变量注入，随主题切换

验证：light mode 下日志背景为浅色、文字为深色；dark mode 下为深色背景 + 浅色文字。切换主题后日志区域配色正确跟随。

### S2-5. 统一 API 调用

**文件**: `pages/ExperimentPage.tsx`

将以下 raw fetch 替换为 `api.ts` 封装：

1. **第292行** `fetch('/api/runs')` → 使用 `api.ts` 中的 `listRuns()`（如不存在则在 api.ts 中新增）
2. **第350行** `fetch('/api/paths/soft-delete', ...)` → 在 `api.ts` 中新增 `softDeleteByPath(path: string)` 封装

同时检查 `PathTreePanel.tsx` 是否有类似的 raw fetch，一并处理。

验证：全局搜索 `fetch('/api/` 仅出现在 `api.ts` 文件中。

### S2-6. Header 改造

**文件**: `App.tsx` (第212-239行)

**当前**: antd `Header` + `Menu theme="dark"`。

**替换为**: 自定义导航栏：
```tsx
<header style={{
  display: 'flex', alignItems: 'center', height: 48,
  borderBottom: `1px solid ${isDark ? '#2D3748' : '#E5E7EB'}`,
  background: isDark ? '#1A1D27' : '#FFFFFF',
  padding: '0 24px',
}}>
  <div style={{ fontWeight: 700, color: token.colorPrimary, marginRight: 32 }}>
    {t('app.title')}
  </div>
  <nav style={{ display: 'flex', gap: 24, flex: 1 }}>
    {navItems.map(item => (
      <NavLink key={item.key} to={item.path} style={({ isActive }) => ({
        color: isActive ? token.colorPrimary : token.colorText,
        borderBottom: isActive ? `2px solid ${token.colorPrimary}` : '2px solid transparent',
        padding: '12px 0', textDecoration: 'none', fontSize: 14,
      })}>
        {item.icon} {item.label}
      </NavLink>
    ))}
  </nav>
  {/* 右侧：API 状态、语言切换、设置按钮 保持不变 */}
</header>
```

移除 antd `Header`、`Menu` 的 import（如其他地方不用）。

验证：Header 跟随全局主题切换（light 白色 / dark 深色），选中项有主色下划线，无暴力暗色块。

---

## Sprint 3：架构优化（3-5 天）

目标：提升可维护性、性能上限和代码质量。

### S3-1. LogsViewer 虚拟滚动

**文件**: `components/LogsViewer.tsx`

**新增依赖**: `@tanstack/react-virtual`

**实现要点**：
1. 用 `useVirtualizer` 替代当前的全量 DOM 渲染
2. 缓存已转换的 ANSI HTML 字符串（`useMemo` + 稳定的 line index 作为 key），避免滚动时重复解析
3. 智能吸底（Smart Stickiness）：
   - 滚动条在底部时自动上推新日志
   - 用户向上滚动时立即暂停 auto-scroll
   - 显示浮动按钮 "⬇ Resume Auto-scroll"，点击回底部并恢复

验证：5000+ 行日志时滚动流畅无卡顿。向上滚动查看历史时不会被新日志强制拉回底部。

### S3-2. RunDetailPage Tab 化布局

**文件**: `pages/RunDetailPage.tsx`

**方案**: 将超长滚动页改为 4 个 Tab：

```tsx
import { Tabs } from 'antd'

<Tabs defaultActiveKey="overview" items={[
  { key: 'overview', label: 'Overview',  children: <> {顶部信息卡} {指标图表网格} </> },
  { key: 'logs',     label: 'Logs',      children: <LogsViewer url={...} /> },
  { key: 'assets',   label: 'Assets',    children: <RunAssets runId={id} /> },
  { key: 'system',   label: 'System',    children: <GpuMetricsCard ... /> },
]} />
```

**注意**：Logs Tab 应使用 `destroyInactiveTabPane={false}` 保持 WebSocket 连接，或在切换回来时重连。

验证：各 Tab 切换正常，Logs Tab 切回时不丢失已有日志。

### S3-3. 删除 designTokens.ts 和 gradients.ts

**前置条件**: 迁移完成，确认无遗漏。

**步骤**：
1. 全局搜索 `designTokens` 引用（目前仅 `MetricChart.tsx` 和 `RunDetailPage.tsx`）
2. 将引用替换为 `theme.useToken()` 等价值，例如：
   - `designTokens.colors.primary` → `token.colorPrimary`
   - `designTokens.spacing.md` → `16`（或直接内联）
   - `designTokens.shadows.sm` → `token.boxShadow` 或内联值
3. 全局搜索 `gradients` 引用，同样替换
4. 确认无引用后删除 `styles/designTokens.ts` 和 `styles/gradients.ts`

验证：无 import 报错，视觉效果不变。

### S3-4. 引入 Error Boundary

**新建文件**: `components/ErrorBoundary.tsx`

```tsx
import React from 'react'
import { Alert, Button } from 'antd'

interface State { hasError: boolean; error?: Error }

export class ErrorBoundary extends React.Component<{ children: React.ReactNode; fallback?: string }, State> {
  state: State = { hasError: false }
  static getDerivedStateFromError(error: Error) { return { hasError: true, error } }
  render() {
    if (this.state.hasError) {
      return <Alert type="error" message={this.props.fallback || 'Component Error'}
        description={this.state.error?.message}
        action={<Button onClick={() => this.setState({ hasError: false })}>Retry</Button>} />
    }
    return this.props.children
  }
}
```

**应用位置**：
- `MetricChart` 外层（防止 ECharts 崩溃白屏）
- `LogsViewer` 外层（防止 WebSocket/ANSI 解析崩溃）
- `RunAssets` 外层（防止 CodeMirror/JSZip 崩溃）

验证：强制触发组件错误时显示 Alert 而非白屏，点击 Retry 可恢复。

### S3-5. 引入 React Query（可选）

**新增依赖**: `@tanstack/react-query`

**范围**：接管主要 API 数据获取：
- `useQuery(['runs'], listRuns)` — 实验列表
- `useQuery(['runDetail', id], () => getRunDetail(id))` — 运行详情
- `useQuery(['stepMetrics', id], () => getStepMetrics(id))` — 指标数据

**收益**：
- 自动缓存：从 RunDetail 返回 ExperimentPage 时无需重新加载
- 智能轮询：`refetchInterval` 配合 `staleTime` 替代手动 setInterval
- 窗口聚焦刷新：`refetchOnWindowFocus` 保证切回标签页时看到最新数据

**注意**：仅用 React Query 管理 Server State。纯 UI 状态（sidebar 开合、主题、对比模式选中 ID）继续用 React state / URL params。

验证：页面切换时数据瞬时展示（缓存命中），后台静默刷新。

### S3-6. 图表系列色色觉障碍验证

使用 Coblis 或 Viz Palette 工具对当前 8 色色板做色盲模拟。

重点检查：`#4C6EF5`(蓝) 与 `#7C3AED`(紫) 在 Deuteranopia 下是否可区分。

如有问题，在相邻色之间增加亮度差异（而非仅靠色相差异）。修正后更新 `chartColors.ts`。

### S3-7. 可访问性增强

**涉及文件**：多个组件

1. **ARIA 标签**：为图标按钮加 `aria-label`：
   - PathTreePanel 开合按钮：`aria-label="Toggle path tree panel"`
   - 表格操作按钮（查看/删除）：`aria-label="View run details"` / `aria-label="Delete run"`
   - Settings 按钮：`aria-label="Open settings"`

2. **Focus 指示器**：全局 CSS 添加：
```css
*:focus-visible {
  outline: 2px solid var(--ant-color-primary);
  outline-offset: 2px;
}
```

3. **键盘导航**：表格行支持 Enter 打开详情。

### S3-8. i18n 降级文案清理

**涉及文件**：多个组件（ExperimentPage、CompareRunsPanel、RunDetailPage 等）

**步骤**：
1. 全局搜索 `|| '` 模式（即 `t('key') || 'English fallback'`）
2. 将 fallback 文本补充到 `locales/en/*.ts` 和 `locales/zh/*.ts`
3. 删除代码中的 `|| 'fallback'`，依赖 i18next 的 `fallbackLng` 机制

验证：切换中英文时所有文案正确显示，无 key 原样展示。

### S3-9. 死代码减重

**配置文件**: `tsconfig.json` + `.eslintrc.*`

1. 在 `tsconfig.json` 中开启 `"noUnusedLocals": true`、`"noUnusedParameters": true`
2. 配置 ESLint 规则 `no-unused-vars`
3. 运行 `npx tsc --noEmit` 和 `npx eslint src/` 获取所有警告
4. 逐一清理未使用的变量、导入、状态

重点关注：
- `ExperimentPage.tsx` 的 `tagEditingRunId`、`statusCheckLoading` 等可能未闭环的状态
- `RunDetailPage.tsx` 中移除叠加对比后残留的未用导入

验证：`tsc --noEmit` 无未使用变量警告。

---

## 全局注意事项

### 色彩策略
- 主色保留 `#1677ff`，不换色
- 语义色如需调整，统一通过 `ConfigProvider` 的 `token` 注入，不硬编码
- 清理主色滥用（渐变底色、glow、装饰）才是解决视觉压力的核心

### 动画策略
- 移除装饰性 framer-motion 动画，保留 CSS transition 微交互
- `PageTransition` 的 `AnimatePresence` + fade 是 framer-motion 唯一保留的使用场景
- 所有保留的动效时长不超过 200ms

### 原则
- **改默认值而非删功能** — Settings 可选项全部保留
- **充分利用 antd 原生组件** — Tag、Empty、Statistic 已具备所需风格
- **每个 Sprint 独立可交付** — 不依赖后续 Sprint，可随时停止
