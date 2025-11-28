# Runicorn

[English](README.md) | **简体中文**

[![PyPI version](https://img.shields.io/pypi/v/runicorn)](https://pypi.org/project/runicorn/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
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
| 📦 **模型版本控制** | Git 风格的 Artifacts，智能去重 |
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

run = rn.init(project="my_project", name="exp_1")

for epoch in range(100):
    loss = train_one_epoch()
    run.log({"loss": loss, "epoch": epoch})

run.finish()
```

---

## 📦 模型版本控制

```python
# 保存
artifact = rn.Artifact("my-model", type="model")
artifact.add_file("model.pth")
run.log_artifact(artifact)  # → v1, v2, v3...

# 加载
artifact = run.use_artifact("my-model:latest")
model_path = artifact.download()
```

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

## 🆕 v0.5.3（最新）

- ⚡ **LTTB 降采样** — 高效处理 10万+ 数据点
- 💾 **增量缓存** — 解析速度提升 300 倍
- 🚀 **懒加载** — 更快的页面加载
- 🎯 **统一图表** — 单组件支持所有场景

---

## 许可证

MIT — 详见 [LICENSE](LICENSE)

---

**版本**: v0.5.3 | **更新日期**: 2025-11-28
