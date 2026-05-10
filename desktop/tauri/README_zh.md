[English](README.md) | [简体中文](README_zh.md)

# Runicorn Desktop (Tauri)

本目录包含 Runicorn Viewer 的桌面封装。本文档面向开发者，重点说明 Windows 下的 Tauri 打包、构建脚本分工、配置入口和当前验证边界，不是面向最终用户的使用说明。

当前桌面端由两个主要构建面组成：

- `web/frontend` 产出的前端 bundle
- `desktop/tauri/sidecar` 下打包出来的 Python sidecar

Rust/Tauri 外壳负责加载前端静态产物，并拉起 sidecar 可执行文件。

## 前置条件（Windows）

以下依赖通常只需安装一次：

1. Rust 工具链（`rustup`）

```powershell
winget install --id Rustlang.Rustup -e
```

2. 带 Windows SDK 的 MSVC Build Tools

```powershell
winget install --id Microsoft.VisualStudio.2022.BuildTools -e
```

在安装器中勾选 `Desktop development with C++`。

3. WebView2 Runtime

```powershell
winget install --id Microsoft.EdgeWebView2Runtime -e
```

4. Node.js LTS

```powershell
winget install OpenJS.NodeJS.LTS -e
```

5. Tauri CLI

```powershell
cargo install tauri-cli
```

6. 一个可用于 sidecar 构建的 Python 解释器

当前本地构建脚本会从配置中读取 Python 路径。在本仓库里，Python 相关测试/构建约定使用 `runicorn_dev` 这个 Conda 环境。

## 构建配置

Desktop 构建参数现在统一走配置文件。

- 共享默认配置：`desktop/tauri/build_config.json`
- 个人机器覆盖配置：`desktop/tauri/build_config.local.json`
- 本地覆盖示例：`desktop/tauri/build_config.local.example.json`

`build_config.local.json` 已被 Git 忽略，适合放机器相关参数，例如：

- `common.pythonExe`
- `common.httpProxy`
- `common.httpsProxy`
- `common.noProxy`

几个关键约束：

- 本地覆盖会递归覆盖共享默认配置
- 桌面构建脚本会在启动时打印合并后的有效配置
- 所有桌面构建脚本都支持 `-DryRun`
- 非本地 sidecar 构建没有默认包版本；如果 `sidecar.useLocal` 为 `false`，必须显式传 `-RunicornVersion`

主要配置段：

- `common`
  - 进程级公共设置，例如 Python 路径和代理
- `sidecar`
  - sidecar 构建模式与运行时探针设置
- `sidecar.pyInstaller`
  - PyInstaller 收集规则和 DLL 注入规则
- `release`
  - 桌面打包默认项，例如 `bundles` 和 `skipFrontend`

## 脚本分工

### `build_release_clean.ps1`

这是当前推荐的 desktop 主构建入口。

当你不确定前端、sidecar 或 Tauri 壳哪一层受到影响，或者前后端都有改动时，用这个脚本。

它会：

- 停掉残留的 desktop/sidecar 进程
- 重建前端 bundle
- 重建 sidecar 可执行文件
- 执行 `cargo tauri build`

常用命令：

```powershell
./desktop/tauri/build_release_clean.ps1
```

只看本次解析出的参数、不真正执行：

```powershell
./desktop/tauri/build_release_clean.ps1 -DryRun
```

### `build_release.ps1`

这是常规 desktop release 构建入口。

它和 `build_release_clean.ps1` 接近，但更适合你已经明确知道前端产物状态时使用。若不确定当前工作区状态，优先用 `build_release_clean.ps1`。

### `sidecar/build_sidecar.ps1`

这是 sidecar 单独构建入口。

它会：

- 准备或刷新 sidecar 虚拟环境
- 安装 sidecar 依赖
- 用 PyInstaller 构建 `runicorn-viewer.exe`
- 从所选 Python 基础环境补齐所需运行时 DLL
- 生成 Tauri 所需的带 target triple 后缀的 sidecar 可执行文件
- 对 `/api/health` 执行运行时健康探针

适合以下场景：

- 只改了 Python viewer / backend 打包链
- 只想单独验证 sidecar
- 正在排查 sidecar 构建或运行时失败

常用命令：

```powershell
./desktop/tauri/sidecar/build_sidecar.ps1
```

非本地包构建示例：

```powershell
./desktop/tauri/sidecar/build_sidecar.ps1 -RunicornVersion 0.7.1
```

### `build_config.ps1`

这是构建辅助层，不是直接执行入口。

它负责：

- 读取并合并配置
- 在当前进程作用域设置代理环境变量
- 提供配置打印和 `DryRun` 输出辅助函数

## 推荐工作流

### 前端和 desktop 都改了

用：

```powershell
./desktop/tauri/build_release_clean.ps1
```

### 只改了 sidecar 路径

用：

```powershell
./desktop/tauri/sidecar/build_sidecar.ps1
```

### 只想检查本次会吃到什么配置

用：

```powershell
./desktop/tauri/build_release_clean.ps1 -DryRun
```

## 当前构建产物

当前本地 Windows 打包默认通过 desktop 配置走 `nsis`。

成功的 release 产物通常位于：

- `desktop/tauri/src-tauri/target/release/runicorn-desktop.exe`
- `desktop/tauri/src-tauri/target/release/bundle/nsis/Runicorn Desktop_<version>_x64-setup.exe`

成功的 sidecar 产物通常位于：

- `desktop/tauri/sidecar/dist/runicorn-viewer.exe`
- `desktop/tauri/sidecar/dist/runicorn-viewer-<target-triple>.exe`

## CI 验证边界

仓库把 desktop 验证视为独立于主 CI 的一个自动化面。

- 主 CI 继续跑 Python / frontend 检查以及 frontend mocked browser smoke
- 当前 Python CI 仍然依赖默认的 `pytest -q`，其中包含现有 integration 标记测试
- desktop 验证位于 `.github/workflows/desktop-build.yml`

当前 desktop workflow 的验证范围比完整安装包构建更窄，主要做：

- 构建前端静态资源
- 执行 `desktop/tauri/sidecar/build_sidecar.ps1`
- 在 `desktop/tauri/src-tauri` 下执行 `cargo check`

当前要明确的限制：

- CI 目前验证了 sidecar 打包与运行时健康探针，也验证了 Rust 编译面
- CI 目前不会在每次运行时都构建完整 Windows 安装包

## 开发注意事项

- 当需要同时保证前端、sidecar 和 Tauri 打包链一致时，应把这些 PowerShell 脚本视为标准入口，不要把裸 `cargo tauri build` 当成顶层规范流程。
- 仓库中跟踪的 `runicorn-viewer.spec` 故意保持为通用模板。sidecar 构建脚本会在打包时生成临时 spec，避免把本机 DLL 绝对路径写回仓库。
- 如果某台机器需要特殊代理或非默认 Python 解释器，应写入 `build_config.local.json`，不要直接改跟踪中的脚本。
