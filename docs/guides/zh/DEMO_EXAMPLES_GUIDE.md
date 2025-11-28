[English](../en/DEMO_EXAMPLES_GUIDE.md) | [简体中文](DEMO_EXAMPLES_GUIDE.md)

---

# 演示代码指南

## 概述

本指南介绍Runicorn的演示示例，展示如何正确使用SDK API进行实验记录、模型版本管理、去重存储和血缘追踪。

## 新增演示代码

### 1. `quickstart_demo.py` - 快速入门

**最简单的5分钟入门示例**

```bash
python examples/quickstart_demo.py
```

**展示功能**：
- ✅ 基本实验初始化和完成
- ✅ 模型artifact创建和保存
- ✅ 模型加载和使用
- ✅ 实验与模型的自动关联

**代码特点**：
- 使用正确的API：`rn.init()`, `run.summary()`, `run.finish()`
- 简洁明了，适合首次使用者
- 完整展示最小工作流

### 2. `complete_workflow_demo.py` - 完整工作流

**模拟真实ML项目的完整演示**

```bash
python examples/complete_workflow_demo.py
```

**展示功能**：
- ✅ 实验记录与指标跟踪（4个实验）
- ✅ 模型版本控制（3个模型版本）
- ✅ **文件级去重效果**（共享预训练权重）
- ✅ 实验与模型的双向关联
- ✅ 模型使用和血缘追踪
- ✅ 模型评估和微调

**演示场景**：

1. **场景1: 基线模型训练**
   - 训练ResNet-50基线模型
   - 记录训练指标（loss, accuracy）
   - 保存模型为v1

2. **场景2: 改进模型训练**
   - 使用更好的超参数重新训练
   - 创建模型v2（共享预训练权重）
   - 展示性能提升

3. **场景3: 模型评估**
   - 加载模型v2进行评估
   - 记录测试集指标
   - 判断是否达到生产标准

4. **场景4: 针对特定任务微调**
   - 基于模型v2进行医疗影像微调
   - 创建新的模型artifact
   - 展示迁移学习

**去重效果（两文件模型结构）**：
- 每个模型包含2个文件：
  1. 共享权重文件（~1.9 MB）- 所有版本相同
  2. 微调权重文件（~950 KB）- 每个版本独有
- 3个模型版本都复用同一个共享权重文件
- 通过硬链接，共享文件只存储一次
- 节省约44%的存储空间（8.55 MB → 4.75 MB）
- 通过硬链接实现（Windows同盘符/Linux同文件系统）

## 核心API使用

### 正确的实验初始化和结束

```python
import runicorn as rn

# 初始化实验
run = rn.init(project="my_project", name="experiment_1")

# ... 实验代码 ...

# 结束实验
run.finish()
```

**❌ 错误用法**：
```python
run.finish()  # 不要这样用
```

### 记录指标

```python
# 记录单步指标
run.log(step=1, loss=0.5, accuracy=0.8)

# 记录汇总信息
run.summary({
    "final_accuracy": 0.95,
    "training_time": 120
})
```

**❌ 错误用法**：
```python
run.summary(...)  # 不要这样用
run.log_summary(...)  # 方法不存在
run.log_config(...)  # 方法不存在
```

### 创建和保存模型

#### 单文件模型
```python
# 创建artifact
artifact = rn.Artifact("my-model", type="model")
artifact.add_file("model.pth")
artifact.add_metadata({"accuracy": 0.95})
artifact.add_tags("production", "v2")

# 保存artifact（自动版本控制）
version = run.log_artifact(artifact)
```

#### 两文件模型（推荐，支持去重）
```python
# 创建artifact，包含多个文件
artifact = rn.Artifact("my-model", type="model")
artifact.add_file("shared_backbone.pth")     # 共享权重
artifact.add_file("task_head_v1.pth")        # 任务特定权重
artifact.add_metadata({
    "accuracy": 0.95,
    "files": {
        "backbone": "shared_backbone.pth",
        "head": "task_head_v1.pth"
    }
})

# 保存artifact
version = run.log_artifact(artifact)
```

**两文件结构的优势**:
- ✅ 多个版本共享相同的backbone，去重节省空间
- ✅ 只需存储不同的任务头文件
- ✅ 符合真实ML场景（预训练+微调）
- ✅ 可以节省40-60%的存储空间

### 使用模型

```python
# 加载模型（自动记录使用关系）
artifact = run.use_artifact("my-model:latest")  # 或 "my-model:v2"
model_path = artifact.download()

# 获取元数据
metadata = artifact.get_metadata()
accuracy = metadata.metadata.get('accuracy')
```

## 文件级去重原理

### 创建有共享部分的模型

```python
import random
import json
from pathlib import Path

def create_model_with_shared_weights(path, version):
    # 共享部分（所有版本相同）
    random.seed(42)  # 固定种子
    shared_weights = [random.random() for _ in range(50000)]
    
    # 独有部分（每个版本不同）
    random.seed(version * 100)  # 不同种子
    unique_weights = [random.random() for _ in range(25000)]
    
    model_data = {
        "shared": shared_weights,  # 共享
        "unique": unique_weights,  # 独有
        "version": version
    }
    
    with open(path, 'w') as f:
        json.dump(model_data, f)
```

### 去重效果计算

- **不使用去重**：N个版本 × 文件大小 = 总大小
- **使用去重**：共享部分 + N×独有部分 = 总大小
- **节省空间**：(不去重 - 去重) / 不去重 × 100%

**示例**：
- 3个模型版本，每个2.85 MB
- 不去重：2.85 × 3 = 8.55 MB
- 去重：1.9（共享）+ 0.95×3（独有）= 4.75 MB
- 节省：(8.55 - 4.75) / 8.55 = 44.4%

## 查看结果

### 启动Web UI

```bash
runicorn viewer --host 0.0.0.0 --port 5000
```

### 访问功能

1. **实验列表**（http://localhost:5000）
   - 查看"产生制品"列
   - 查看"使用制品"列

2. **实验详情**
   - 点击实验进入详情页
   - 切换到"关联制品"标签页
   - 查看该实验创建和使用的模型

3. **模型详情**
   - 点击模型名称进入详情
   - "训练历史"标签：查看创建该模型的实验
   - "性能趋势"标签：对比不同版本的性能
   - "血缘关系"标签：查看模型依赖关系图

4. **去重统计**
   - 模型页面右上角查看去重统计
   - 显示节省的空间和比例

## 批量运行

### Linux/Mac
```bash
chmod +x examples/run_all_demos.sh
./examples/run_all_demos.sh
```

### Windows
```cmd
examples\run_all_demos.bat
```

## 常见错误

### 1. API调用错误

**❌ 错误**：
```python
run.log_config(params)  # 方法不存在
run.log_summary({...})  # 方法不存在
```

**✅ 正确**：
```python
run.summary({"hyperparameters": params})
run.summary({...})
```

### 2. 文件清理

**记得清理临时文件**：
```python
model_path.unlink()  # 删除临时文件
```

### 3. 去重不生效

**原因**：
- Windows：文件不在同一盘符
- Linux/Mac：文件不在同一文件系统

**解决**：
- 确保所有文件在同一盘符/文件系统
- 使用绝对路径或相对于项目的路径

## 最佳实践

1. **实验命名**：使用有意义的project和name
2. **模型命名**：使用统一的命名规范
3. **元数据**：记录完整的超参数和指标
4. **标签**：使用标签标记重要版本
5. **描述**：为artifact添加清晰的描述
6. **清理**：及时清理临时文件

## 进一步学习

- 查看 `examples/test_artifacts.py` - 基础用法
- 查看 `examples/user_workflow_demo.py` - 完整项目
- 查看 `deduplication_demo/` - 去重详细测试
- 阅读 `docs/guides/zh/ARTIFACTS_GUIDE.md` - 详细文档

## 总结

新的演示代码修正了之前的API使用错误，展示了：

✅ 正确的SDK API使用方式
✅ 实验记录和指标跟踪
✅ 模型版本控制和管理
✅ 文件级去重效果（45%空间节省）
✅ 实验与模型的关联关系
✅ 完整的血缘追踪

通过这些示例，你可以快速掌握Runicorn的核心功能，并应用到实际项目中。

