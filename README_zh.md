# Runicorn

[English](README.md) | **简体中文**

[![PyPI version](https://img.shields.io/pypi/v/runicorn)](https://pypi.org/project/runicorn/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<p align="center">
  <img src="docs/assets/icon.jpg" alt="Runicorn logo" width="300" />
</p>

**本地、开源的 ML 实验追踪工具。** 100% 离线，零遥测。现代化的 W&B 自托管替代方案。

---

## ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🏠 **100% 本地** | 数据永远不离开你的机器 |
| 📊 **实时可视化** | 实时指标、日志和 GPU 监控 |
| 📦 **资产与快照** | 工作区快照，以及数据集/配置/预训练模型引用 |
| 🌐 **Remote Viewer** | 通过 SSH 访问远程 GPU 服务器（类似 VSCode Remote） |
| 🖥️ **桌面应用** | Windows 原生应用，自动后端 |

<table>
  <tr>
    <td><img src="docs/assets/p1.png" alt="实验列表" width="100%" /></td>
    <td><img src="docs/assets/p2.png" alt="实验详情" width="100%" /></td>
  </tr>
</table>

---

## 🚀 快速开始

```bash
pip install runicorn
runicorn viewer  # 打开 http://127.0.0.1:23300
```

```python
import runicorn as rn

run = rn.init(path="my_project/exp_1", alias="baseline")

for epoch in range(100):
    loss = train_one_epoch()
    run.log({"loss": loss}, step=epoch + 1)

run.finish()
```

---

## 🎯 适合谁 / 不适合谁

**适合**

- 训练主要发生在本地或自有服务器，希望避免 SaaS 绑定
- 希望把指标、日志、资产和代码上下文放在同一个实验视图里
- 经常在本地工作站和远程 GPU 机器之间切换

**不适合**

- 你需要开箱即用的托管协作平台、团队权限或云端仪表盘
- 你只需要最简单的 CSV 日志，不关心后续浏览和回看实验
- 你的工作流本来就依赖托管在线生态，而不是本地或自控基础设施

---

## ✅ 推荐工作流

1. 在训练入口接入 `runicorn.init(...)`，训练过程中持续记录指标
2. 本地打开 `runicorn viewer` 查看实验、对比指标、检查日志和资产
3. 对重要实验补充配置、数据集、预训练输入的快照或引用
4. 如果训练跑在远程 GPU 服务器上，直接用 `Remote` 页面查看，不先走手工拷文件回本地的流程

---

## 🔍 它比手工流程好在哪里

| 工作方式 | 常见问题 | Runicorn |
|---|---|---|
| 手工维护本地目录和脚本 | 指标、日志、配置、输出容易散开 | 把实验历史、summary、日志和资产绑定到同一个 run |
| SSH 登录远程机器 + tail 日志 + 临时画图 | 查看慢、对比难、上下文容易丢 | Remote Viewer 通过 SSH 提供结构化界面，不要求先同步 |
| 托管式实验追踪平台 | 需要依赖外网、服务方和外部存储 | 保持本地、离线、数据边界可控 |

---

## 📦 资产与工作区快照

```python
from pathlib import Path

snapshot = rn.snapshot_workspace(Path.cwd(), Path("workspace_snapshot.zip"))

print(snapshot["archive_path"])
print(snapshot["file_count"])
```

在 run 内可以使用 `run.log_config(...)`、`run.log_dataset(...)` 和 `run.log_pretrained(...)` 记录可复用的训练上下文；旧的 `Artifact` API 已不再公开。

---

## 🌐 Remote Viewer

无需文件同步，直接访问远程 GPU 服务器：

```bash
runicorn viewer  # → 点击 "Remote" → 输入 SSH 信息 → 完成！
```

| | 旧版同步 (v0.4) | Remote Viewer (v0.5+) |
|---|---|---|
| **等待时间** | 分钟~小时 | 秒级 |
| **本地存储** | 需要 | 零占用 |
| **实时性** | ❌ | ✅ |

---

## 📚 文档

| 资源 | 链接 |
|------|------|
| 用户指南 | [docs/user-guide/](docs/user-guide/) |
| API 参考 | [docs/api/](docs/api/) |
| 更新日志 | [CHANGELOG.md](CHANGELOG.md) |

---

## 🆕 v0.7.0（最新）

- 🌐 **Remote Viewer 强化** — 保存连接、健康监控、重连状态与 OpenSSH 密码支持
- 🎨 **Web UI 产品化改进** — 更清晰的导航、更顺手的对比流程、ZIP 导入导出预览与统一回收站
- 📈 **日志与监控** — 虚拟滚动日志、更一致的暗色模式、后端采集的 GPU 遥测历史
- 🔌 **日志兼容增强** — 更好支持 ImageNet meters、TensorBoard 与 tensorboardX
- 🖥️ **桌面端改进** — 当前桌面工作流支持原生远程会话窗口

---

## 许可证

MIT — 详见 [LICENSE](LICENSE)

---

**版本**: v0.7.0 | **更新日期**: 2026-04-27
