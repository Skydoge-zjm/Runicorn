[English](../en/logging_api.md) | [简体中文](logging_api.md)

---

# 增强日志 API 参考文档

> **版本**: v0.7.1
> **最后更新**: 2026-03-28
> **模块**: `runicorn.console`, `runicorn.log_compat`

---

## 📖 目录

- [概述](#概述)
- [SDK 参数](#sdk-参数)
- [日志处理器](#日志处理器)
- [MetricLogger 兼容层](#metriclogger-兼容层)
- [日志文件格式](#日志文件格式)
- [示例](#示例)
- [故障排除](#故障排除)

---

## 概述

Runicorn 当前提供增强日志系统，提供以下功能：

- **控制台捕获**: 自动捕获 `stdout`/`stderr` 到日志文件
- **Python Logging 集成**: 标准 `logging.Handler` 无缝集成
- **MetricLogger 兼容**: torchvision MetricLogger 的直接替代品
- **智能 tqdm 处理**: 智能过滤进度条输出

### 核心组件

| 组件 | 模块 | 描述 |
|------|------|------|
| `ConsoleCapture` | `runicorn.console` | 捕获 stdout/stderr 到日志文件 |
| `RunicornLoggingHandler` | `runicorn.console` | Python logging 处理器 |
| `LogManager` | `runicorn.console` | 线程安全的日志文件管理器 |
| `MetricLogger` | `runicorn.log_compat.torchvision` | torchvision 兼容的日志记录器 |

---

## SDK 参数

### `runicorn.init()` 日志参数

```python
import runicorn

run = runicorn.init(
    path="my/experiment",
    capture_console=True,    # 启用控制台捕获
    tqdm_mode="smart",       # tqdm 处理模式
)
```

#### `capture_console: bool = False`

启用后，将所有 `stdout` 和 `stderr` 输出捕获到运行的 `logs.txt` 文件。

**特性**:
- 输出同时发送到终端和日志文件（tee 行为）
- 通过 `LogManager` 实现线程安全写入
- 立即刷新以支持实时 WebSocket 流
- 捕获失败时优雅降级

**示例**:
```python
import runicorn

run = runicorn.init(path="training/resnet", capture_console=True)

# 所有 print 语句都会被捕获
print("开始训练...")  # 同时输出到终端和 logs.txt
print(f"Epoch 1/100")

run.finish()
```

#### `tqdm_mode: str = "smart"`

控制控制台捕获期间如何处理 tqdm 进度条。

| 模式 | 行为 |
|------|------|
| `"smart"` | 仅捕获 tqdm 最终输出，过滤中间更新 |
| `"all"` | 捕获所有 tqdm 输出（可能产生冗长日志） |
| `"none"` | 从日志中过滤所有 tqdm 输出 |

**示例**:
```python
from tqdm import tqdm
import runicorn

# Smart 模式（默认）：仅捕获最终进度
run = runicorn.init(path="exp", capture_console=True, tqdm_mode="smart")

for i in tqdm(range(100)):
    pass  # 进度条更新被过滤，最终行被捕获

run.finish()
```

---

## 日志处理器

### `run.get_logging_handler()`

返回一个 Python `logging.Handler`，将日志记录写入运行的日志文件。

```python
def get_logging_handler(
    self,
    level: int = logging.INFO,
    fmt: Optional[str] = None,
) -> RunicornLoggingHandler
```

#### 参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `level` | `int` | `logging.INFO` | 捕获的最低日志级别 |
| `fmt` | `str \| None` | `None` | 自定义格式字符串（None 时使用默认格式） |

#### 默认格式

```
%(asctime)s | %(levelname)s | %(name)s | %(message)s
```

使用 `datefmt='%H:%M:%S'`，产生如下输出：
```
14:30:45 | INFO | my_module | 训练开始
```

#### 使用示例

```python
import logging
import runicorn

# 初始化运行
run = runicorn.init(path="training/bert", capture_console=True)

# 获取 logger 并添加 Runicorn 处理器
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(run.get_logging_handler(level=logging.DEBUG))

# 日志消息写入 logs.txt
logger.info("模型已初始化")
logger.debug("批次大小: 32")
logger.warning("GPU 内存不足")

run.finish()
```

#### 自定义格式

```python
handler = run.get_logging_handler(
    level=logging.INFO,
    fmt="[%(levelname)s] %(message)s"
)
logger.addHandler(handler)

logger.info("自定义格式")  # 输出: [INFO] 自定义格式
```

### `RunicornLoggingHandler` 类

对于高级用例，可以直接实例化处理器：

```python
from runicorn.console import RunicornLoggingHandler

# 使用显式 run
handler = RunicornLoggingHandler(run=my_run, level=logging.DEBUG)

# 不使用 run（如果可用则使用活动 run）
handler = RunicornLoggingHandler()
```

#### 特性

- **线程安全**: 使用 `LogManager` 进行并发写入
- **延迟初始化**: 即使没有活动 Run 也能工作
- **自动清理**: 关闭时正确释放资源

---

## MetricLogger 兼容层

### 概述

`MetricLogger` 提供了 torchvision `MetricLogger` 类的直接替代品，并自动集成 Runicorn。

```python
# 替换这个:
# from torchvision.references.detection.utils import MetricLogger

# 为这个:
from runicorn.log_compat.torchvision import MetricLogger
```

### 基本用法

```python
from runicorn.log_compat.torchvision import MetricLogger
import runicorn

run = runicorn.init(path="detection/yolo")

metric_logger = MetricLogger(delimiter="  ")

for epoch in range(10):
    for batch in metric_logger.log_every(dataloader, print_freq=10, header=f"Epoch {epoch}"):
        loss = model(batch)

        # 指标自动记录到 Runicorn
        metric_logger.update(loss=loss.item(), lr=optimizer.param_groups[0]['lr'])

run.finish()
```

### API 参考

#### `MetricLogger(delimiter: str = "\t")`

创建新的 MetricLogger 实例。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `delimiter` | `str` | `"\t"` | 字符串输出中指标之间的分隔符 |

#### `MetricLogger.update(**kwargs)`

更新指标并自动记录到 Runicorn。

```python
metric_logger.update(
    loss=0.5,
    accuracy=0.95,
    lr=0.001
)
```

**支持的值类型**:
- `float`
- `int`
- `torch.Tensor`（自动调用 `.item()`）

#### `MetricLogger.log_every(iterable, print_freq, header=None)`

生成器，产出项目并打印进度。

```python
for data in metric_logger.log_every(dataloader, 10, header="Train"):
    # 处理数据
    pass
```

**输出格式**:
```
Train [  0/100]  eta: 0:05:00  loss: 0.5000 (0.5000)  time: 0.3000  data: 0.1000
Train [ 10/100]  eta: 0:04:30  loss: 0.4500 (0.4750)  time: 0.2800  data: 0.0900
...
Train Total time: 0:05:00 (0.3000 s / it)
```

#### `MetricLogger.synchronize_between_processes()`

在分布式训练进程之间同步指标。

```python
# 分布式训练中每个 epoch 后
metric_logger.synchronize_between_processes()
```

### SmoothedValue 类

`SmoothedValue` 跟踪一系列值并提供平滑：

```python
from runicorn.log_compat.torchvision import SmoothedValue

sv = SmoothedValue(window_size=20, fmt="{median:.4f} ({global_avg:.4f})")
sv.update(0.5)
sv.update(0.4)

print(sv.median)      # 最近 20 个值的中位数
print(sv.avg)         # 最近 20 个值的平均值
print(sv.global_avg)  # 全局平均值
print(sv.max)         # 窗口内的最大值
print(sv.value)       # 最近的值
```

---

## 日志文件格式

### 位置

日志文件存储在：
```
<storage_root>/runs/<path>/<run_id>/logs.txt
```

### 格式

带时间戳的纯文本：
```
14:30:45 | 开始训练...
14:30:46 | Epoch 1/100
14:30:47 | INFO | trainer | Batch 0: loss=0.5432
14:31:00 | Epoch 1 完成: loss=0.4321, accuracy=0.8765
```

### 实时流

日志文件支持通过 WebSocket 实时流：
```
WS ws://127.0.0.1:23300/api/runs/{run_id}/logs/ws
```

`LogManager` 确保每次写入后立即刷新以支持实时更新。

---

## 示例

### 完整训练脚本

```python
import logging
import runicorn
from runicorn.log_compat.torchvision import MetricLogger
from tqdm import tqdm

# 使用控制台捕获初始化
run = runicorn.init(
    path="vision/resnet50",
    capture_console=True,
    tqdm_mode="smart"
)

# 设置 Python logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(run.get_logging_handler())

# 使用 MetricLogger 的训练循环
metric_logger = MetricLogger(delimiter="  ")

logger.info("开始训练")
print(f"配置: epochs=100, batch_size=32")

for epoch in range(100):
    for batch in metric_logger.log_every(train_loader, 50, header=f"Epoch {epoch}"):
        loss = train_step(batch)
        metric_logger.update(loss=loss)

    # 验证
    val_loss, val_acc = validate(model, val_loader)
    logger.info(f"Epoch {epoch}: val_loss={val_loss:.4f}, val_acc={val_acc:.4f}")

    # 记录到 Runicorn 指标
    run.log({"val_loss": val_loss, "val_acc": val_acc}, step=epoch)

logger.info("训练完成")
run.finish()
```

### 从 torchvision 迁移

**之前**（torchvision）:
```python
from torchvision.references.detection.utils import MetricLogger, SmoothedValue

metric_logger = MetricLogger(delimiter="  ")
for data in metric_logger.log_every(loader, 10):
    loss = model(data)
    metric_logger.update(loss=loss.item())
```

**之后**（Runicorn）:
```python
from runicorn.log_compat.torchvision import MetricLogger, SmoothedValue
import runicorn

run = runicorn.init(path="detection/exp1")

metric_logger = MetricLogger(delimiter="  ")
for data in metric_logger.log_every(loader, 10):
    loss = model(data)
    metric_logger.update(loss=loss.item())  # 自动记录到 Runicorn！

run.finish()
```

### 多个 Logger

```python
import logging
import runicorn

run = runicorn.init(path="exp", capture_console=True)

# 不同模块使用不同的 logger
train_logger = logging.getLogger("trainer")
eval_logger = logging.getLogger("evaluator")

# 都使用相同的 Runicorn 处理器
handler = run.get_logging_handler()
train_logger.addHandler(handler)
eval_logger.addHandler(handler)

train_logger.info("训练开始")
eval_logger.info("评估开始")

run.finish()
```

---

## 故障排除

### 控制台捕获不工作

**症状**: `print()` 输出未出现在 `logs.txt` 中

**解决方案**:
1. 确保在 `runicorn.init()` 中设置了 `capture_console=True`
2. 检查初始化期间的错误（警告会被记录）
3. 验证运行目录存在且可写

### tqdm 输出过于冗长

**症状**: 日志文件充满进度条更新

**解决方案**: 使用 `tqdm_mode="smart"` 或 `tqdm_mode="none"`:
```python
run = runicorn.init(path="exp", capture_console=True, tqdm_mode="none")
```

### 日志处理器未捕获

**症状**: `logger.info()` 未出现在日志中

**解决方案**:
1. 确保添加了处理器: `logger.addHandler(run.get_logging_handler())`
2. 检查 logger 级别: `logger.setLevel(logging.DEBUG)`
3. 检查处理器级别是否匹配您的日志级别

### MetricLogger 未记录到 Runicorn

**症状**: 指标未出现在 Runicorn UI 中

**解决方案**:
1. 确保在创建 MetricLogger 之前调用了 `runicorn.init()`
2. 验证存在活动运行: `runicorn.get_active_run()` 应返回 Run
3. 检查值是否为数值类型（float/int/Tensor）

---

## 相关文档

- **[Runs API](./runs_api.md)** - 实验管理
- **[Metrics API](./metrics_api.md)** - 指标和实时日志
- **[快速参考](./QUICK_REFERENCE.md)** - API 快速参考

---

**作者**: Runicorn Development Team
**版本**: v0.7.1
**最后更新**: 2026-03-28

**[返回 API 索引](API_INDEX.md)**
