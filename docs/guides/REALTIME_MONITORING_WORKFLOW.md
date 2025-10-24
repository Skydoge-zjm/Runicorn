# 实时监控工作流 - 完整指南

**场景**: 在本地 SSH 到远程服务器训练模型，实时在本地查看训练指标

**适用于**: 
- ML 研究员和工程师
- 远程 GPU 服务器训练
- 需要实时监控训练进度

---

## 📋 目录

1. [工作流概览](#工作流概览)
2. [环境准备](#环境准备)
3. [步骤 1: 在服务器训练模型](#步骤-1-在服务器训练模型)
4. [步骤 2: 配置远程同步](#步骤-2-配置远程同步)
5. [步骤 3: 实时查看指标](#步骤-3-实时查看指标)
6. [高级用法](#高级用法)
7. [故障排除](#故障排除)

---

## 工作流概览

```
┌─────────────────────────────────────────────────────────────┐
│                      完整工作流                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  服务器端 (GPU 训练服务器)                                   │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  1. 训练脚本 (train.py)                               │ │
│  │     import runicorn                                   │ │
│  │     run = runicorn.init(...)                          │ │
│  │     run.log({"loss": loss, "acc": acc})              │ │
│  │                                                       │ │
│  │  2. 实验数据保存到                                     │ │
│  │     /data/experiments/my_project/exp1/runs/...        │ │
│  │                                                       │ │
│  │  3. Manifest 生成 (可选，推荐)                         │ │
│  │     runicorn generate-manifest                        │ │
│  │     → .runicorn/full_manifest.json                    │ │
│  └───────────────────────────────────────────────────────┘ │
│                          ↓                                  │
│                    SSH + SFTP 同步                          │
│                          ↓                                  │
│  本地端 (开发机器)                                           │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  4. SSH 远程同步配置                                   │ │
│  │     runicorn viewer (启动 Web UI)                     │ │
│  │     → 配置 SSH 连接                                    │ │
│  │     → 选择远程目录                                     │ │
│  │     → 启动自动同步                                     │ │
│  │                                                       │ │
│  │  5. 本地缓存                                           │ │
│  │     ~/.runicorn/cache/remote_server/...               │ │
│  │                                                       │ │
│  │  6. Web UI 查看 (http://localhost:23300)              │ │
│  │     → 实时指标图表                                     │ │
│  │     → 训练日志流                                       │ │
│  │     → 实验对比                                         │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 环境准备

### 服务器端 (GPU 训练服务器)

```bash
# 1. 安装 Runicorn
pip install runicorn

# 2. 验证安装
runicorn --version

# 3. (可选) 配置 Manifest 自动生成
# 按照 docs/future/SERVER_SETUP_GUIDE.md 设置
```

### 本地端 (开发机器)

```bash
# 1. 安装 Runicorn
pip install runicorn

# 2. 确保可以 SSH 到服务器
ssh user@gpu-server.example.com

# 3. 配置 SSH 密钥（推荐，避免重复输入密码）
ssh-copy-id user@gpu-server.example.com
```

---

## 步骤 1: 在服务器训练模型

### 1.1 创建训练脚本

**服务器上**: `train.py`

```python
import torch
import torch.nn as nn
import runicorn

# 初始化 Runicorn 运行
run = runicorn.init(
    project="image_classification",
    name="resnet50_experiment",
    config={
        "model": "resnet50",
        "batch_size": 32,
        "learning_rate": 0.001,
        "epochs": 100,
        "optimizer": "Adam",
        "dataset": "CIFAR-10"
    },
    tags=["production", "resnet", "v2.0"]
)

# 模型定义
model = ...  # 你的 PyTorch 模型
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
criterion = nn.CrossEntropyLoss()

# 训练循环
for epoch in range(100):
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    
    for batch_idx, (data, target) in enumerate(train_loader):
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        
        # 累计指标
        total_loss += loss.item()
        pred = output.argmax(dim=1)
        correct += pred.eq(target).sum().item()
        total += target.size(0)
        
        # 每 10 个 batch 记录一次
        if batch_idx % 10 == 0:
            step = epoch * len(train_loader) + batch_idx
            
            # 记录训练指标
            run.log({
                "train/loss": loss.item(),
                "train/accuracy": 100. * correct / total,
                "train/learning_rate": optimizer.param_groups[0]['lr'],
                "epoch": epoch,
            }, step=step)
            
            # 打印日志（会自动同步）
            print(f"Epoch {epoch} [{batch_idx}/{len(train_loader)}] "
                  f"Loss: {loss.item():.4f} Acc: {100.*correct/total:.2f}%")
    
    # 验证
    model.eval()
    val_loss = 0
    val_correct = 0
    val_total = 0
    
    with torch.no_grad():
        for data, target in val_loader:
            output = model(data)
            loss = criterion(output, target)
            val_loss += loss.item()
            pred = output.argmax(dim=1)
            val_correct += pred.eq(target).sum().item()
            val_total += target.size(0)
    
    # 记录验证指标
    run.log({
        "val/loss": val_loss / len(val_loader),
        "val/accuracy": 100. * val_correct / val_total,
    }, step=(epoch + 1) * len(train_loader))
    
    # 记录汇总指标
    run.summary({
        "best_val_accuracy": max(
            run.summary.get("best_val_accuracy", 0),
            100. * val_correct / val_total
        ),
        "total_epochs": epoch + 1
    })
    
    # 每 10 个 epoch 保存检查点
    if (epoch + 1) % 10 == 0:
        torch.save(model.state_dict(), f'checkpoint_epoch_{epoch+1}.pth')
        print(f"✓ Checkpoint saved: epoch {epoch+1}")

# 训练完成
run.finish()
print("✓ Training completed!")
```

### 1.2 启动训练

```bash
# SSH 到服务器
ssh user@gpu-server.example.com

# 进入项目目录
cd /home/user/projects/my_ml_project

# 启动训练（可选：使用 tmux/screen 保持会话）
tmux new -s training
python train.py

# Detach from tmux: Ctrl+B, then D
# 训练会在后台继续运行
```

### 1.3 验证数据生成

```bash
# 检查实验数据目录
ls -la ~/.runicorn/experiments/image_classification/resnet50_experiment/runs/

# 应该看到类似的结构：
# 20250123_180000_abc123/
#   ├── meta.json          # 元数据
#   ├── status.json        # 运行状态
#   ├── summary.json       # 汇总指标
#   ├── events.jsonl       # 时间序列指标
#   └── logs.txt           # 训练日志
```

---

## 步骤 2: 配置远程同步

### 2.1 启动本地 Runicorn Viewer

**在本地机器上**:

```bash
# 启动 Runicorn Web UI
runicorn viewer

# 输出类似：
# ╭──────────────────────────────────────────────────────────╮
# │ Runicorn Viewer                                          │
# │ Version: 0.4.0                                           │
# │ URL: http://127.0.0.1:23300                             │
# │                                                          │
# │ Press Ctrl+C to stop                                     │
# ╰──────────────────────────────────────────────────────────╯
```

### 2.2 在浏览器中配置 SSH 连接

1. **打开浏览器**: `http://127.0.0.1:23300`

2. **进入设置页面**: 
   - 点击右上角 ⚙️ 设置图标
   - 或访问 `http://127.0.0.1:23300/settings`

3. **添加 SSH 连接**:
   
   点击 "远程同步" 选项卡，填写连接信息：

   ```
   连接名称: GPU Server 1
   服务器地址: gpu-server.example.com
   端口: 22
   用户名: your_username
   
   认证方式: SSH 密钥（推荐）
   密钥路径: ~/.ssh/id_rsa
   
   或
   
   认证方式: 密码
   密码: ********
   ```

4. **测试连接**:
   - 点击 "测试连接" 按钮
   - 应显示 ✓ 连接成功

5. **选择远程目录**:
   ```
   远程实验根目录: /home/user/.runicorn/experiments
   ```
   
   或使用自定义目录：
   ```
   远程实验根目录: /data/experiments
   ```

6. **配置同步模式**:
   
   ```
   同步模式: 自动同步（推荐）
   同步间隔: 30 秒
   
   可选：
   ☑ 启用 Manifest-based sync（高性能）
   ☑ 仅同步元数据和小文件
   ☐ 同步大文件（模型检查点等）
   ```

7. **启动同步**:
   - 点击 "保存并启动同步" 按钮
   - 系统开始初始同步

### 2.3 使用 CLI 配置（高级用户）

```bash
# 方法 1: 交互式配置
runicorn config ssh add

# 按提示输入信息

# 方法 2: 直接命令配置
runicorn config ssh add \
  --name "GPU Server 1" \
  --host gpu-server.example.com \
  --port 22 \
  --user your_username \
  --key ~/.ssh/id_rsa \
  --remote-root /home/user/.runicorn/experiments

# 启动同步
runicorn sync start --connection "GPU Server 1"
```

---

## 步骤 3: 实时查看指标

### 3.1 查看实验列表

1. **返回主页**: 点击 "Runicorn" 图标或访问 `http://127.0.0.1:23300`

2. **实验列表**:
   - 看到所有同步的实验
   - 显示项目、名称、状态、开始时间等
   - 正在运行的实验标记为 🟢 Running

### 3.2 查看实时指标

点击正在运行的实验进入详情页：

#### 指标图表

**训练损失**:
```
Loss 曲线会实时更新，显示：
- train/loss: 实时训练损失
- val/loss: 验证损失（每个 epoch）
```

**准确率**:
```
Accuracy 曲线显示：
- train/accuracy: 训练准确率
- val/accuracy: 验证准确率
```

**学习率**:
```
Learning Rate 曲线：
- 跟踪学习率变化
- 如果使用 scheduler，可以看到下降
```

#### 实时日志流

```
在 "日志" 选项卡：

[18:30:45] Epoch 0 [0/1563] Loss: 2.3025 Acc: 10.00%
[18:30:47] Epoch 0 [10/1563] Loss: 2.1842 Acc: 15.63%
[18:30:49] Epoch 0 [20/1563] Loss: 1.9876 Acc: 21.88%
...
[18:35:12] ✓ Checkpoint saved: epoch 10
...

日志会自动滚动显示最新内容
```

#### 系统指标（可选）

如果服务器安装了 GPU 监控：

```
GPU 使用率: 95%
GPU 内存: 8.2 GB / 11 GB
CPU 使用率: 45%
内存使用: 12 GB / 64 GB
```

### 3.3 对比多个实验

1. **进入对比页面**: 
   - 主页选择多个实验（勾选框）
   - 点击 "对比" 按钮

2. **并排查看**:
   ```
   Experiment 1          Experiment 2          Experiment 3
   ─────────────        ─────────────        ─────────────
   ResNet50             ResNet18             VGG16
   LR: 0.001            LR: 0.01             LR: 0.001
   Batch: 32            Batch: 64            Batch: 32
   
   最佳验证准确率:
   85.6%                82.3%                83.9%
   ```

3. **重叠图表**:
   - 所有实验的损失曲线叠加在一张图上
   - 不同颜色区分
   - 可以清楚地看到哪个配置效果更好

---

## 高级用法

### 使用 Manifest-Based Sync（推荐）

Manifest sync 提供 **99% 网络减少** 和 **95% 时间减少**。

#### 服务器端设置

```bash
# 1. 首次手动生成
cd /data/experiments
runicorn generate-manifest --verbose

# 2. 设置自动生成（推荐）
# 方法 A: Systemd (Linux)
sudo systemctl enable runicorn-manifest.timer
sudo systemctl start runicorn-manifest.timer

# 方法 B: Cron (Linux/macOS)
crontab -e
# 添加：每 5 分钟生成一次
*/5 * * * * cd /data/experiments && runicorn generate-manifest

# 方法 C: Task Scheduler (Windows)
# 参考 docs/future/SERVER_SETUP_GUIDE.md
```

#### 客户端自动使用

Manifest sync **默认启用**，无需额外配置。系统会：

1. 尝试下载 manifest（<1 秒）
2. 计算需要同步的文件
3. 并发下载变更文件
4. 如果 manifest 不可用，自动回退到传统模式

### 监控多个服务器

```python
# 在不同窗口或标签页
# 服务器 1
runicorn viewer --port 23300

# 服务器 2
runicorn viewer --port 23301

# 服务器 3
runicorn viewer --port 23302

# 然后分别配置不同的 SSH 连接
```

### 离线模式

即使断开 SSH，已同步的数据仍然可以查看：

```bash
# 停止同步但保持 viewer 运行
# 在 Web UI 设置中点击 "暂停同步"

# 或者完全离线
runicorn viewer --offline
```

### 导出数据

```bash
# 导出实验数据为 CSV
runicorn export --run-id 20250123_180000_abc123 --format csv

# 导出为 TensorBoard 格式
runicorn export --run-id 20250123_180000_abc123 --format tensorboard
```

---

## 故障排除

### 问题 1: 无法连接到服务器

**症状**: SSH 连接测试失败

**解决方案**:
```bash
# 1. 检查网络连接
ping gpu-server.example.com

# 2. 检查 SSH 服务
ssh user@gpu-server.example.com

# 3. 检查防火墙
# 确保端口 22 开放

# 4. 检查密钥权限
chmod 600 ~/.ssh/id_rsa

# 5. 查看详细错误
# 在 Web UI 的浏览器控制台查看详细日志
```

### 问题 2: 同步很慢

**症状**: 初始同步需要很长时间

**解决方案**:

```bash
# 方法 1: 启用 Manifest sync（推荐）
# 在服务器端设置 manifest 生成
runicorn generate-manifest

# 方法 2: 仅同步元数据
# Web UI 设置中：
# ☑ 仅同步元数据和小文件
# ☐ 同步大文件

# 方法 3: 减少同步实验数量
# 仅同步最近的实验
# 活跃窗口: 最近 24 小时
```

### 问题 3: 指标不更新

**症状**: 图表停止更新

**解决方案**:

```bash
# 1. 检查训练是否还在运行
ssh user@gpu-server.example.com
ps aux | grep python

# 2. 检查同步状态
# Web UI 右上角应显示 🟢 已连接
# 如果显示 🔴 断开连接，点击重新连接

# 3. 手动触发同步
# 点击 "立即同步" 按钮

# 4. 检查日志
# ~/.runicorn/logs/sync.log
```

### 问题 4: 数据显示不完整

**症状**: 某些实验或文件缺失

**解决方案**:

```bash
# 1. 检查服务器端文件
ssh user@gpu-server.example.com
ls -la ~/.runicorn/experiments/

# 2. 清除本地缓存重新同步
rm -rf ~/.runicorn/cache/gpu-server
# 然后在 Web UI 重新启动同步

# 3. 检查权限
# 确保 SSH 用户有读取权限
```

### 问题 5: 内存占用高

**症状**: Runicorn viewer 占用大量内存

**解决方案**:

```bash
# 1. 限制缓存大小
runicorn viewer --cache-size 1GB

# 2. 清理旧数据
runicorn cache clean --older-than 30d

# 3. 仅缓存最近实验
# Web UI 设置 → 仅同步最近 7 天的实验
```

---

## 最佳实践

### 1. 开发流程

```
1. 本地开发和调试代码
   ↓
2. 提交到 Git
   ↓
3. 在服务器拉取代码
   ↓
4. 启动训练（使用 tmux/screen）
   ↓
5. 在本地 Runicorn 查看进度
   ↓
6. 根据指标调整超参数
   ↓
7. 训练完成后分析结果
```

### 2. 组织实验

```python
# 使用有意义的 project 和 name
run = runicorn.init(
    project="paper_reproduction",      # 项目名称
    name="transformer_base_v1",        # 实验名称
    tags=["baseline", "attention"],    # 标签便于筛选
)

# 记录完整的配置
run.config.update({
    "model": "transformer",
    "layers": 6,
    "heads": 8,
    "d_model": 512,
    # ... 所有超参数
})
```

### 3. 记录策略

```python
# 不同频率记录不同指标
# 每个 batch: 训练损失
if batch_idx % 10 == 0:
    run.log({"train/loss": loss.item()}, step=step)

# 每个 epoch: 验证指标
run.log({
    "val/loss": val_loss,
    "val/accuracy": val_acc,
}, step=epoch)

# 训练结束: 汇总指标
run.summary({
    "best_val_accuracy": best_acc,
    "total_time": training_time,
    "final_loss": final_loss,
})
```

### 4. 性能优化

```python
# 批量记录（减少 I/O）
metrics_buffer = []

for batch in data_loader:
    # ... 训练 ...
    metrics_buffer.append({
        "loss": loss.item(),
        "step": step
    })
    
    # 每 100 个 batch 批量记录
    if len(metrics_buffer) >= 100:
        for m in metrics_buffer:
            run.log({"train/loss": m["loss"]}, step=m["step"])
        metrics_buffer.clear()
```

---

## 完整示例：端到端工作流

### 场景

研究员 Alice 需要在实验室的 GPU 服务器上训练多个模型，在办公室电脑上实时监控。

### 步骤

```bash
# ═══════════════════════════════════════════════════════════
# 第 1 天上午：服务器设置
# ═══════════════════════════════════════════════════════════

# SSH 到服务器
ssh alice@lab-gpu-01.university.edu

# 安装 Runicorn
pip install runicorn

# 设置 Manifest 自动生成
crontab -e
# 添加：*/5 * * * * cd ~/experiments && runicorn generate-manifest

# 验证
runicorn generate-manifest --verbose


# ═══════════════════════════════════════════════════════════
# 第 1 天上午：准备训练脚本
# ═══════════════════════════════════════════════════════════

# 编辑训练脚本
vim ~/projects/vision/train_resnet.py
# 添加 Runicorn 集成（见上文示例）

# 启动第一个实验
tmux new -s exp1
python train_resnet.py --model resnet50 --lr 0.001 --batch-size 32
# Ctrl+B, D (detach)


# ═══════════════════════════════════════════════════════════
# 第 1 天下午：本地监控设置
# ═══════════════════════════════════════════════════════════

# 在本地电脑（办公室）
# 确保可以 SSH
ssh alice@lab-gpu-01.university.edu

# 启动 Runicorn viewer
runicorn viewer

# 浏览器访问 http://localhost:23300
# 在 Web UI 配置 SSH 连接：
#   - 服务器: lab-gpu-01.university.edu
#   - 用户: alice
#   - 密钥: ~/.ssh/id_rsa
#   - 远程目录: /home/alice/experiments

# 查看实时训练进度
# ✓ 看到实验 "resnet50_experiment"
# ✓ Loss 曲线实时更新
# ✓ 日志流实时显示


# ═══════════════════════════════════════════════════════════
# 第 1 天晚上：启动更多实验
# ═══════════════════════════════════════════════════════════

# SSH 到服务器
ssh alice@lab-gpu-01.university.edu

# 启动实验 2
tmux new -s exp2
python train_resnet.py --model resnet18 --lr 0.01 --batch-size 64
# Ctrl+B, D

# 启动实验 3
tmux new -s exp3
python train_vgg.py --model vgg16 --lr 0.001 --batch-size 32
# Ctrl+B, D

# 在本地可以同时看到 3 个实验并行运行


# ═══════════════════════════════════════════════════════════
# 第 2 天：分析和对比
# ═══════════════════════════════════════════════════════════

# 在本地 Web UI
# 1. 查看实验列表
# 2. 选择 3 个实验
# 3. 点击 "对比"
# 4. 查看哪个配置效果最好
# 5. 决定继续调优哪个模型


# ═══════════════════════════════════════════════════════════
# 第 3 天：继续改进
# ═══════════════════════════════════════════════════════════

# 基于对比结果，启动新实验
ssh alice@lab-gpu-01.university.edu
tmux new -s exp4
python train_resnet.py --model resnet50 --lr 0.0005 --batch-size 64
# 使用调整后的超参数

# 本地继续监控
# ✓ 可以看到所有历史实验
# ✓ 实时对比新旧实验
# ✓ 快速迭代优化
```

---

## 总结

这个工作流让你能够：

✅ **便捷训练**: 在远程 GPU 服务器训练，无需坐在机房  
✅ **实时监控**: 本地浏览器查看训练进度，随时随地  
✅ **高效同步**: Manifest-based sync 提供近乎即时的数据同步  
✅ **灵活对比**: 轻松对比多个实验，快速找到最佳配置  
✅ **持续改进**: 基于实时反馈快速迭代，缩短研究周期

---

## 相关文档

- **API 文档**: [../api/zh/manifest_api.md](../api/zh/manifest_api.md)
- **SSH API**: [../api/zh/ssh_api.md](../api/zh/ssh_api.md)
- **服务器设置**: [../future/SERVER_SETUP_GUIDE.md](../future/SERVER_SETUP_GUIDE.md)
- **完整工作流视频**: (待添加)

---

**Happy Training! 🚀**
