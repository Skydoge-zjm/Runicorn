[English](../en/ENHANCED_LOGGING_GUIDE.md) | [简体中文](ENHANCED_LOGGING_GUIDE.md)

---

# 增强日志指南

> **版本**: v0.6.0  
> **功能**: 控制台捕获、Python Logging 集成、MetricLogger 兼容

---

## 📋 概述

Runicorn v0.6.0 引入了**增强日志系统**，可以自动捕获控制台输出，无需修改代码。该系统提供：

- **控制台捕获**: 自动捕获 `print()` 和 `sys.stderr` 输出到 `logs.txt`
- **Python Logging 集成**: 与 Python 的 `logging` 模块无缝集成
- **MetricLogger 兼容**: torchvision 风格 MetricLogger 的直接替换
- **智能 tqdm 处理**: 智能进度条过滤，防止日志膨胀

### 设计理念

增强日志系统将**文本日志**与**结构化指标**分离：

| 类型 | 用户操作 | 存储位置 | 用途 |
|------|----------|----------|------|
| 文本日志 | `print(...)` | `logs.txt` | 调试、查看 |
| 结构化指标 | `run.log({...})` | 数据库 | 绘图、比较 |

这种分离确保：
- `print()` 输出按原样捕获，不强制解析
- `run.log()` 提供显式的结构化指标记录
- 两者都有价值，服务于不同目的

---

## 🚀 快速入门

### 基本控制台捕获

只需一个参数即可启用控制台捕获：

```python
import runicorn as rn

# 启用控制台捕获
run = rn.init(path="my_experiment", capture_console=True)

# 所有 print 输出自动捕获
print("开始训练...")
print(f"Epoch 1: loss=0.5, accuracy=0.85")

# 结构化指标用于绘图
run.log({"loss": 0.5, "accuracy": 0.85})

run.finish()
```

运行后，查看运行目录中的 `logs.txt`：
```
[10:30:15] 开始训练...
[10:30:16] Epoch 1: loss=0.5, accuracy=0.85
```

### 使用 Python Logging Handler

与现有 Python logger 集成：

```python
import logging
import runicorn as rn

run = rn.init(path="my_experiment")

# 获取 Runicorn logging handler
handler = run.get_logging_handler()

# 添加到你的 logger
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# 日志消息写入 logs.txt
logger.info("模型已初始化")
logger.warning("GPU 内存不足")

run.finish()
```

### MetricLogger 直接替换

对于使用 torchvision 风格 MetricLogger 的项目，只需修改一行 import：

```python
# 之前 (torchvision 风格)
# from utils import MetricLogger

# 之后 (Runicorn 集成)
from runicorn.log_compat.torchvision import MetricLogger

import runicorn as rn

run = rn.init(path="training", capture_console=True)

metric_logger = MetricLogger(delimiter="  ")

for epoch in range(10):
    for data in metric_logger.log_every(dataloader, 10, header=f"Epoch {epoch}"):
        loss = train_step(data)
        # 自动同时记录到控制台和 run.log()
        metric_logger.update(loss=loss)

run.finish()
```

---

## 📚 功能详解

### 控制台捕获

控制台捕获使用 "Tee" 模式将 `stdout` 和 `stderr` 同时重定向到终端和日志文件。

#### 参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `capture_console` | `bool` | `False` | 启用控制台捕获 |
| `tqdm_mode` | `str` | `"smart"` | 进度条处理模式 |

#### 示例

```python
run = rn.init(
    path="experiment",
    capture_console=True,
    tqdm_mode="smart",  # "smart", "all", 或 "none"
)
```

### tqdm 处理模式

进度条（tqdm、rich.progress）使用回车符（`\r`）进行动态更新。如果不特殊处理，每次更新都会在日志文件中变成新行，导致严重膨胀。

Runicorn 提供三种模式：

| 模式 | 行为 | 使用场景 |
|------|------|----------|
| `"smart"` | 缓冲 `\r` 行，只写入最终版本 | **推荐** - 干净的日志 |
| `"all"` | 写入每次更新（将 `\r` 替换为 `\n`） | 调试进度条问题 |
| `"none"` | 忽略所有包含 `\r` 的行 | 最小化日志 |

#### Smart 模式示例

```python
from tqdm import tqdm
import runicorn as rn

run = rn.init(path="training", capture_console=True, tqdm_mode="smart")

# tqdm 进度条
for i in tqdm(range(100), desc="Training"):
    # ... 训练代码 ...
    pass

run.finish()
```

**终端输出**（动态）：
```
Training: 100%|██████████| 100/100 [00:10<00:00, 10.0it/s]
```

**logs.txt**（干净，只有最终状态）：
```
[10:30:15] Training: 100%|██████████| 100/100 [00:10<00:00, 10.0it/s]
```

### Python Logging Handler

`RunicornLoggingHandler` 是标准的 `logging.Handler`，写入 Runicorn 的日志文件。

#### 特性

- 通过 `LogManager` 实现线程安全
- 延迟初始化（即使没有活动 Run 也能工作）
- 可配置日志级别和格式
- 独立于控制台捕获工作

#### API

```python
handler = run.get_logging_handler(
    level=logging.INFO,      # 最小日志级别
    fmt="%(asctime)s | %(levelname)s | %(message)s"  # 自定义格式
)
```

#### 示例：多个 Logger

```python
import logging
import runicorn as rn

run = rn.init(path="experiment")
handler = run.get_logging_handler()

# 添加到多个 logger
for name in ["model", "data", "trainer"]:
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# 所有日志写入同一个 logs.txt
logging.getLogger("model").info("模型已加载")
logging.getLogger("data").info("数据集就绪")
logging.getLogger("trainer").info("训练开始")

run.finish()
```

### MetricLogger 兼容层

`MetricLogger` 类是 torchvision MetricLogger 的直接替换，广泛用于 CV 项目（DeiT、DETR、DINOv2、BLIP 等）。

#### 特性

- **100% API 兼容**: 所有方法行为完全相同
- **自动 Runicorn 集成**: `update()` 调用自动记录到 `run.log()`
- **纯 Python**: 有无 PyTorch 都能工作
- **分布式训练支持**: `synchronize_between_processes()` 正常工作

#### 类

| 类 | 描述 |
|----|------|
| `MetricLogger` | 主日志器，带平滑值跟踪 |
| `SmoothedValue` | 滑动窗口统计（median、avg、global_avg、max） |

#### 示例：训练循环

```python
from runicorn.log_compat.torchvision import MetricLogger
import runicorn as rn

run = rn.init(path="deit_training", capture_console=True)

metric_logger = MetricLogger(delimiter="  ")

for epoch in range(100):
    header = f"Epoch: [{epoch}]"
    
    for samples, targets in metric_logger.log_every(train_loader, 10, header):
        loss = model(samples, targets)
        
        # 这会自动：
        # 1. 更新内部 SmoothedValue
        # 2. 调用 run.log({"loss": loss_value})
        metric_logger.update(loss=loss.item())
        metric_logger.update(lr=optimizer.param_groups[0]["lr"])
    
    # 跨 GPU 同步（如果是分布式）
    metric_logger.synchronize_between_processes()

run.finish()
```

---

## 📖 API 参考

### Run 参数

```python
run = rn.init(
    path="experiment",
    capture_console=True,   # 启用控制台捕获
    tqdm_mode="smart",      # tqdm 处理模式
)
```

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `capture_console` | `bool` | `False` | 捕获 stdout/stderr 到 logs.txt |
| `tqdm_mode` | `str` | `"smart"` | 进度条处理："smart"、"all"、"none" |

### run.get_logging_handler()

```python
handler = run.get_logging_handler(
    level: int = logging.INFO,
    fmt: Optional[str] = None,
) -> logging.Handler
```

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `level` | `int` | `logging.INFO` | 最小日志级别 |
| `fmt` | `str` | `None` | 自定义格式字符串 |

**默认格式**: `%(asctime)s | %(levelname)s | %(name)s | %(message)s`

### MetricLogger 类

```python
from runicorn.log_compat.torchvision import MetricLogger, SmoothedValue
```

#### MetricLogger

| 方法 | 描述 |
|------|------|
| `__init__(delimiter="\t")` | 创建指定分隔符的日志器 |
| `update(**kwargs)` | 更新指标并记录到 Runicorn |
| `log_every(iterable, print_freq, header)` | 带进度打印的生成器 |
| `add_meter(name, meter)` | 添加自定义 SmoothedValue 计量器 |
| `synchronize_between_processes()` | 跨分布式进程同步 |

#### SmoothedValue

| 属性 | 描述 |
|------|------|
| `median` | 窗口内值的中位数 |
| `avg` | 窗口内值的平均值 |
| `global_avg` | 所有更新的全局平均值 |
| `max` | 窗口内的最大值 |
| `value` | 最近的值 |

---

## 💡 示例

### 带控制台捕获的训练脚本

```python
import runicorn as rn
from tqdm import tqdm

def train():
    run = rn.init(
        path="resnet_training",
        capture_console=True,
        tqdm_mode="smart",
    )
    
    print("=" * 50)
    print("开始 ResNet 训练")
    print("=" * 50)
    
    for epoch in range(10):
        print(f"\nEpoch {epoch + 1}/10")
        
        # 带 tqdm 的训练循环
        train_loss = 0
        for batch in tqdm(train_loader, desc="训练中"):
            loss = train_step(batch)
            train_loss += loss
        
        avg_loss = train_loss / len(train_loader)
        print(f"训练损失: {avg_loss:.4f}")
        
        # 记录结构化指标
        run.log({"epoch": epoch, "train_loss": avg_loss})
    
    print("\n训练完成！")
    run.finish()

if __name__ == "__main__":
    train()
```

### 与现有 Logger 集成

```python
import logging
import runicorn as rn

# 现有 logger 设置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("my_app")

def train_with_existing_logger():
    run = rn.init(path="experiment")
    
    # 将 Runicorn handler 添加到现有 logger
    handler = run.get_logging_handler(level=logging.DEBUG)
    logger.addHandler(handler)
    
    logger.info("开始实验")
    
    for epoch in range(10):
        loss = train_epoch()
        logger.info(f"Epoch {epoch}: loss={loss:.4f}")
        run.log({"loss": loss})
    
    logger.info("实验完成")
    run.finish()
```

### MetricLogger 迁移

**之前**（独立 MetricLogger）：
```python
from utils import MetricLogger

metric_logger = MetricLogger()
for data in metric_logger.log_every(loader, 10):
    loss = model(data)
    metric_logger.update(loss=loss.item())
```

**之后**（Runicorn 集成）：
```python
from runicorn.log_compat.torchvision import MetricLogger
import runicorn as rn

run = rn.init(path="training", capture_console=True)

metric_logger = MetricLogger()
for data in metric_logger.log_every(loader, 10):
    loss = model(data)
    metric_logger.update(loss=loss.item())  # 现在也会记录到 Runicorn！

run.finish()
```

---

## 🔧 故障排除

### 问题：控制台输出未被捕获

**原因**: `capture_console=False`（默认值）

**解决方案**:
```python
run = rn.init(path="experiment", capture_console=True)
```

### 问题：日志文件有太多 tqdm 行

**原因**: 使用了 `tqdm_mode="all"`

**解决方案**:
```python
run = rn.init(path="experiment", capture_console=True, tqdm_mode="smart")
```

### 问题：Logging handler 不写入

**原因**: Handler 在 `run.init()` 之前或 `run.finish()` 之后创建

**解决方案**: 在 init 之后创建 handler，在 finish 之前使用：
```python
run = rn.init(path="experiment")
handler = run.get_logging_handler()  # 在 init 之后创建
logger.addHandler(handler)
# ... 使用 logger ...
run.finish()  # 此后 handler 停止工作
```

### 问题：MetricLogger 不记录到 Runicorn

**原因**: 调用 `update()` 时没有活动的 Run

**解决方案**: 确保在使用 MetricLogger 之前调用 `rn.init()`：
```python
import runicorn as rn
from runicorn.log_compat.torchvision import MetricLogger

run = rn.init(path="experiment")  # 必须先调用
metric_logger = MetricLogger()
metric_logger.update(loss=0.5)  # 现在会记录到 Runicorn
run.finish()
```

### 问题：ANSI 颜色在 Web UI 中不显示

**原因**: 这是预期行为 - ANSI 代码保留在 `logs.txt` 中

**解决方案**: Web UI 的 LogsViewer 组件会渲染 ANSI 颜色。在 Web UI 中查看日志以获得彩色输出。

---

## 📊 日志文件格式

控制台捕获写入 `<run_dir>/logs.txt`，带时间戳：

```
[HH:MM:SS] <消息>
```

示例：
```
[10:30:15] 开始训练...
[10:30:16] Epoch 1/10
[10:30:45] Training: 100%|██████████| 100/100 [00:29<00:00, 3.45it/s]
[10:30:46] 训练损失: 0.4523
[10:31:15] Epoch 2/10
...
```

Python logging handler 使用可配置格式（默认）：
```
HH:MM:SS | LEVEL | logger_name | message
```

---

**[返回指南](README.md)** | **[返回主页](../../README.md)**
