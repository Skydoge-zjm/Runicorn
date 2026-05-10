# 前端构建体积对比记录（2026-04-27）

## 目的

记录 `ISSUE-P2-01` 与 `ISSUE-P2-02` 的实际构建产物变化，避免后续前端拆包优化只能靠口头描述。

## 执行命令

在 `E:\pycharm_project\Runicorn\web\frontend` 下执行：

```powershell
npm run build
```

## 优化前（来自本轮评估基线）

- `assets/echarts-vendor-*.js`：约 `1.0 MB`
- `assets/antd-vendor-*.js`：约 `1.1 MB`
- `assets/index-*.js`：约 `1.6 MB`
- 构建状态：通过，但有 chunk size warning

## 本轮优化内容

1. 在 `web/frontend/src/App.tsx` 对路由页面启用 `React.lazy` / `Suspense`
2. 在 `web/frontend/src/components/assets/AssetPreview.tsx` 对代码预览和文本预览启用二级懒加载

## 优化后（2026-04-27 本地实测）

- `assets/index-CwA3IHQ5.js`：`228.50 kB`
- `assets/ExperimentPage-Cj2k0ipT.js`：`173.96 kB`
- `assets/AssetDetailPage-CdWF0-pd.js`：`7.42 kB`
- `assets/CodeArchivePreview-Dp0_DInQ.js`：`898.22 kB`
- `assets/echarts-vendor-CvUoHKeA.js`：`1,049.17 kB`
- `assets/antd-vendor-VDbj6N9j.js`：`1,113.01 kB`
- 构建状态：通过，仍有 chunk size warning

## 结果解读

- 主入口包已经明显下降，不再把多个页面统一压进首包。
- `AssetDetailPage` 自身已明显变轻，重的代码预览链路被转移到独立 chunk。
- 当前 warning 主要仍来自：
  - `antd-vendor`
  - `echarts-vendor`
  - `CodeArchivePreview`（其下包含 `JSZip`、`CodeMirror` 相关能力）

## 当前结论

- `ISSUE-P2-01` 已落地并产生明显效果。
- `ISSUE-P2-02` 已对资产预览重模块完成一轮拆分。
- 后续若要继续压 warning，优先方向应放在：
  - 进一步审查 `CodeArchivePreview` / `CodeTextViewer` 的语言包与编辑器能力拆分
  - 评估 `echarts` 使用面是否还能按图表类型或页面再拆
  - 评估 `antd` 是否存在可下沉到页面级的重依赖
