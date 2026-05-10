# Runicorn 前端测试体系建设方案
## 1. 现状分析
**源码规模**: ~85 个源文件，分布在 utils(5)、hooks(8)、api(3)、components(~40)、pages(6)、contexts(2)、types(1)、locales(6)、styles(3)
**现有测试**: 已有 Vitest 单测/组件测试/页面集成测试，以及 `web/frontend/tests/smoke/` 下的 Playwright mocked browser smoke。
**构建工具**: Vite 5 + TypeScript 5 + React 18，ESModule 模式。
**依赖特征**: 重度依赖 Ant Design（UI）、ECharts（图表）、React Query（数据请求）、react-router-dom（路由）、i18next（国际化）、framer-motion（动画）、CodeMirror 6（代码编辑器）。
## 2. 测试框架选型
**测试运行器**: Vitest（与 Vite 共享配置和转换管线，零额外构建配置，原生 ESM 支持）
**DOM 环境**: happy-dom（比 jsdom 快 2-3x，足够覆盖本项目需求；仅在 CodeMirror 等需要完整 DOM 的场景降级 jsdom）
**组件测试**: @testing-library/react + @testing-library/user-event
**HTTP Mock**: msw (Mock Service Worker)（拦截 fetch 级别，不侵入 api.ts 代码）
**覆盖率**: @vitest/coverage-v8（基于 V8 引擎，无需 istanbul 转换）
**快照测试**: Vitest 内置
**浏览器级 smoke**: Playwright（已落地为 mocked browser smoke，用于验证关键 UI 主流程；不等同于真实后端联调 E2E）
### 需要安装的依赖
```warp-runnable-command
devDependencies:
  vitest
  @vitest/coverage-v8
  happy-dom
  @testing-library/react
  @testing-library/jest-dom
  @testing-library/user-event
  msw
```
## 3. 目录结构
```warp-runnable-command
web/frontend/
├── vitest.config.ts          # 测试专用配置（继承 vite.config.ts）
├── src/
│   ├── __tests__/            # 集成级测试（跨模块交互）
│   │   └── setup.ts          # 全局 setup（happy-dom、RTL matchers、msw server）
│   ├── __mocks__/            # 手动 mock 模块
│   │   ├── api.ts            # api.ts 的 mock（供 hook 测试使用）
│   │   └── matchMedia.ts     # window.matchMedia polyfill
│   ├── utils/
│   │   ├── format.ts
│   │   ├── format.test.ts          # ← 同目录放置
│   │   ├── assetIdentity.ts
│   │   ├── assetIdentity.test.ts
│   │   ├── assetParse.ts
│   │   ├── assetParse.test.ts
│   │   ├── assetDownload.ts
│   │   └── assetDownload.test.ts
│   ├── hooks/
│   │   ├── useExperimentFilters.ts
│   │   ├── useExperimentFilters.test.ts
│   │   └── ...（每个 hook 同目录对应 .test.ts）
│   ├── components/
│   │   ├── settings/
│   │   │   ├── themePresets.ts
│   │   │   └── themePresets.test.ts
│   │   ├── FilterToolbar.tsx
│   │   ├── FilterToolbar.test.tsx
│   │   └── ...
│   └── api/
│       └── __tests__/
│           └── api.test.ts         # API 层 + msw 集成测试
```
**文件命名约定**: `*.test.ts(x)`，与源文件同目录。集成测试放 `src/__tests__/`。
## 4. 配置文件设计
### vitest.config.ts
关键配置项：
* `environment: 'happy-dom'`
* `globals: true`（启用全局 describe/it/expect，减少 import 噪音）
* `setupFiles: ['./src/__tests__/setup.ts']`
* `include: ['src/**/*.test.{ts,tsx}']`
* `coverage.provider: 'v8'`，`coverage.include: ['src/**/*.{ts,tsx}']`，`coverage.exclude: ['**/*.test.*', '**/__mocks__/**', '**/__tests__/**', 'src/main.tsx', 'src/vite-env.d.ts', 'src/locales/**']`
* `alias: { '@': path.resolve(__dirname, 'src') }` — 与 vite.config.ts 保持一致
* `deps.inline: [/antd/, /@ant-design/]` — 避免 ESM 解析问题
### setup.ts
* 引入 `@testing-library/jest-dom`（提供 `toBeInTheDocument()` 等匹配器）
* Mock `window.matchMedia`（Ant Design 内部使用）
* Mock `ResizeObserver`（ECharts / react-virtual 使用）
* Mock `IntersectionObserver`（LazyChartWrapper 使用）
* Mock `localStorage`（多个 hook 使用持久化）
* 初始化 msw server（`beforeAll/afterEach/afterAll`）
* Mock `import.meta.env` 以设置 `VITE_API_BASE`
### package.json 新增 scripts
```json
"test": "vitest run",
"test:watch": "vitest",
"test:coverage": "vitest run --coverage",
"test:ui": "vitest --ui"
```
## 5. 测试分层与详细用例
### 第一层：纯函数单测（零依赖，最高 ROI）
#### 5.1 utils/format.ts（6 个函数，~25 个用例）
**formatFileSize / formatBytes**
* 0 bytes → `'0 B'`
* 1023 → `'1023 B'`（边界：未进入 KB）
* 1024 → `'1 KB'`
* 1048576 → `'1 MB'`
* 大数：`1099511627776` → `'1 TB'`
* 负数处理（防御性）
**formatTimestamp**
* 0 → `'-'`
* 秒级时间戳（10 位）自动转毫秒
* 毫秒级时间戳（13 位）直接使用
* NaN/无效值 → `'-'`
* 验证输出格式包含 年/月/日/时/分/秒
**formatDuration**
* 0 → `'0s'`
* 负数 → `'0s'`
* 纯秒：`5000` → `'5s'`
* 带分钟：`65000` → `'1m 5s'`
* 带小时：`3661000` → `'1h 1m'`
* 带天：`90061000` → `'1d 1h'`
**formatRelativeTime**
* 0 → `'-'`
* 刚才（< 60s）→ 包含 "now" / "second" 类字样
* 5 分钟前
* 3 小时前
* 2 天前
* 超过 30 天 → 回退到 formatTimestamp 格式
* locale 参数传 'zh' → 中文输出
* 未来时间戳 → 回退到 formatTimestamp
**formatPercent**
* `0.1234` → `'12.34%'`
* `NaN` → `'-'`
* 自定义 precision
**formatNumber**
* `1234567` → 包含千位分隔符
* `NaN` → `'-'`
* 带 precision 参数
**truncateText / formatRunId**
* 空字符串 → 空 / `'-'`
* 短于 maxLength → 原样返回
* 超过 maxLength → 末尾含 `'...'`
#### 5.2 utils/assetIdentity.ts（5 个函数，~20 个用例）
**buildAssetIdentity**
* 有 fingerprint → `idType: 'fingerprint'`
* 无 fingerprint 有 archive_path → `idType: 'archive_path'`
* 无以上有 source_uri → `idType: 'source_uri'`
* 全空 → `idType: 'name'`, `idValue: '-'`
* 空白字符串 fingerprint 应被跳过（trim 后为空）
**assetIdentityToString**
* 正确拼接 `kind:idType:idValue`
**encodeAssetIdentity / decodeAssetIdentity 往返**
* 编码后解码 → 与原始 identity 深度相等
* 包含特殊字符（中文、/、=、+）的 idValue 往返不丢失
* 非法 base64 字符串 → `null`
* 非法 JSON → `null`
* 缺少 kind/idType/idValue 字段 → `null`
**base64UrlEncode / base64UrlDecode（间接测试）**
* 输出不含 `+`, `/`, `=`
* 通过 encode → decode 往返验证
#### 5.3 utils/assetParse.ts（~15 个用例）
**parseRunAssetsPayload**
* `null` / `undefined` / `{}` → `[]`
* 仅有 code snapshot → 返回 1 个 kind='code' 的 ParsedAsset
* 仅有 config → 返回 kind='config'
* datasets 数组（多个）→ 正确解析 name、fingerprint、uri
* pretrained 数组 → 解析 source_type、description
* outputs 数组 → saved 始终为 true
* 混合 payload → 输出顺序：code → config → datasets → pretrained → outputs
* fingerprint 为 object → stableStringify 处理
* fingerprint 为 number → 转字符串
* 缺少 name 字段 → 使用 `dataset_0` 等默认命名
**stableStringify（间接测试）**
* 对象键排序稳定（`{b:1,a:2}` === `{a:2,b:1}`）
* 嵌套对象 / 数组
* null / undefined
#### 5.4 utils/assetDownload.ts（~12 个用例）
**sanitizeFilename**
* 替换 `\` 和 `/` 为 `_`
* 多空格压缩为单空格
* 前后 trim
* 空字符串 → `''`
**suggestAssetDownloadFilename**
* kind='code' → `'code_snapshot.zip'`
* kind='config' → `'config.json'`
* 普通 dataset 有 archive_path 以 .zip 结尾 → 自动加 .zip 后缀
* 无 name/meta → 回退 `'asset'`
**isProbablyTextFilename**
* `.py`, `.json`, `.yaml`, `.md` → `true`
* `.png`, `.bin`, `.exe` → `false`
* 空字符串 → `false`
* 大小写不敏感：`.JSON` → `true`
#### 5.5 components/settings/themePresets.ts（~8 个用例）
**detectActivePreset**
* 传入与 'default' preset 完全匹配的 settings → 返回 `'default'`
* 传入 'minimal' preset 的 settings → 返回 `'minimal'`
* 修改其中一个字段后不再匹配 → 返回 `undefined`
* 传入自定义 settings（不匹配任何预设）→ `undefined`
**themePresets 数据完整性**
* 每个 preset 有唯一 key
* 每个 preset 有 labelKey
* swatch 是长度为 2 的数组
* settings 中的 themeMode 值合法
### 第二层：Hook 单测（需 renderHook + Mock）
#### 5.6 useExperimentFilters（~12 个用例）
**filteredRuns 过滤逻辑**
* 空搜索 + 无过滤器 → 返回全部 runs
* searchText 匹配 run_id → 仅返回匹配项
* searchText 匹配 alias → 仅返回匹配项
* searchText 匹配 tags → 仅返回匹配项
* projectFilter 过滤 → 仅返回该 project 下的 runs
* statusFilter='running' → 仅返回 running 状态
* selectedTreePath 过滤 → 返回该路径及子路径
* 多个过滤器叠加（AND 逻辑）
**状态持久化**
* pageSize 变更后写入 localStorage
* 初始化时从 localStorage 恢复 pageSize
* treePanelCollapsed 持久化
**handleResizeStart**
* 拖动调整 width 在 160-400 范围内
#### 5.7 useExperimentData（~6 个用例，需 mock api + React Query）
* 初始加载返回 mapped RunData[]
* autoRefresh=true 时 refetchInterval 生效
* fetchRuns 调用 invalidateQueries
* handleBatchDeleteByPath 成功 → message.success
* handleBatchDeleteByPath deleted_count=0 → message.info
* handleBatchExportByPath 构建正确的下载 URL
#### 5.8 useCompareMode（~8 个用例，需 mock api + router）
* 初始状态 compareMode=false
* handleCompare 少于 2 个选中 → message.warning
* handleCompare 正常流程 → setSearchParams、fetch metrics
* toggleRunVisibility 切换可见性
* handleExitCompare 清空所有状态
* URL 中有 compare 参数 → 自动恢复对比模式
* 有 running 状态的 run → 自动刷新 metrics
#### 5.9 useInlineEditing（~8 个用例，需 mock api）
* handleAliasEdit 设置正确的 editingRunId 和 editingAlias
* handleAliasSave 调用 updateRunAlias API
* handleAliasSave 成功 → 乐观更新 runs 数组
* handleAliasSave 失败 → message.error
* handleAliasCancel 重置状态
* handleRemoveTag 从 tags 中移除指定 tag
* handleOpenTagModal / handleAddTagFromModal / handleCloseTagModal 完整流程
* allTagsFromRuns 从所有 runs 收集去重标签
#### 5.10 useColumnWidths（~5 个用例，需 mock api）
* 初始化使用 defaultWidths
* loadPreferences 从 API 获取覆盖默认值
* setColumnWidth 更新单列宽度并触发 debounced save
* resetWidths 恢复默认值
* windowResize 事件触发重新加载
#### 5.11 useAssetsIndex（~5 个用例，需 mock api）
* 初始从 localStorage 缓存恢复
* refresh 调用 listRuns + 并发 getRunAssets
* buildIndexFromRuns 正确聚合 experiments 和 repo
* cancel 设置 abort flag
* stats 正确计算 totalRuns / runsWithAssets / totalAssets / archivedAssets
### 第三层：API 层测试（msw 拦截）
#### 5.12 api.ts apiFetch（~10 个用例）
* GET 请求正常返回 JSON
* POST 请求发送 correct headers 和 body
* 服务端返回 4xx → 抛出 Error，message 为响应文本
* 服务端返回 5xx → 抛出 Error
* health() 超时 → abort signal 触发
* health() 正常返回
* exportRunsZip 触发 blob 下载（mock createObjectURL）
* previewImport 发送 FormData
* confirmImport 发送正确 mode
#### 5.13 api/remote.ts（~6 个用例）
* connectRemote 成功返回 SSHSession
* connectRemote 失败 → 抛出 ApiError
* ensureOk 解析 detail 字段
* startRemoteViewer 无 remoteRoot → 抛出本地 Error
* listRemoteSessions 返回 sessions 数组
#### 5.14 api/preferences.ts（~4 个用例）
* getDismissedAlerts 正常返回数组
* dismissAlert 发送 POST
* undismissAlert 发送 POST
* 响应非 ok → 抛出 Error
### 第四层：组件测试（RTL 渲染级）
#### 5.15 FilterToolbar（~6 个用例）
* 渲染搜索框、项目下拉、状态下拉、刷新按钮
* 搜索输入触发 onSearchChange 回调
* selectedCount > 0 时显示 Compare / Export / Delete 按钮
* selectedCount === 0 时隐藏批量操作按钮
* Compare 按钮在 selectedCount < 2 时 disabled
* autoRefresh checkbox 触发 onAutoRefreshChange
#### 5.16 StatsBar（~3 个用例）
* 渲染 total / running / finished / failed 四个统计数字
* stats 全部为 0 时正常渲染
* 数字正确匹配传入 props
#### 5.17 StatusTag（~4 个用例）
* status='running' → 显示 processing 颜色
* status='finished' → 显示 success 颜色
* status='failed' → 显示 error 颜色
* status='unknown' → 显示 default
#### 5.18 RecycleBin（~5 个用例，需 mock API）
* open=true 时渲染 Modal
* open=false 时不渲染
* 加载后显示删除的 runs 列表
* 选中 runs 后 Restore 按钮可点击
* 空回收站显示空状态文案
#### 5.19 ErrorBoundary（~3 个用例）
* 子组件正常 → 渲染子组件
* 子组件抛出错误 → 渲染 fallback
* fallback 为字符串时正确显示
#### 5.20 DismissibleAlert（~3 个用例）
* 渲染 alert 内容
* 点击关闭后调用 dismiss API
* 已关闭的 alert 不再显示
### 第五层：集成测试
#### 5.21 ExperimentPage 数据流（~3 个用例）
* msw 模拟 `/api/runs` → 页面渲染 Table
* 搜索过滤 → Table 行数减少
* 选中行 → 批量操作栏出现
#### 5.22 i18n 完整性验证（自动化检查）
* 遍历 en 和 zh 的所有 key → 两者 key 集合完全一致
* 无孤儿 key（en 有但 zh 没有，反之亦然）
## 6. Mock 策略
### 6.1 API Mock（msw）
使用 msw 的 `setupServer` 在 Node 环境拦截 fetch。定义 `src/__mocks__/handlers.ts` 包含所有 API endpoint 的默认 happy-path 响应。单个测试可通过 `server.use()` 覆盖特定 handler 来模拟异常情况。
好处：不修改 api.ts 源代码，测试的是真实 fetch 行为。
### 6.2 浏览器 API Mock
* `window.matchMedia` → 返回固定的 `{ matches: false, addEventListener: vi.fn() }`
* `ResizeObserver` → stub 类，构造时记录 callback
* `IntersectionObserver` → stub 类
* `localStorage` → 使用内存 Map 实现，每个测试 beforeEach 清空
* `navigator.clipboard` → `{ writeText: vi.fn() }`
* `URL.createObjectURL` / `URL.revokeObjectURL` → `vi.fn()`
* `window.open` → `vi.fn()`
### 6.3 重型第三方库 Mock
* `echarts` / `echarts-for-react` → mock 为空组件（组件测试中不验证图表渲染）
* `@codemirror/*` → mock 为 `<div data-testid="codemirror" />`
* `framer-motion` → mock `motion.div` 为普通 `div`
* `react-router-dom` → 使用 `MemoryRouter` 包裹
* `react-i18next` → mock `useTranslation` 返回 `t: (key) => key`（测试中验证 i18n key 而非翻译文本）
### 6.4 React Query Mock
测试 Hook 时使用 `QueryClientProvider` 包裹，配置 `retry: false`、`cacheTime: 0`。
提供 `createTestQueryClient()` 工具函数。
## 7. 覆盖率目标
### 阶段一（本分支目标）
* **utils/**: 行覆盖率 ≥ 95%，分支覆盖率 ≥ 90%
* **hooks/**: 行覆盖率 ≥ 80%
* **api层**: 行覆盖率 ≥ 70%
* **组件层**: 仅覆盖 FilterToolbar、StatsBar、StatusTag、ErrorBoundary、RecycleBin
* **全局**: 行覆盖率 ≥ 40%（因组件大量未覆盖）
### 阶段二（后续迭代）
* 组件覆盖扩展到所有非图表组件
* 全局行覆盖率 ≥ 60%
* 在现有 mocked browser smoke 之外，再视需要补真实后端联调或更高层 E2E
## 8. 实施顺序
**Step 1**: 基础设施搭建
* 安装依赖
* 创建 vitest.config.ts
* 创建 setup.ts（全局 mock）
* 创建 `__mocks__/` 目录和基础 mock
* 验证 `vitest run` 能跑通空测试
**Step 2**: utils 纯函数测试（format → assetIdentity → assetParse → assetDownload → themePresets）
**Step 3**: API 层测试（配置 msw handlers → 测试 apiFetch → 测试各 endpoint）
**Step 4**: Hook 测试（useExperimentFilters → useInlineEditing → useCompareMode → useExperimentData → useColumnWidths → useAssetsIndex）
**Step 5**: 组件测试（FilterToolbar → StatsBar → StatusTag → ErrorBoundary → RecycleBin）
**Step 6**: 集成测试 + i18n 完整性
**Step 7**: 覆盖率报告审查，补充遗漏分支
## 9. CI 集成建议（参考）
```yaml
# .github/workflows/ci.yml
steps:
  - uses: actions/setup-node@v4
  - run: npm ci
    working-directory: web/frontend
  - run: npm test -- --reporter=junit --outputFile=test-results.xml
    working-directory: web/frontend
  - run: npm run test:coverage
    working-directory: web/frontend
  - run: npx playwright install --with-deps chromium
    working-directory: web/frontend
  - run: npm run test:smoke
    working-directory: web/frontend
```
说明：

* `vitest` 负责单元、组件和页面集成测试。
* `test:smoke` 是 mocked browser smoke，覆盖浏览器中的关键 UI 主流程。
* `test:smoke` 依赖 Playwright + 本地 Vite dev server，但 API 仍由 mock 驱动，不代表真实 remote backend 端到端联调。
* 设置 coverage 阈值时，应针对 `vitest` 报告，不要把 smoke 结果误解为更高层交付证明。
## 10. 测试编写规范
**命名**: `describe('函数名/组件名', () => { it('should 行为描述', ...) })`
**结构**: Arrange → Act → Assert，避免在一个 test 中验证多个不相关行为
**隔离**: 每个 test 独立，不依赖执行顺序。beforeEach 清理共享状态（localStorage、msw handlers）
**断言**: 优先用具体断言（`toEqual`, `toContain`）而非 `toBeTruthy`。组件测试优先用 `getByRole` / `getByText` 而非 `getByTestId`
**Mock 最小化**: 只 mock 必要的外部依赖，不 mock 被测模块内部函数
**不测实现细节**: Hook 测试验证返回值和副作用，不验证内部 state 变化。组件测试验证用户可见行为，不验证 DOM 结构
## 11. 实施进度与当前状态
> 最后更新: 2026-05-09 — smoke/CI 边界说明与当前状态校对完成

### 测试规模
| 指标 | 阶段一 | 阶段二 | 阶段三（当前） |
|------|--------|--------|----------------|
| 测试文件 | 20 | 23 | **27** |
| 测试用例 | 252 | 377 | **414** |
| 运行耗时 | ~50s | ~60s | **~85s** |
| 分支 | `test/frontend-tests` | 同左 | 同左 |

### 测试文件清单（27 个）
**基础设施** (2):
- `src/__tests__/setup.ts` — 全局 mock（matchMedia, ResizeObserver, IntersectionObserver, localStorage, URL, WebSocket）
- `src/__mocks__/handlers.ts` + `server.ts` — msw 服务器和默认 API handlers

**utils 纯函数** (6):
- `format.test.ts` (38), `assetIdentity.test.ts` (13), `assetParse.test.ts` (27), `assetDownload.test.ts` (27), `themePresets.test.ts` (65), `logger.test.ts` (12)

**API 层** (3):
- `api/__tests__/api.test.ts` (65), `preferences.test.ts` (6), `remote.test.ts` (32)

**Hooks** (6):
- `useExperimentFilters.test.ts` (22), `useExperimentData.test.ts` (11), `useCompareMode.test.ts` (11), `useInlineEditing.test.ts` (7), `useColumnWidths.test.ts` (4), `useAssetsIndex.test.ts` (6)

**组件** (6):
- `FilterToolbar.test.tsx` (6), `StatsBar.test.tsx` (3), `StatusTag.test.tsx` (4), `ErrorBoundary.test.tsx` (3), `DismissibleAlert.test.tsx` (3), `RecycleBin.test.tsx` (5)

**集成测试** (3):
- `ExperimentPage.test.tsx` (3), `RunDetailPage.test.tsx` (15), `AssetsPage.test.tsx` (14)

**其他** (3):
- `i18n.test.ts` (4), `AddTagModal.test.tsx` (17), `RemoteViewerPage.test.tsx` (1)

### 当前 CI / 交付面边界
- `.github/workflows/ci.yml` 中的 frontend smoke job 运行 `npm run test:smoke`，覆盖 `web/frontend/tests/smoke/viewer.spec.ts` 与 `web/frontend/tests/smoke/remote.spec.ts` 这两条 mocked browser smoke。
- 同一个 CI workflow 中的 Python job 继续运行默认 `pytest -q`，当前关键交付面 integration 用例至少包括：
  - `tests/integration/test_viewer_remote_api.py`：当前 `/api/remote/*` 主路径、已保存连接和 remote viewer 启动链
  - `tests/integration/test_config_migration.py`：历史 XOR 凭据向 Fernet `connections.json` 的迁移边界
- 这些 Python integration 用例当前并未拆成独立 workflow/job，而是作为默认 pytest 集的一部分提供回归保护。

### 覆盖率达标情况
| 区域 | 目标 | 实际 | 状态 |
|------|------|------|------|
| utils/ 行覆盖率 | ≥95% | 97.48% | ✅ |
| utils/ 分支覆盖率 | ≥90% | 90.55% | ✅ |
| hooks/（计划范围 6 文件均值） | ≥80% | ~88.2% | ✅ |
| API 层 api.ts | ≥70% | 100% | ✅ |
| API 层 api/ 目录 | ≥70% | 94.05% | ✅ |
| 页面集成测试 | P0 完成 | ExperimentPage + RunDetailPage + AssetsPage | ✅ |
| 业务组件测试 | P1 部分完成 | AddTagModal ✅, DismissedAlertsManager ⏳ | ✅/⏳ |

### 阶段三新增（+46 用例，+3 文件）
| 文件 | 用例数 | 内容 |
|------|--------|------|
| `RunDetailPage.test.tsx` | 15 | 加载详情、状态渲染(running/finished/failed)、Tabs 切换、指标图表渲染、空指标、统计信息、子组件挂载(LogsViewer/RunAssets)、骨架屏、API 错误容错 |
| `AssetsPage.test.tsx` | 14 | 页面标题/统计、Overview 表格、Repo 表格（tab 切换）、过滤控件、saved/ref 标签、空 index 容错、存储统计 API、刷新按钮 |
| `AddTagModal.test.tsx` | 17 | Modal 开关、输入验证、确认提交(trim)、Enter/Escape 键盘、推荐/历史标签过滤、点击标签直接提交、上限10个历史标签、重新打开清空输入 |

### 已发现并修复的源码问题
1. **RecycleBin.tsx 无限重渲染**（阶段一）：`useCallback` 依赖 `t`（不稳定引用）导致与 `useEffect` 形成无限循环。已移除 `t` 依赖。
2. **handlers.ts StorageStats 不完整**（阶段三）：`/api/storage/stats` mock 缺少 `archive` 字段，导致 AssetsPage 在测试中 crash。已补全完整结构。
3. **英文 locale 缺失 key**（阶段一）：`remote.env.cancelButton` 和 `remote.env.confirmButton` 缺失，已补齐。

### 剩余可做工作（优先级从高到低）
1. **P1** DismissedAlertsManager 组件测试（小范围，~5 个用例）
2. **P2** useRemoteSessions / useSavedConnections hooks 测试（等 Remote 功能迭代时顺带）
3. **不推荐** 把 mocked smoke 继续膨胀成全量 E2E，也不推荐为覆盖率数字而牺牲测试可维护性
