[English](../en/FRONTEND_ARCHITECTURE.md) | [简体中文](FRONTEND_ARCHITECTURE.md)

---

# 前端架构

**文档类型**: 架构  
**目的**: React 应用设计和模式

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
│   └── SettingsDrawer.tsx
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

