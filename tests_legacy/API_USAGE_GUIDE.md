# Runicorn API 使用指南

## ✅ 标准 API 使用方式（面向对象）

### 基础使用

```python
import runicorn as rn

# 1. 初始化实验
run = rn.init(
    project="my_project",
    name="experiment_1"
)

# 2. 记录配置参数（在第一步记录）
run.log({
    "learning_rate": 0.001,
    "batch_size": 32,
    "epochs": 100
}, step=0)

# 3. 记录训练指标
for step in range(1, 11):
    loss = 1.0 / (step + 1)
    accuracy = 0.5 + step * 0.05
    
    run.log({
        "loss": loss,
        "accuracy": accuracy
    }, step=step)

# 4. 更新汇总
run.summary({
    "best_loss": 0.1,
    "final_accuracy": 0.95,
    "total_epochs": 10
})

# 5. 完成实验
run.finish()

# 6. 访问 run ID
print(f"Run ID: {run.id}")
```

## ❌ 常见错误

### 错误 1：直接实例化 Run 类

```python
# ❌ 错误：不要直接实例化 Run
from runicorn import Run
run = Run(project="test", name="exp1")
```

```python
# ✅ 正确：使用 init() 函数
import runicorn as rn
run = rn.init(project="test", name="exp1")
```

### 错误 2：忘记调用 init()

```python
# ❌ 错误：未初始化就记录
import runicorn as rn
rn.log({"loss": 0.5})  # 没有 run 对象
```

```python
# ✅ 正确：先初始化
import runicorn as rn
run = rn.init(project="test")
run.log({"loss": 0.5})
```

### 错误 3：Step 管理错误

```python
# ❌ 错误：不提供 step 参数
run.log({"loss": 0.5})  # step 会自动递增，可能不符合预期
```

```python
# ✅ 正确：显式指定 step
for epoch in range(10):
    run.log({"loss": 0.5}, step=epoch)
```

### 错误 4：ID 属性名错误

```python
# ❌ 错误：使用 run_id
run = rn.init(project="test")
print(run.run_id)  # 属性不存在
```

```python
# ✅ 正确：使用 id
run = rn.init(project="test")
print(run.id)
```

## 📚 完整的 Run API

```python
import runicorn as rn

# 初始化
run = rn.init(project="...", name="...")

# 记录指标
run.log({"metric": value}, step=0)

# 记录文本日志
run.log_text("Some log message")

# 记录图片
run.log_image("image_name", image_path_or_array, step=0)

# 更新汇总
run.summary({"final_metric": value})

# 设置主要指标
run.set_primary_metric("accuracy", mode="max")

# 完成实验
run.finish()

# 访问 run 属性
print(run.id)              # Run ID
print(run.project)         # 项目名
print(run.name)            # 实验名
```

## 🔧 Run 对象属性和方法

### 只读属性
```python
run = rn.init(project="test", name="exp1")

run.id              # Run ID (字符串)
run.project         # 项目名
run.name            # 实验名
run.storage_root    # 存储根目录
run.run_dir         # Run 目录路径
```

### 主要方法
```python
# 记录指标
run.log(data: Dict, step: int = None, stage: str = None)

# 记录文本日志
run.log_text(text: str)

# 记录图片
run.log_image(key: str, image: Any, step: int = None, caption: str = None)

# 更新汇总
run.summary(update: Dict)

# 设置主要指标
run.set_primary_metric(metric_name: str, mode: str = "max")

# 完成实验
run.finish(status: str = "finished")

# Artifacts 相关
run.log_artifact(artifact: Artifact) -> int
run.use_artifact(name: str) -> Artifact
```

## 📝 测试脚本规范

在编写测试脚本时，务必遵循标准 API：

```python
import runicorn as rn
import os

# 设置存储位置
os.environ["RUNICORN_DIR"] = "/path/to/test/data"

# 创建实验
run = rn.init(project="test", name="experiment")

# 记录配置（作为指标记录）
run.log({"param": "value"}, step=0)

# 记录指标
for i in range(1, 11):
    run.log({"metric": i * 0.1}, step=i)

# 添加汇总
run.summary({"total_steps": 10})

# 完成
run.finish()
print(f"Created run: {run.id}")
```

## 🚨 核心要点

1. **使用 `rn.init()`** 来创建实验，返回 `Run` 对象
2. **通过 `run.log()`** 记录指标（面向对象风格）
3. **通过 `run.summary()`** 记录汇总
4. **通过 `run.finish()`** 完成实验
5. **访问 ID 使用 `run.id`**
6. **不要直接实例化 `Run` 类**

## 🎯 设计理念

- **显式优于隐式**：`run.log()` 明确知道在操作哪个 run
- **面向对象**：符合 Python 最佳实践和主流框架风格（wandb, TensorBoard）
- **支持并发**：可以同时管理多个 run 对象
- **类型安全**：更好的 IDE 自动补全和类型检查

---

参考文档：[docs/guides/zh/QUICKSTART.md](../docs/guides/zh/QUICKSTART.md)
