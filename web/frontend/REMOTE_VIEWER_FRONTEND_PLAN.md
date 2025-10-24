# Remote Viewer 前端方案 (VSCode Remote 架构)

**日期**: 2025-10-24  
**状态**: 设计阶段  
**架构**: 类似 VSCode Remote 的远程执行模式

---

## 🎯 核心理念

不同于旧版本的"同步文件到本地"模式，新的 Remote Viewer 采用 **VSCode Remote** 架构：

- ✅ 在远程服务器上运行 Viewer 进程
- ✅ 通过 SSH 隧道转发 HTTP 端口
- ✅ 本地浏览器直接访问远程 Viewer
- ❌ 不再同步文件到本地
- ❌ 不再有 smart/mirror 模式

---

## 📐 架构设计

### 工作流程

```
┌─────────────┐                    ┌─────────────────┐                    ┌─────────────────┐
│   Local PC  │                    │   SSH Tunnel    │                    │  Remote Server  │
│             │                    │                 │                    │                 │
│  Browser    │──HTTP Request──────│  Port Forward   │──SSH Tunnel───────│  Runicorn       │
│  :23301     │←──HTTP Response────│  23300→23301    │                   │  Viewer :23300  │
│             │                    │                 │                    │                 │
└─────────────┘                    └─────────────────┘                    └─────────────────┘
                                                                           │                 │
                                                                           │  /data/runicorn │
                                                                           │  experiments/   │
                                                                           └─────────────────┘
```

### 关键特性

1. **远程执行**：Viewer 在远程服务器上运行
2. **端口转发**：本地端口映射到远程端口
3. **会话管理**：管理多个 Remote Viewer 会话
4. **自动清理**：断开连接时自动停止远程 Viewer

---

## 🎨 UI 设计

### 页面结构

```
Remote Viewer 页面
├── SSH 连接管理区
│   ├── 连接表单（host, port, username, auth）
│   ├── 保存的连接列表
│   └── 连接状态指示器
│
├── 活动会话列表
│   ├── 会话卡片
│   │   ├── 远程主机信息
│   │   ├── 本地访问 URL（可点击）
│   │   ├── 远程路径
│   │   └── 操作按钮（打开、停止、断开）
│   └── 会话统计
│
└── 快速操作栏
    ├── 一键启动（使用保存的配置）
    ├── 批量管理
    └── 帮助文档
```

### 主要组件

#### 1. RemoteViewerPage.tsx

主页面，包含所有功能。

**核心状态**：
- `connections: SavedConnection[]` - 保存的连接配置
- `activeSessions: RemoteSession[]` - 活动的 Remote Viewer 会话
- `connecting: boolean` - 连接中状态
- `selectedConnection: string | null` - 选中的连接

**核心功能**：
- SSH 连接建立
- Remote Viewer 启动
- 会话监控和管理
- 连接配置保存

#### 2. SSHConnectionForm.tsx

SSH 连接配置表单。

**字段**：
```typescript
interface SSHConnectionConfig {
  host: string                    // 远程主机地址
  port: number                    // SSH 端口（默认 22）
  username: string                // SSH 用户名
  authMethod: 'password' | 'key'  // 认证方式
  password?: string               // 密码（如果选择密码认证）
  privateKeyPath?: string         // 私钥路径（如果选择密钥认证）
  passphrase?: string             // 私钥密码短语（可选）
  
  // Remote Viewer 配置
  remoteRoot: string              // 远程存储根目录
  localPort?: number              // 本地端口（可选，自动分配）
  remotePort?: number             // 远程端口（默认 23300）
  
  // 保存配置
  saveName?: string               // 配置名称（用于保存）
}
```

#### 3. RemoteSessionCard.tsx

显示单个 Remote Viewer 会话。

**显示内容**：
- 远程主机 + 端口
- 本地访问 URL（如 `http://localhost:23301`）
- 远程存储路径
- 会话状态（连接中、运行中、停止中）
- 操作按钮（打开新窗口、停止、断开）

#### 4. SavedConnectionsList.tsx

显示保存的连接配置列表。

**功能**：
- 显示已保存的连接
- 一键连接
- 编辑/删除配置
- 配置导入/导出

---

## 🔌 API 集成

### 后端 API 端点

根据架构，需要以下 API 端点：

```typescript
// SSH 连接管理
POST /api/remote/connect
  → 建立 SSH 连接
  
POST /api/remote/disconnect
  → 断开 SSH 连接
  
GET /api/remote/sessions
  → 列出 SSH 会话

// Remote Viewer 管理
POST /api/remote/viewer/start
  → 启动远程 Viewer
  
POST /api/remote/viewer/stop
  → 停止远程 Viewer
  
GET /api/remote/viewer/sessions
  → 列出 Remote Viewer 会话

GET /api/remote/viewer/status/:sessionId
  → 获取会话状态
```

### 前端 API 封装

```typescript
// src/api/remote.ts

export interface RemoteSession {
  sessionId: string
  host: string
  sshPort: number
  localPort: number
  remotePort: number
  remoteRoot: string
  status: 'connecting' | 'running' | 'stopping' | 'stopped'
  startedAt: number
  remotePid?: number
}

export interface SSHSession {
  host: string
  port: number
  username: string
  connectedAt: number
  status: 'connected' | 'disconnected'
}

// 连接到远程服务器
export async function connectRemote(config: SSHConnectionConfig): Promise<SSHSession>

// 启动 Remote Viewer
export async function startRemoteViewer(
  host: string,
  remoteRoot: string,
  localPort?: number,
  remotePort?: number
): Promise<RemoteSession>

// 停止 Remote Viewer
export async function stopRemoteViewer(sessionId: string): Promise<void>

// 断开 SSH 连接
export async function disconnectRemote(host: string): Promise<void>

// 列出活动会话
export async function listRemoteSessions(): Promise<RemoteSession[]>

// 列出 SSH 连接
export async function listSSHSessions(): Promise<SSHSession[]>
```

---

## 🎯 用户流程

### 标准流程

```
1. 用户打开 Remote Viewer 页面
   ↓
2. 填写 SSH 连接信息
   - 主机地址
   - 用户名 + 密码/私钥
   - 远程存储路径
   ↓
3. 点击"连接并启动"
   ↓
4. 后端执行：
   a. 建立 SSH 连接
   b. 在远程服务器上启动 Viewer
   c. 建立 SSH 隧道（端口转发）
   ↓
5. 前端显示：
   - 会话卡片（含本地访问 URL）
   - 状态：运行中
   ↓
6. 用户点击"打开"按钮
   ↓
7. 在新窗口/标签页中打开 Remote Viewer
   → http://localhost:23301
   ↓
8. 用户查看远程实验数据
   ↓
9. 完成后，点击"停止"或"断开连接"
   ↓
10. 后端清理：
    a. 停止远程 Viewer 进程
    b. 关闭 SSH 隧道
    c. 断开 SSH 连接
```

### 快速流程（使用保存的配置）

```
1. 用户从保存的连接列表中选择一个
   ↓
2. 点击"快速启动"
   ↓
3. 自动执行标准流程 步骤 3-7
```

---

## 🎨 界面设计细节

### 连接表单设计

```tsx
<Card title="🔗 新建 Remote Viewer 连接">
  <Form layout="vertical">
    {/* SSH 连接信息 */}
    <Form.Item label="远程主机" required>
      <Input placeholder="192.168.1.100 或 server.example.com" />
    </Form.Item>
    
    <Row gutter={16}>
      <Col span={12}>
        <Form.Item label="SSH 端口">
          <InputNumber defaultValue={22} />
        </Form.Item>
      </Col>
      <Col span={12}>
        <Form.Item label="用户名" required>
          <Input placeholder="username" />
        </Form.Item>
      </Col>
    </Row>
    
    {/* 认证方式 */}
    <Form.Item label="认证方式">
      <Radio.Group>
        <Radio value="password">密码</Radio>
        <Radio value="key">私钥</Radio>
      </Radio.Group>
    </Form.Item>
    
    {/* 密码或私钥 */}
    {authMethod === 'password' ? (
      <Form.Item label="密码" required>
        <Input.Password />
      </Form.Item>
    ) : (
      <>
        <Form.Item label="私钥路径" required>
          <Input placeholder="~/.ssh/id_rsa" />
        </Form.Item>
        <Form.Item label="密码短语（可选）">
          <Input.Password />
        </Form.Item>
      </>
    )}
    
    {/* Remote Viewer 配置 */}
    <Divider>Remote Viewer 设置</Divider>
    
    <Form.Item label="远程存储路径" required>
      <Input placeholder="/data/runicorn" />
      <Button icon={<FolderOpenOutlined />} onClick={browseRemote}>
        浏览...
      </Button>
    </Form.Item>
    
    <Row gutter={16}>
      <Col span={12}>
        <Form.Item label="本地端口" help="留空自动分配">
          <InputNumber placeholder="23301" />
        </Form.Item>
      </Col>
      <Col span={12}>
        <Form.Item label="远程端口">
          <InputNumber defaultValue={23300} />
        </Form.Item>
      </Col>
    </Row>
    
    {/* 保存配置 */}
    <Form.Item>
      <Checkbox>保存此连接配置</Checkbox>
    </Form.Item>
    
    {saveConfig && (
      <Form.Item label="配置名称">
        <Input placeholder="GPU 服务器 - 实验室" />
      </Form.Item>
    )}
    
    {/* 操作按钮 */}
    <Form.Item>
      <Space>
        <Button type="primary" loading={connecting}>
          连接并启动 Viewer
        </Button>
        <Button>测试连接</Button>
        <Button>取消</Button>
      </Space>
    </Form.Item>
  </Form>
</Card>
```

### 会话卡片设计

```tsx
<Card 
  title={
    <Space>
      <CloudServerOutlined />
      {session.host}
      <Badge status={statusMap[session.status]} />
    </Space>
  }
  extra={
    <Space>
      <Button 
        type="primary" 
        icon={<LinkOutlined />}
        onClick={() => window.open(`http://localhost:${session.localPort}`)}
      >
        打开 Viewer
      </Button>
      <Button icon={<StopOutlined />} onClick={handleStop}>
        停止
      </Button>
      <Button 
        danger 
        icon={<DisconnectOutlined />} 
        onClick={handleDisconnect}
      >
        断开
      </Button>
    </Space>
  }
>
  <Descriptions column={2} size="small">
    <Descriptions.Item label="本地访问">
      <a href={`http://localhost:${session.localPort}`} target="_blank">
        http://localhost:{session.localPort}
      </a>
    </Descriptions.Item>
    <Descriptions.Item label="远程路径">
      <Text code>{session.remoteRoot}</Text>
    </Descriptions.Item>
    <Descriptions.Item label="SSH 端口">
      {session.sshPort}
    </Descriptions.Item>
    <Descriptions.Item label="远程 Viewer 端口">
      {session.remotePort}
    </Descriptions.Item>
    <Descriptions.Item label="远程 PID">
      {session.remotePid || 'N/A'}
    </Descriptions.Item>
    <Descriptions.Item label="启动时间">
      {dayjs(session.startedAt).fromNow()}
    </Descriptions.Item>
  </Descriptions>
  
  {/* 状态指示器 */}
  <Alert 
    type={session.status === 'running' ? 'success' : 'info'}
    message={statusMessages[session.status]}
    showIcon
  />
</Card>
```

### 保存的连接列表

```tsx
<Card title="📋 保存的连接">
  <List
    dataSource={savedConnections}
    renderItem={conn => (
      <List.Item
        actions={[
          <Button 
            type="primary" 
            icon={<ThunderboltOutlined />}
            onClick={() => quickConnect(conn)}
          >
            快速启动
          </Button>,
          <Button icon={<EditOutlined />}>编辑</Button>,
          <Button danger icon={<DeleteOutlined />}>删除</Button>
        ]}
      >
        <List.Item.Meta
          avatar={<Avatar icon={<CloudServerOutlined />} />}
          title={conn.name}
          description={
            <Space direction="vertical" size={0}>
              <Text type="secondary">{conn.username}@{conn.host}</Text>
              <Text type="secondary" code>{conn.remoteRoot}</Text>
            </Space>
          }
        />
      </List.Item>
    )}
  />
</Card>
```

---

## 🔧 技术实现要点

### 1. WebSocket 状态同步

虽然不是必需，但可以用 WebSocket 实时更新会话状态：

```typescript
// 监听会话状态变化
const ws = new WebSocket('ws://localhost:23300/api/remote/viewer/events')

ws.onmessage = (event) => {
  const update = JSON.parse(event.data)
  if (update.type === 'session_status') {
    updateSessionStatus(update.sessionId, update.status)
  }
}
```

### 2. 本地存储管理

保存的连接配置存储在浏览器 localStorage 中：

```typescript
const STORAGE_KEY = 'runicorn_saved_connections'

export function saveConnection(config: SSHConnectionConfig) {
  const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  saved.push({
    id: generateId(),
    name: config.saveName,
    host: config.host,
    port: config.port,
    username: config.username,
    authMethod: config.authMethod,
    remoteRoot: config.remoteRoot,
    // 不保存密码和私钥内容，只保存路径
    privateKeyPath: config.privateKeyPath,
    createdAt: Date.now()
  })
  localStorage.setItem(STORAGE_KEY, JSON.stringify(saved))
}
```

### 3. 错误处理

完善的错误提示：

```typescript
try {
  await startRemoteViewer(config)
  message.success('Remote Viewer 启动成功！')
} catch (error) {
  if (error.code === 'SSH_AUTH_FAILED') {
    message.error('SSH 认证失败，请检查用户名和密码')
  } else if (error.code === 'REMOTE_PATH_NOT_FOUND') {
    message.error(`远程路径不存在: ${config.remoteRoot}`)
  } else if (error.code === 'PORT_IN_USE') {
    message.error(`本地端口 ${config.localPort} 已被占用`)
  } else {
    message.error(`连接失败: ${error.message}`)
  }
}
```

### 4. 自动重连机制

当 SSH 连接断开时，提示用户并提供重连选项：

```typescript
function watchConnection(sessionId: string) {
  const intervalId = setInterval(async () => {
    try {
      const status = await getSessionStatus(sessionId)
      if (status === 'disconnected') {
        clearInterval(intervalId)
        Modal.confirm({
          title: '连接已断开',
          content: 'Remote Viewer 会话已断开，是否重新连接？',
          onOk: () => reconnect(sessionId)
        })
      }
    } catch (error) {
      // 忽略错误，继续轮询
    }
  }, 5000) // 每 5 秒检查一次
}
```

---

## 📦 文件结构

```
web/frontend/src/
├── pages/
│   └── RemoteViewerPage.tsx          # 主页面
│
├── components/
│   └── remote/
│       ├── SSHConnectionForm.tsx     # SSH 连接表单
│       ├── RemoteSessionCard.tsx     # 会话卡片
│       ├── SavedConnectionsList.tsx  # 保存的连接列表
│       └── RemoteStatusIndicator.tsx # 状态指示器（可选）
│
├── api/
│   └── remote.ts                     # Remote API 封装
│
├── types/
│   └── remote.ts                     # TypeScript 类型定义
│
├── hooks/
│   ├── useRemoteSessions.ts          # 会话管理 Hook
│   └── useSavedConnections.ts        # 保存的连接管理 Hook
│
└── locales/
    ├── zh/
    │   └── remote.ts                 # 中文翻译
    └── en/
        └── remote.ts                 # 英文翻译
```

---

## 🎯 开发优先级

### Phase 1: 核心功能（MVP）
- [ ] RemoteViewerPage 主页面框架
- [ ] SSHConnectionForm 连接表单
- [ ] Remote API 集成
- [ ] 基本会话管理（启动、停止、断开）
- [ ] RemoteSessionCard 会话卡片

### Phase 2: 增强功能
- [ ] 保存的连接配置
- [ ] SavedConnectionsList 组件
- [ ] 快速启动功能
- [ ] 连接状态实时更新

### Phase 3: 用户体验优化
- [ ] 完整的错误处理
- [ ] 自动重连机制
- [ ] 会话统计和监控
- [ ] 帮助文档和向导

---

## 🔍 与旧版本对比

| 特性 | 旧版本（Sync）| 新版本（Remote）|
|------|-------------|----------------|
| 文件位置 | 本地（同步） | 远程（不同步）|
| Viewer 位置 | 本地运行 | 远程运行 |
| 延迟 | 低（本地文件）| 中（网络延迟）|
| 存储占用 | 高（重复数据）| 低（仅元数据缓存）|
| 实时性 | 需要同步 | 完全实时 |
| 复杂度 | 高（同步逻辑）| 低（SSH 隧道）|
| 可靠性 | 中（同步可能失败）| 高（直接访问）|

---

## 🎉 总结

新的 Remote Viewer 前端采用简洁的 VSCode Remote 架构：

✅ **核心理念**: 远程执行 + SSH 隧道  
✅ **用户体验**: 简单、直观、可靠  
✅ **技术实现**: 标准 SSH + 端口转发  
✅ **维护成本**: 低（无复杂同步逻辑）

---

**下一步**: 开始实现 Phase 1 核心功能

