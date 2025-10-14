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

**相关文档**: [API_DESIGN.md](API_DESIGN.md) | [COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md)

**返回**: [架构索引](README.md)

