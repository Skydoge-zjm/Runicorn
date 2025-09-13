# Runicorn

[![PyPI version](https://img.shields.io/pypi/v/runicorn)](https://pypi.org/project/runicorn/)
[![Python Versions](https://img.shields.io/pypi/pyversions/runicorn)](https://pypi.org/project/runicorn/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README.md) | **简体中文**


<p align="center">
  <img src="docs/picture/icon.jpg" alt="Runicorn logo" width="360" />
</p>

本地、开源的实验追踪与可视化工具，100% 离线。轻量、零侵入，是 W&B 的自托管替代方案。

- 包名称：`runicorn`
- 默认存储根：用户级目录（可配置），否则回退到项目目录下的 `./.runicorn`
- 查看器：只读（Read-only），从本地存储读取指标、日志、媒体
- GPU 面板：如果系统存在 `nvidia-smi` 则可显示
- 远程 SSH 实时同步：将 Linux 服务器上的运行镜像到本地存储

<p align="center">
  <img src="https://github.com/Skydoge-zjm/Runicorn/blob/main/docs/picture/p1.png" alt="Runicorn 界面示例 1" width="49%" />
  <img src="https://github.com/Skydoge-zjm/Runicorn/blob/main/docs/picture/p2.png" alt="Runicorn 界面示例 2" width="49%" />
  <br/>
  <img src="https://github.com/Skydoge-zjm/Runicorn/blob/main/docs/picture/p3.png" alt="Runicorn 界面示例 3" width="49%" />
  <img src="https://github.com/Skydoge-zjm/Runicorn/blob/main/docs/picture/p4.png" alt="Runicorn 界面示例 4" width="49%" />
  <br/>
  <img src="https://github.com/Skydoge-zjm/Runicorn/blob/main/docs/picture/p5.png" alt="Runicorn demo 5" width="98%" />
  <br/>
  <span style="color:#888; font-size: 12px;">界面示意：运行列表、运行详情、指标叠加、GPU 面板</span>
</p>

## 0.2.0 有哪些更新

- 新增“用户级根目录 + 项目/实验”层级组织：`user_root_dir/<project>/<name>/runs/<run_id>/...`
- 新增 CLI：`runicorn config`，用于设置与查看全局的 `user_root_dir`
- 前端：
  - 运行列表页新增 Project/Name 筛选
  - 运行详情页支持“同一实验的多次运行叠加显示”（多条曲线同图比较）
- 后端：
  - 新增层级发现 API：`/api/projects`、`/api/projects/{project}/names`、`/api/projects/{project}/names/{name}/runs`
  - 兼容旧版目录结构（`./.runicorn/runs/<run_id>`）

## 特性

- 100% 本地，数据只存储在你的机器上
- 只读 Viewer（FastAPI），对训练过程零侵入
- UI 资源打包进 wheel，安装后可离线使用
- 支持“步/时间”双横轴、阶段分隔线（stage）、实时日志（WebSocket）
- 可选 GPU 面板（依赖 `nvidia-smi`）
- 用户级根目录 + 项目/实验层级组织
- 同一实验下的多运行叠加展示（对比不同 run 的同一指标）

## 安装

需要 Python 3.8+（Windows/Linux）。桌面应用目前仅 Windows 可用；CLI/Viewer 在 Windows 与 Linux 均可运行。

```bash
pip install -U runicorn
# 可选：图像相关（Pillow, NumPy, Matplotlib）
pip install -U "runicorn[images]"
```

## 快速开始

```python
import runicorn as rn
import math, random

# 指定项目与实验名；默认写入用户级根目录
run = rn.init(project="demo", name="exp1")

stages = ["warmup", "train"]
for i in range(1, 101):
    stage = stages[min((i - 1) // 50, len(stages) - 1)]
    loss = max(0.02, 2.0 * math.exp(-0.02 * i) + random.uniform(-0.02, 0.02))
    rn.log({"loss": round(loss, 4)}, stage=stage)

rn.summary({"best_val_acc_top1": 77.3})
rn.finish()
```

可选：显式覆盖存储根目录
```python
run = rn.init(project="demo", name="exp1", storage="E:\\RunicornData")
```

## 查看器（Viewer）

启动本地只读查看器并打开 UI：
```bash
runicorn viewer
# 或自定义参数
runicorn viewer --storage ./.runicorn --host 127.0.0.1 --port 8000
# 打开 http://127.0.0.1:8000
```

提示：如果要在 UI 中使用“离线导入”（上传 `.zip` 或 `.tar.gz`），需要安装可选依赖：

```bash
pip install python-multipart
```

## 远程同步（SSH 实时）

将远程 Linux 服务器上的运行（runs）通过 SSH 实时镜像到本机 storage。

- 打开 UI 顶部导航中的「Remote」，或直接访问 `/remote`
- 操作步骤：
  1) 连接：输入 `主机`、`端口`（默认 22）、`用户名`；可选输入 `密码` 或 `私钥内容/路径`
  2) 浏览远程目录并选择正确的层级：
     - 新目录结构：选择到 `<project>/<name>/runs`
     - 旧目录结构：选择到 `runs`
     - 不要选择具体的 `<run_id>` 目录
  3) 点击「同步此目录」。下方会出现「同步任务」，「Runs」页面会立即刷新

小贴士与排查
- 看不到运行时，请确认：
  - 同步任务是否存在：GET `/api/ssh/mirror/list` 应显示 `alive: true`，统计项递增
  - 本地存储根是否正确：GET `/api/config` 查看 `storage` 路径；检查是否按预期层级生成
  - 选择的层级是否为 `.../runs`（而不是某个具体 `<run_id>` 目录）
  - 凭据仅用于本次会话，不会持久化；SSH 由 Paramiko 负责

## 桌面应用（Windows）

- 推荐普通用户通过 GitHub Releases 安装，或在本地自行构建安装包。
- 构建前置依赖：Node.js 18+；Rust & Cargo（稳定版）；Python 3.8+；NSIS（用于打包安装器）
- 本地构建（生成 NSIS 安装器）：

  ```powershell
  # 在仓库根目录执行
  powershell -ExecutionPolicy Bypass -File .\desktop\tauri\build_release.ps1 -Bundles nsis
  # 安装包输出路径：
  # desktop/tauri/src-tauri/target/release/bundle/nsis/Runicorn Desktop_<version>_x64-setup.exe
  ```

- 安装后启动「Runicorn Desktop」。
  - 首次运行：右上角齿轮 → 设置 → 数据目录，选择一个可写路径（如 `D:\RunicornData`），点击保存。
  - 桌面应用会自动启动本地后端并打开 UI。

## 配置

- “用户级根目录”可通过 UI 或 CLI 设置：

  - 桌面应用 UI：右上角齿轮 → 设置 → 数据目录（写入到 `%APPDATA%\Runicorn\config.json`）。

  - 通过 CLI（全局复用）：
  ```bash
  runicorn config --set-user-root "E:\\RunicornData"
  runicorn config --show
  ```

- 存储根目录的优先级（从高到低）：
  1. `runicorn.init(storage=...)`
  2. 环境变量 `RUNICORN_DIR`
  3. 全局配置 `user_root_dir`（`runicorn config` 设置）
  4. 本地目录 `./.runicorn`

- 实时日志通过 `/api/runs/{run_id}/logs/ws` 读取 `logs.txt`（WebSocket）

## 隐私与离线

- 无遥测收集；Viewer 仅读取本地 JSON/JSONL/媒体文件
- 未设置用户级根目录时，回退到本地 `./.runicorn`
- UI 打包进 wheel，运行时不依赖 Node.js

## 存储结构

```
user_root_dir/
  <project>/
    <name>/
      runs/
        <run_id>/
          meta.json
          status.json
          summary.json
          events.jsonl
          logs.txt
          media/
```

兼容旧版目录结构：
```
./.runicorn/
  runs/
    <run_id>/
      ...
```

## 路线图（Roadmap）

- 高级筛选/搜索
- Artifact 浏览与媒体库改进
- CSV 导出与后端分页
- 可选远端存储适配（如 S3/MinIO），同时保持 Viewer 只读

## 社区

- 开发规范与提交流程：`CONTRIBUTING.md`
- 安全披露：`SECURITY.md`
- 版本历史：`CHANGELOG.md`
