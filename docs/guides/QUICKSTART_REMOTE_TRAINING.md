# 快速开始：远程训练实时监控

**5 分钟上手** - 最简单的远程训练监控方案

---

## 🚀 快速开始（3 步）

### 步骤 1: 服务器端 - 记录训练数据

**在训练脚本中添加 3 行代码**:

```python
import runicorn  # 1. 导入

# 2. 初始化
run = runicorn.init(project="my_project", name="experiment_1")

# 训练循环
for epoch in range(100):
    for batch in data_loader:
        loss = train_step(batch)
        
        # 3. 记录指标
        run.log({"loss": loss, "accuracy": acc})

run.finish()  # 训练完成
```

### 步骤 2: 本地端 - 启动 Viewer

```bash
# 在本地电脑运行
runicorn viewer
```

浏览器自动打开 `http://localhost:23300`

### 步骤 3: 配置 SSH 同步

在 Web 界面中：

1. 点击 ⚙️ 设置
2. 选择 "远程同步"
3. 填写服务器信息：
   ```
   服务器: gpu-server.example.com
   用户名: your_username
   密钥: ~/.ssh/id_rsa
   远程目录: ~/.runicorn/experiments
   ```
4. 点击 "保存并启动同步"

**完成！** 🎉 现在可以实时查看训练指标了！

---

## 📊 实时查看

### 主界面

访问 `http://localhost:23300`，你会看到：

- 📝 **实验列表**: 所有训练任务
- 🟢 **运行状态**: Running / Completed / Failed
- 📈 **关键指标**: Loss, Accuracy 等
- ⏱️ **运行时间**: 已运行多久

### 实验详情

点击任意实验查看：

#### 指标图表
```
Loss 曲线 ↓
┌─────────────────────────────────┐
│  2.5 •                          │
│      \                          │
│  2.0   •                        │
│         \                       │
│  1.5     •─•─•─•──•──•──•       │
│                                 │
└─────────────────────────────────┘
   0    50   100  150  200  250
```

#### 实时日志
```
[18:30:45] Epoch 0, Loss: 2.301
[18:30:47] Epoch 0, Loss: 2.184
[18:30:49] Epoch 0, Loss: 1.987
...
```

---

## 💡 常见场景

### 场景 1: 单个实验监控

```python
# 服务器：train.py
import runicorn

run = runicorn.init(project="mnist", name="baseline")

for epoch in range(10):
    train_loss = train(model, data_loader)
    val_loss = validate(model, val_loader)
    
    run.log({
        "train_loss": train_loss,
        "val_loss": val_loss
    })

run.finish()
```

**本地查看**: 打开浏览器即可看到实时更新的 Loss 曲线

### 场景 2: 对比多个实验

```python
# 实验 1: 学习率 0.001
run1 = runicorn.init(project="mnist", name="lr_0.001")

# 实验 2: 学习率 0.01
run2 = runicorn.init(project="mnist", name="lr_0.01")

# 实验 3: 学习率 0.1
run3 = runicorn.init(project="mnist", name="lr_0.1")
```

**本地查看**: 
1. 在实验列表勾选 3 个实验
2. 点击 "对比"
3. 查看叠加的 Loss 曲线，找出最佳学习率

### 场景 3: 长期训练监控

```bash
# 服务器：使用 tmux 保持训练运行
tmux new -s training
python train.py  # 可能需要几天
# Ctrl+B, D (detach)

# 本地：随时查看
# 在办公室、在家、在咖啡店...
# 只要打开浏览器就能看到最新进度
```

---

## ⚡ 性能提示

### 启用 Manifest Sync（推荐）

**服务器一次性设置**:

```bash
# 生成 manifest
runicorn generate-manifest

# 设置自动生成（每 5 分钟）
crontab -e
# 添加: */5 * * * * cd ~/experiments && runicorn generate-manifest
```

**效果**: 同步速度提升 **20-50 倍** 🚀

### 仅同步元数据

在 Web UI 设置中：
- ☑️ 仅同步元数据和小文件
- ☐ 同步大文件（模型检查点）

**效果**: 更快的同步，更低的带宽

---

## 🔧 故障排除

### 问题: 连接不上服务器

```bash
# 测试 SSH 连接
ssh user@gpu-server.example.com

# 如果失败，检查：
# 1. 服务器地址正确？
# 2. SSH 端口开放？（默认 22）
# 3. 密钥权限正确？
chmod 600 ~/.ssh/id_rsa
```

### 问题: 看不到数据

```bash
# 1. 检查服务器端是否生成数据
ssh user@gpu-server.example.com
ls -la ~/.runicorn/experiments/

# 2. 检查同步状态
# Web UI 右上角应显示 🟢 已连接

# 3. 手动触发同步
# 点击 "立即同步" 按钮
```

### 问题: 更新太慢

```bash
# 启用 manifest sync（见上文）
# 或减少同步间隔
# Web UI 设置 → 同步间隔: 10 秒
```

---

## 📚 完整文档

更详细的使用指南，请查看：

- **完整工作流**: [REALTIME_MONITORING_WORKFLOW.md](./REALTIME_MONITORING_WORKFLOW.md)
- **API 文档**: [../api/zh/README.md](../api/zh/README.md)
- **Manifest Sync**: [../api/zh/manifest_api.md](../api/zh/manifest_api.md)

---

## 🎉 总结

只需 **5 分钟** 设置，你就能：

✅ 在远程 GPU 服务器训练模型  
✅ 在本地浏览器实时查看进度  
✅ 对比多个实验找到最佳配置  
✅ 随时随地监控训练状态  

**开始使用 Runicorn，让 ML 实验更简单！** 🚀

---

**问题？** 查看 [故障排除文档](./REALTIME_MONITORING_WORKFLOW.md#故障排除) 或提交 Issue
