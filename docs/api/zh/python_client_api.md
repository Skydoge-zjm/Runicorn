[English](../en/python_client_api.md) | [简体中文](python_client_api.md)

---

# Python API Client - 程序化访问

**模块**: Python API Client
**包路径**: `runicorn.client`
**工具模块**: `runicorn.client.utils`
**版本**: v0.7.2
**最后更新**: 2026-03-28
**说明**: 通过 Python 代码访问 Runicorn Viewer REST API。

---

## 概览

当前 Python client 暴露在 `runicorn.client`，不再使用旧的 `runicorn.api` 路径。

它适合做这些事情：

- 查询 run 和路径层级
- 拉取指标数据做分析
- 导出 CSV / report
- 控制 Remote Viewer 会话
- 把 API 返回值转换成 pandas DataFrame

`connect()` 在创建 client 时会先校验 `GET /api/health`，因此连接错误会尽早暴露。

---

## 安装

Python client 随主包一起发布：

```bash
pip install runicorn
```

如果你需要 DataFrame 工具，请单独安装 pandas：

```bash
pip install pandas
```

---

## 快速开始

```python
import runicorn.client as client_mod

with client_mod.connect("http://127.0.0.1:23300") as client:
    runs = client.list_runs_by_path(path="vision", exact=False)
    print(f"匹配到 {len(runs)} 个 run")

    if runs:
        metrics = client.get_metrics(runs[0]["id"], downsample=500)
        print(metrics["columns"])
        print(metrics["rows"][:2])
```

---

## 核心 Client

### `connect()`

```python
import runicorn.client as client_mod

client = client_mod.connect(
    base_url="http://127.0.0.1:23300",
    timeout=30,
    max_retries=3,
)
```

返回 `RunicornClient` 实例。

### `RunicornClient`

也可以直接构造：

```python
from runicorn.client import RunicornClient

client = RunicornClient(
    base_url="http://127.0.0.1:23300",
    timeout=30,
    max_retries=3,
)
```

它支持上下文管理器：

```python
import runicorn.client as client_mod

with client_mod.connect() as client:
    health = client.health_check()
    print(health["status"])
```

---

## 实验管理

Viewer UI 和 Python client 现在统一使用 **run** 术语。旧文档里如果还写 experiment，那是历史表述；当前公开方法如下。

### `list_runs()`

```python
runs = client.list_runs()
```

返回 run 列表，常见字段包括 `id`、`path`、`alias`、`status`。

### `get_run(run_id)`

```python
run = client.get_run("20260328_120000_abcd12")
print(run["path"], run["status"])
```

### `list_paths(include_stats=False)`

```python
path_info = client.list_paths(include_stats=True)
print(path_info.keys())
```

返回 `/api/paths` 的路径列表 / 树结构结果。

### `list_runs_by_path(path=None, exact=False)`

这就是当前用来替代旧 `list_experiments(project=..., name=...)` 用法的接口。

```python
vision_runs = client.list_runs_by_path(path="vision", exact=False)
baseline_runs = client.list_runs_by_path(path="vision/baseline", exact=True)
```

---

## 指标数据

### `get_metrics(run_id, downsample=None)`

```python
metrics = client.get_metrics("20260328_120000_abcd12", downsample=1000)
```

返回结构是：

```python
{
    "columns": ["global_step", "loss", "acc"],
    "rows": [
        {"global_step": 1, "loss": 0.8, "acc": 0.52},
        {"global_step": 2, "loss": 0.6, "acc": 0.61},
    ],
    ...
}
```

请使用 `metrics["columns"]` 和 `metrics["rows"]`，不要再按旧文档假设存在 `metrics["metrics"]` 结构。

### `export_csv(run_id)`

```python
csv_bytes = client.export_csv("20260328_120000_abcd12")
```

### `export_report(run_id, format="markdown")`

```python
report_bytes = client.export_report("20260328_120000_abcd12", format="html")
```

当前 `format` 支持 `"markdown"` 和 `"html"`。

---

## 配置与健康检查

### `get_config()`

```python
config = client.get_config()
```

### `set_user_root_dir(path)`

```python
updated = client.set_user_root_dir(r"E:\runs")
```

### `get_gpu_info()`

```python
gpu = client.get_gpu_info()
```

### `health_check()`

```python
health = client.health_check()
```

### `get_storage_stats()`

```python
stats = client.get_storage_stats()
```

### `check_status()`

```python
result = client.check_status()
```

---

## Remote API

Remote Viewer 相关能力挂在 `client.remote` 下：

```python
import runicorn.client as client_mod

with client_mod.connect() as client:
    client.remote.connect(
        host="gpu-server",
        port=22,
        username="alice",
        private_key_path="C:/Users/alice/.ssh/id_ed25519",
    )

    session = client.remote.start_viewer(
        host="gpu-server",
        port=22,
        username="alice",
        remote_root="/data/runicorn",
        conda_env="runicorn_dev",
    )

    print(session)
```

当前可用的方法：

- `client.remote.connect(...)`
- `client.remote.disconnect(host, port=22, username=...)`
- `client.remote.list_sessions()`
- `client.remote.start_viewer(...)`
- `client.remote.stop_viewer(session_id)`
- `client.remote.list_viewer_sessions()`
- `client.remote.list_remote_storage_candidates(connection_id, conda_env="system", scan_root=None, max_depth=3)`
- `client.remote.get_remote_status()`
- `client.remote.confirm_host_key(...)`

注意：

- `start_viewer()` 当前期望显式传入 `host`、`port`、`username`、`remote_root`。
- `connection_id="user@host:port"` 仍保留向后兼容，但推荐新调用方直接传 SSH 参数。
- 如果服务端要求确认 host key，请先捕获 `HostKeyConfirmationRequiredError`，调用 `confirm_host_key(...)`，然后重试原操作。

---

## 工具函数

工具函数位于 `runicorn.client.utils`：

```python
import runicorn.client as client_mod
import runicorn.client.utils as client_utils

with client_mod.connect() as client:
    runs = client.list_runs()
    runs_df = client_utils.runs_to_dataframe(runs)

    if runs:
        metrics = client.get_metrics(runs[0]["id"])
        metrics_df = client_utils.metrics_to_dataframe(metrics)
```

当前工具函数包括：

- `metrics_to_dataframe(metrics_data)`
- `runs_to_dataframe(runs)`
- `export_metrics_to_csv(client, run_id, output_path)`
- `compare_runs(client, run_ids, metric_name)`

向后兼容说明：

- `experiments_to_dataframe` 仍然存在，但它只是 `runs_to_dataframe` 的别名。

---

## 错误处理

包里导出了这些常用异常：

```python
from runicorn.client import (
    ConnectionError,
    NotFoundError,
    BadRequestError,
    ServerError,
    HostKeyConfirmationRequiredError,
)
```

示例：

```python
import runicorn.client as client_mod
from runicorn.client import ConnectionError, NotFoundError

try:
    with client_mod.connect() as client:
        run = client.get_run("missing-run")
except NotFoundError:
    print("Run 不存在")
except ConnectionError as exc:
    print(f"Viewer 不可用: {exc}")
```

---

## 备注

- 请使用 `runicorn.client`，不要再使用已经移除的 `runicorn.api` 路径。
- 请使用 `list_runs_by_path(...)` 做路径过滤，而不是旧的 `project` / `name` 过滤参数。
- 指标返回值按 `{columns, rows}` 结构处理，需要 DataFrame 时用 `runicorn.client.utils` 转换。
