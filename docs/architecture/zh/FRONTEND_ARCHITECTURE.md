[English](../en/FRONTEND_ARCHITECTURE.md) | [简体中文](FRONTEND_ARCHITECTURE.md)

---

# 前端架构

**文档类型**: 架构  
**目的**: React 应用设计和模式  
**版本**: v0.6.0  
**最后更新**: 2025-01-XX

---

## 应用结构

```
src/
├── App.tsx                # 根组件
├── main.tsx               # 入口点
├── api.ts                 # 集中式 API 客户端
├── i18n.ts                # 国际化
│
├── pages/                 # 页面组件
│   ├── ExperimentPage.tsx
│   ├── RunDetailPage.tsx
│   ├── ArtifactsPage.tsx
│   └── UnifiedRemotePage.tsx
│
├── components/            # 可复用组件
│   ├── MetricChart.tsx
│   ├── LogsViewer.tsx
│   ├── LineageGraph.tsx
│   ├── SettingsDrawer.tsx
│   ├── PathTreePanel.tsx      # v0.6.0 - 路径树导航
│   ├── CompareChartsView.tsx  # v0.6.0 - 多运行比较
│   └── CompareRunsPanel.tsx   # v0.6.0 - 比较模式面板
│
├── contexts/              # React Context
│   └── SettingsContext.tsx
│
├── hooks/                 # 自定义 hooks
│   └── useColumnWidths.ts
│
├── utils/                 # 工具函数
│   ├── format.ts
│   └── logger.ts
│
└── styles/                # 设计系统
    ├── designTokens.ts
    └── resizable-table.css
```

---

## 状态管理

### Context API 模式

```typescript
// Context 中的全局设置
const SettingsContext = createContext<{
  settings: UiSettings
  setSettings: (s: UiSettings) => void
}>()

// App.tsx 中的 Provider
<SettingsProvider value={{ settings, setSettings }}>
  <Routes>...</Routes>
</SettingsProvider>

// 在组件中消费
const { settings } = useSettings()
```

### localStorage 持久化

```typescript
// 保存设置
useEffect(() => {
  localStorage.setItem('ui_settings', JSON.stringify(settings))
}, [settings])

// 加载设置
const [settings, setSettings] = useState(() => {
  const saved = localStorage.getItem('ui_settings')
  return saved ? JSON.parse(saved) : defaultSettings
})
```

---

## 组件模式

### 智能 vs 哑组件

**智能**（容器）:
```typescript
// 获取数据，管理状态
function RunDetailPage() {
  const [run, setRun] = useState(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    fetchRunDetail(id).then(setRun).finally(() => setLoading(false))
  }, [id])
  
  return <RunDetailView run={run} loading={loading} />
}
```

**哑**（展示）:
```typescript
// 仅渲染，不获取数据
function RunDetailView({ run, loading }) {
  if (loading) return <Skeleton />
  return <div>{run.name}</div>
}
```

---

### React.memo 优化

```typescript
// 昂贵的图表组件
const MetricChart = memo(({ metrics, title }) => {
  // 复杂的渲染逻辑
  return <EChartsReact option={option} />
}, (prevProps, nextProps) => {
  // 自定义比较 - 仅在数据更改时重新渲染
  return prevProps.metrics === nextProps.metrics &&
         prevProps.title === nextProps.title
})
```

---

## 性能优化

### 代码分割

```javascript
// vite.config.ts
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        'react-vendor': ['react', 'react-dom'],
        'antd-vendor': ['antd', '@ant-design/icons'],
        'echarts-vendor': ['echarts', 'echarts-for-react']
      }
    }
  }
}

// 结果: 3 个 vendor bundles + 应用代码
// 浏览器分别缓存 vendors
```

### 虚拟滚动

```typescript
// 带虚拟滚动的 Ant Design 表格
<Table
  dataSource={10000items}
  virtual                    // 启用虚拟滚动
  scroll={{ y: 600 }}        // 固定高度
/>
// 仅渲染可见行 + 缓冲区
```

---

## 设计系统

### 设计 Tokens

```typescript
export const designTokens = {
  spacing: {
    xs: 8,
    sm: 12,
    md: 16,
    lg: 24
  },
  colors: {
    primary: '#1677ff',
    success: '#52c41a',
    warning: '#faad14',
    error: '#ff4d4f'
  },
  typography: {
    fontSize: {
      xs: 12,
      sm: 14,
      md: 16,
      lg: 18
    }
  }
}
```

**使用**:
```typescript
<Card style={{
  padding: designTokens.spacing.md,
  borderRadius: designTokens.borderRadius.md
}}>
```

---

## API 通信

### 集中式 API 客户端

```typescript
// api.ts
const BASE_URL = import.meta.env.VITE_API_BASE || '/api'

export async function listRuns() {
  const res = await fetch(`${BASE_URL}/runs`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// 在组件中使用
import { listRuns } from '../api'

const runs = await listRuns()
```

**优势**:
- URL 的单一数据源
- 一致的错误处理
- 易于模拟测试
- TypeScript 类型安全

---

## 性能优化 (v0.5.3) ⚡

### 统一的 MetricChart 组件

**v0.5.3** 引入了统一的 `MetricChart` 组件，同时处理单实验和多实验（对比）场景：

```typescript
// 统一的单实验和多实验图表接口
interface MetricChartProps {
  runs: RunMetric[]      // 单实验: [{ id, metrics }], 多实验: 多个条目
  xKey: string           // X 轴键 (global_step, time 等)
  yKey: string           // Y 轴指标键
  title: string
  height?: number | string
  persistKey?: string    // localStorage 键用于控件持久化
  group?: string         // ECharts 组用于同步缩放
}

// 使用方式 - 单实验
<MetricChart 
  runs={[{ id: runId, metrics: stepMetrics }]} 
  xKey="global_step" 
  yKey="loss" 
  title="训练损失" 
/>

// 使用方式 - 多实验对比
<MetricChart 
  runs={selectedRuns.map(r => ({ id: r.id, label: r.name, metrics: r.metrics }))}
  xKey="global_step" 
  yKey="loss" 
  title="损失对比" 
/>
```

**优势**：
- 所有指标可视化共用单一代码库
- 单实验和对比视图行为一致
- 减小打包体积（移除 `MultiRunMetricChart.tsx`）
- 更易维护和添加新功能

### 图表懒加载

使用 `IntersectionObserver` 懒加载图表：

```typescript
function LazyChartWrapper({ children, height = 320, threshold = 0.1 }) {
  const ref = useRef<HTMLDivElement>(null)
  const [hasLoaded, setHasLoaded] = useState(false)

  useEffect(() => {
    if (hasLoaded) return
    
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setHasLoaded(true)
          observer.disconnect()
        }
      },
      { rootMargin: '200px', threshold }  // 进入视口前 200px 预加载
    )

    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [hasLoaded, threshold])

  return (
    <div ref={ref} style={{ minHeight: height }}>
      {hasLoaded ? children : <Skeleton />}
    </div>
  )
}
```

**优势**：
- 更快的初始页面加载（视口外的图表不渲染）
- 减少多图表页面的内存使用
- 预加载（200px）确保流畅的滚动体验

### 高级 Memo 优化

使用数据指纹进行自定义 memo 比较：

```typescript
const MetricChart = memo(function MetricChart({ runs, xKey, yKey, ... }) {
  // 组件实现
}, (prevProps, nextProps) => {
  // 通过指纹比较 runs 数组，而非引用
  if (prevProps.runs.length !== nextProps.runs.length) return false
  
  for (let i = 0; i < prevProps.runs.length; i++) {
    const prevRun = prevProps.runs[i]
    const nextRun = nextProps.runs[i]
    
    if (prevRun.id !== nextRun.id) return false
    if (prevRun.label !== nextRun.label) return false
    
    // 通过行数和最后步数比较（指纹）
    const prevRowCount = prevRun.metrics?.rows?.length ?? 0
    const nextRowCount = nextRun.metrics?.rows?.length ?? 0
    if (prevRowCount !== nextRowCount) return false
    
    if (prevRowCount > 0) {
      const prevLastStep = prevRun.metrics.rows[prevRowCount - 1]?.global_step
      const nextLastStep = nextRun.metrics.rows[nextRowCount - 1]?.global_step
      if (prevLastStep !== nextLastStep) return false
    }
  }
  
  return prevProps.xKey === nextProps.xKey && prevProps.yKey === nextProps.yKey
})
```

**优势**：
- 当数据引用改变但内容相同时防止不必要的重渲染
- O(1) 比较代替深度相等检查
- 实时更新场景下显著的性能提升

### 后端集成：LTTB 降采样

前端与后端 LTTB（最大三角形三桶）降采样集成：

```typescript
// api.ts - 从设置传递 maxDataPoints
export async function getStepMetrics(runId: string, downsample?: number) {
  const params = downsample ? `?downsample=${downsample}` : ''
  const res = await fetch(`${BASE_URL}/runs/${runId}/metrics_step${params}`)
  return res.json()
}

// RunDetailPage.tsx - 使用 settings.maxDataPoints
const { settings } = useSettings()
const metrics = await getStepMetrics(runId, settings.maxDataPoints)

// 响应包含降采样前的总数
// { columns: [...], rows: [...], total: 100000, sampled: 2000 }
```

**优势**：
- 减少大型实验的数据传输（100k+ 点 → 2k 点）
- LTTB 保留数据的视觉特征
- 可通过 UI 设置配置

---

## 新前端功能（v0.6.0）🆕

### 路径树导航

**组件**: `PathTreePanel.tsx`

ExperimentPage 现在包含 VSCode 风格的路径树面板用于层级导航：

```typescript
// 带 PathTreePanel 的 ExperimentPage 布局
<Layout>
  <Sider width={240}>
    <PathTreePanel
      selectedPath={selectedPath}
      onSelectPath={setSelectedPath}
      onBatchDelete={handleBatchDelete}
      onBatchExport={handleBatchExport}
    />
  </Sider>
  <Content>
    <ExperimentTable pathFilter={selectedPath} />
  </Content>
</Layout>
```

**特性**:
- 带展开/折叠的层级文件夹结构
- 运行计数徽章带运行中指示器动画
- 搜索/过滤路径
- 右键上下文菜单用于批量操作
- 展开状态持久化到 localStorage

### 内联比较视图

**组件**: `CompareRunsPanel.tsx`, `CompareChartsView.tsx`

直接在实验列表页面进行多运行比较：

```typescript
// 比较模式布局
{compareMode ? (
  <Layout>
    <Sider width={280}>
      <CompareRunsPanel
        runs={selectedRuns}
        colors={chartColors}
        visibleRunIds={visibleRunIds}
        onToggleRunVisibility={toggleRunVisibility}
        onBack={() => setCompareMode(false)}
      />
    </Sider>
    <Content>
      <CompareChartsView
        runIds={selectedRunIds}
        visibleRunIds={visibleRunIds}
        metricsMap={metricsMap}
        runLabels={runLabels}
        colors={chartColors}
        loading={loading}
      />
    </Content>
  </Layout>
) : (
  <ExperimentTable onCompare={enterCompareMode} />
)}
```

**核心特性**:
- 自动检测选中运行的共同指标
- 切换单个运行/指标可见性
- ECharts 组同步用于联动缩放
- 颜色编码的运行标识

### 增强的 LogsViewer

**组件**: `LogsViewer.tsx`

带完整 ANSI 颜色支持的终端风格日志查看器：

```typescript
// ANSI 颜色渲染
const ansiConverter = new AnsiToHtml({
  fg: '#e6e9ef',
  bg: '#0b1020',
  colors: { /* 终端颜色调色板 */ }
})

// 带行号和搜索高亮的渲染
{displayLines.map((line, index) => (
  <div className="log-line">
    <span className="line-number">{index + 1}</span>
    <span dangerouslySetInnerHTML={{ __html: ansiConverter.toHtml(line) }} />
  </div>
))}
```

**特性**:
- 完整 ANSI 转义码支持（颜色、粗体等）
- 行号便于参考
- 关键词搜索带高亮
- 智能 tqdm 进度条过滤
- 自动滚动切换
- 复制全部 / 清除按钮

---

## Remote Viewer 前端（v0.5.0）

### 新增页面和组件

```
src/pages/
├── RemoteConnectionPage.tsx   # Remote 连接管理页面
└── RemoteViewerPage.tsx       # Remote Viewer 控制页面

src/components/remote/
├── ConnectionForm.tsx          # SSH 连接表单
├── EnvironmentSelector.tsx    # 环境选择器
├── ViewerStatusIndicator.tsx  # Viewer 状态指示器
└── ConnectionList.tsx          # 连接列表
```

### 状态管理（Remote）

**连接状态管理**:
```typescript
interface RemoteConnection {
  connection_id: string
  host: string
  username: string
  status: 'connected' | 'disconnected' | 'connecting'
  has_viewer: boolean
  viewer_url?: string
  health?: HealthStatus
}

const [connections, setConnections] = useState<RemoteConnection[]>([])
const [activeConnection, setActiveConnection] = useState<string | null>(null)

// 定期轮询健康状态
useEffect(() => {
  const interval = setInterval(async () => {
    for (const conn of connections) {
      const health = await checkConnectionHealth(conn.connection_id)
      updateConnectionHealth(conn.connection_id, health)
    }
  }, 30000)  // 每30秒
  
  return () => clearInterval(interval)
}, [connections])
```

### Remote 连接流程（UI）

**步骤 1: 连接表单**:
```typescript
function ConnectionForm({ onConnect }) {
  const [form] = Form.useForm()
  const [connecting, setConnecting] = useState(false)
  
  const handleSubmit = async (values) => {
    setConnecting(true)
    try {
      const result = await connectToRemote({
        host: values.host,
        port: values.port || 22,
        username: values.username,
        auth_method: values.authMethod,
        private_key_path: values.keyPath,
        password: values.password  // 仅在内存中
      })
      
      message.success('连接成功！')
      onConnect(result.connection_id)
    } catch (error) {
      message.error(`连接失败: ${error.message}`)
    } finally {
      setConnecting(false)
    }
  }
  
  return (
    <Form form={form} onFinish={handleSubmit}>
      <Form.Item name="host" label="主机" rules={[{ required: true }]}>
        <Input placeholder="gpu-server.com" />
      </Form.Item>
      {/* 更多表单字段... */}
      <Button type="primary" htmlType="submit" loading={connecting}>
        连接
      </Button>
    </Form>
  )
}
```

**步骤 2: 环境选择**:
```typescript
function EnvironmentSelector({ connectionId, onSelect }) {
  const [environments, setEnvironments] = useState([])
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    detectEnvironments(connectionId)
      .then(envs => {
        setEnvironments(envs.filter(e => e.is_compatible))
        setLoading(false)
      })
  }, [connectionId])
  
  return (
    <List
      loading={loading}
      dataSource={environments}
      renderItem={env => (
        <List.Item
          actions={[
            <Button 
              type="primary" 
              onClick={() => onSelect(env.name)}
            >
              选择
            </Button>
          ]}
        >
          <List.Item.Meta
            title={env.name}
            description={`Runicorn ${env.runicorn_version} - ${env.python_path}`}
          />
          {env.is_compatible ? (
            <Tag color="green">兼容</Tag>
          ) : (
            <Tag color="red">不兼容</Tag>
          )}
        </List.Item>
      )}
    />
  )
}
```

**步骤 3: 启动 Viewer**:
```typescript
async function startRemoteViewer(connectionId: string, envName: string) {
  // 显示启动进度
  const hide = message.loading('正在启动 Remote Viewer...', 0)
  
  try {
    const result = await startViewer({
      connection_id: connectionId,
      env_name: envName,
      auto_open: false  // 手动控制打开
    })
    
    hide()
    
    // 显示成功，提供打开链接
    Modal.success({
      title: 'Remote Viewer 已启动',
      content: (
        <div>
          <p>Viewer URL: <a href={result.viewer_url} target="_blank">
            {result.viewer_url}
          </a></p>
          <p>启动时间: {result.start_time_ms}ms</p>
        </div>
      ),
      onOk: () => {
        // 在新标签页打开
        window.open(result.viewer_url, '_blank')
      }
    })
  } catch (error) {
    hide()
    Modal.error({
      title: '启动失败',
      content: error.message
    })
  }
}
```

### 状态指示器组件

```typescript
function ViewerStatusIndicator({ connection }: { connection: RemoteConnection }) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'green'
      case 'connecting': return 'blue'
      case 'disconnected': return 'gray'
      default: return 'red'
    }
  }
  
  return (
    <Space>
      <Badge 
        status={getStatusColor(connection.status)} 
        text={connection.status}
      />
      {connection.has_viewer && (
        <>
          <Divider type="vertical" />
          <Tag color="success">Viewer 运行中</Tag>
          <Button 
            type="link" 
            size="small"
            onClick={() => window.open(connection.viewer_url, '_blank')}
          >
            打开
          </Button>
        </>
      )}
      {connection.health && (
        <Tooltip title={`延迟: ${connection.health.latency_ms.toFixed(1)}ms`}>
          <span style={{ color: connection.health.is_healthy ? 'green' : 'red' }}>
            {connection.health.is_healthy ? '✓' : '✗'}
          </span>
        </Tooltip>
      )}
    </Space>
  )
}
```

### 实时健康监控

```typescript
function useConnectionHealth(connectionId: string, interval = 30000) {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  
  useEffect(() => {
    if (!connectionId) return
    
    // 立即检查一次
    checkHealth(connectionId).then(setHealth)
    
    // 定期检查
    const timer = setInterval(() => {
      checkHealth(connectionId).then(setHealth)
    }, interval)
    
    return () => clearInterval(timer)
  }, [connectionId, interval])
  
  return health
}

// 使用
function RemoteViewerControl({ connectionId }) {
  const health = useConnectionHealth(connectionId)
  
  if (!health) return <Spin />
  
  return (
    <Card>
      <Statistic
        title="连接延迟"
        value={health.latency_ms}
        suffix="ms"
        valueStyle={{ color: health.latency_ms < 100 ? 'green' : 'orange' }}
      />
      <Statistic
        title="Viewer 状态"
        value={health.viewer_running ? '运行中' : '已停止'}
        valueStyle={{ color: health.viewer_running ? 'green' : 'red' }}
      />
    </Card>
  )
}
```

### 错误处理（前端）

```typescript
// Remote 特定错误处理
async function handleRemoteError(error: any) {
  // 解析错误
  const errorData = await error.json().catch(() => ({}))
  
  switch (errorData.error) {
    case 'ssh_auth_failed':
      Modal.error({
        title: 'SSH 认证失败',
        content: (
          <div>
            <p>{errorData.message}</p>
            <ul>
              {errorData.suggestions?.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        )
      })
      break
    
    case 'environment_not_found':
      notification.warning({
        message: '未找到兼容环境',
        description: '远程服务器上没有安装 Runicorn 或版本不兼容',
        duration: 10
      })
      break
    
    case 'viewer_start_failed':
      Modal.error({
        title: 'Viewer 启动失败',
        content: errorData.details,
        okText: '查看日志',
        onOk: () => {
          // 打开日志查看器
          showViewerLogs(errorData.connection_id)
        }
      })
      break
    
    default:
      message.error(`操作失败: ${errorData.message || '未知错误'}`)
  }
}
```

---

**相关文档**: [API_DESIGN.md](API_DESIGN.md) | [COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md) | [REMOTE_VIEWER_ARCHITECTURE.md](REMOTE_VIEWER_ARCHITECTURE.md)

**返回**: [架构索引](README.md)

