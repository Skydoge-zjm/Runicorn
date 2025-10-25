[English](../en/REMOTE_STORAGE_USER_GUIDE.md) | [简体中文](REMOTE_STORAGE_USER_GUIDE.md)

---

> ⚠️  **已弃用 (Deprecated in v0.5.0)**  
> 
> 此文档描述的远程同步功能（基于文件传输）在 v0.5.0 中已被弃用。  
> 请使用新的 **Remote Viewer** 功能，获得更好的体验：
> 
> - ✅ 无需同步，实时访问远程数据
> - ✅ 零本地存储占用
> - ✅ 连接启动仅需数秒，而非数小时
> - ✅ 完全实时（< 100ms）而非 5-10 分钟延迟
> 
> **新功能指南**: [Remote Viewer 用户指南](REMOTE_VIEWER_GUIDE.md)  
> **迁移指南**: [0.4.x → 0.5.0 迁移指南](MIGRATION_GUIDE_v0.4_to_v0.5.md)
> 
> 以下内容仅供参考，功能仍可使用但不再推荐。

---

# Runicorn 远程存储使用指南 (已弃用)

## 📖 快速开始（5分钟）

### 什么是远程存储模式？

远程存储模式让你可以**在本地查看和管理远程服务器上的 Artifacts，无需同步所有文件**。

**对比**:
- ❌ 旧方式：同步 340GB 到本地（8小时）
- ✅ 新方式：同步 200MB 元数据（5分钟）

---

## 🚀 使用步骤

### 步骤1：打开远程存储配置

1. 启动 Runicorn Viewer
   ```bash
   runicorn viewer
   ```

2. 在浏览器中打开: `http://localhost:23300`

3. 点击顶部菜单 **"远程存储"** (🌩️ 图标)

### 步骤2：配置 SSH 连接

填写以下信息：

**必填项**:
- **服务器地址**: 如 `gpu-server.lab.edu` 或 `192.168.1.100`
- **用户名**: SSH 登录用户名
- **远程目录**: Runicorn 数据存储路径，如 `/home/user/runicorn_data`

**认证方式**（选择一种）:
- **SSH 密钥**（推荐）:
  - 点击"选择私钥文件"上传 `~/.ssh/id_rsa`
  - 或直接粘贴私钥内容
  - 如果有密码，填写"私钥密码"
  
- **密码认证**:
  - 选择"密码"单选按钮
  - 输入 SSH 密码
  
- **SSH Agent**:
  - 如果已配置 SSH Agent，直接选择此项

**可选设置**:
- **自动同步**: 开启后定期同步元数据（推荐）
- **同步间隔**: 默认 10 分钟

### 步骤3：连接并同步

1. 点击 **"连接并同步元数据"** 按钮

2. 等待连接建立（通常 2-3 秒）

3. 观察同步进度：
   ```
   元数据同步进度
   [████████████░░░░] 75%
   (150/200 文件)
   当前: artifacts/model/resnet50/metadata.json
   ```

4. 等待 5 分钟左右完成
   ```
   ✅ 元数据同步完成！
   ```

5. Header 右侧显示 **"远程 🌩️"** 徽章

### 步骤4：浏览远程 Artifacts

1. 点击顶部菜单 **"Artifacts"**

2. 看到所有远程 artifacts 列表（秒级加载）
   - 从本地缓存读取
   - 响应速度与本地相同

3. 点击任意 artifact 查看详情
   - 元数据、文件列表、版本历史
   - 一切从本地缓存，极快！

### 步骤5：下载文件（按需）

1. 在 Artifact 详情页，点击 **"下载到本地 (8.00 GB)"** 按钮

2. 弹出下载进度窗口：
   ```
   📥 下载 Artifact: resnet50:v3
   [████████████░░░░] 75%
   文件: 1 / 1
   大小: 6.00 GB / 8.00 GB
   ```

3. 等待下载完成（根据网速，如 10 分钟）

4. 完成后：
   ```
   ✅ 下载完成！
   文件已保存到: /home/user/.runicorn_remote_cache/.../resnet50/v3
   ```

5. 点击 **"查看下载位置"** 打开文件夹

### 步骤6：管理远程 Artifacts

**删除旧版本**:
1. 在 Artifact 详情页点击 **"删除版本"**
2. 确认对话框（提示：将在远程服务器执行）
3. 2秒后完成
4. ✅ "Soft deleted resnet50:v1 on remote server"

**设置别名**（通过 API）:
```bash
curl -X POST http://localhost:23300/api/remote/artifacts/resnet50/v3/alias \
  -H "Content-Type: application/json" \
  -d '{"alias": "production"}'
```

---

## 🌩️ Header 状态指示器

### 查看详细状态

点击 Header 右侧的 **"远程 🌩️"** 徽章，弹出详细信息：

```
远程存储状态
├─ 连接状态: ✅ 已连接
├─ 上次同步: 2分钟前
├─ 缓存 Artifacts: 50 个
└─ 缓存大小: 180 MB

[立即同步] [断开]
```

### 快捷操作

- **立即同步**: 手动触发元数据同步
- **断开**: 断开远程连接，切换回本地模式

---

## 🔧 高级功能

### 切换存储模式

**通过 API**:
```bash
# 切换到远程模式
curl -X POST http://localhost:23300/api/remote/mode/switch \
  -H "Content-Type: application/json" \
  -d '{"mode": "remote"}'

# 切换到本地模式
curl -X POST http://localhost:23300/api/remote/mode/switch \
  -H "Content-Type: application/json" \
  -d '{"mode": "local"}'
```

### 缓存管理

**清空缓存**:
```bash
curl -X POST http://localhost:23300/api/remote/cache/clear
```

**LRU 清理**（删除旧文件）:
```bash
curl -X POST http://localhost:23300/api/remote/cache/cleanup
```

### 查看下载任务

```bash
# 列出所有下载任务
curl http://localhost:23300/api/remote/downloads

# 查询特定任务进度
curl http://localhost:23300/api/remote/download/{task_id}/status

# 取消下载
curl -X DELETE http://localhost:23300/api/remote/download/{task_id}
```

---

## 💡 使用技巧

### 技巧1：首次连接后断开

首次同步完成后，可以断开连接：
- 缓存的元数据仍然保留
- 可以浏览 artifacts（从缓存）
- 需要下载或管理时再连接

**优点**: 节省 SSH 连接资源

### 技巧2：按需下载策略

不需要下载所有 artifacts，只下载需要的：
- 浏览时：从缓存查看（不下载）
- 需要文件时：点击下载（明确操作）
- 节省：带宽、时间、本地空间

### 技巧3：使用自动同步

开启自动同步（默认10分钟）：
- 自动获取最新元数据
- 无需手动同步
- 始终看到最新状态

### 技巧4：多服务器管理

可以连接不同的服务器：
- 每个服务器有独立的缓存目录
- 切换服务器只需重新连接
- 缓存目录格式: `.runicorn_remote_cache/{host}_{user}`

---

## ❓ 常见问题

### Q1: 需要同步多少数据？

**A**: 只同步元数据文件（JSON），**不**同步大文件：
- 同步: `metadata.json`, `manifest.json`, `versions.json` 等
- 跳过: 模型文件（.pth, .h5）、数据集、图片

**典型大小**: 200MB 元数据 vs 340GB 全部数据

### Q2: 同步需要多长时间？

**A**: 取决于 artifacts 数量和网络速度：
- 小项目（10 artifacts）: ~30秒
- 中项目（50 artifacts）: ~2分钟
- 大项目（200 artifacts）: ~5分钟

### Q3: 下载的文件保存在哪里？

**A**: 默认保存在：
```
~/.runicorn_remote_cache/{host}_{user}/downloads/{artifact_name}/v{version}/
```

下载完成后会显示具体路径，可以复制。

### Q4: 可以同时下载多个 artifacts 吗？

**A**: 可以！下载任务在后台执行，可以：
- 开始下载 artifact A
- 最小化进度窗口
- 开始下载 artifact B
- 通过 API 查看所有任务: `GET /api/remote/downloads`

### Q5: 删除操作在哪里执行？

**A**: 
- **远程模式**: 删除操作在**服务器**上执行
- **本地模式**: 删除操作在**本地**执行

提示信息会明确告诉你操作位置。

### Q6: 断开连接后缓存会保留吗？

**A**: 会！
- 断开连接后，元数据缓存仍然保留
- 可以浏览 artifacts（从缓存）
- 但不能下载新文件或管理（需要连接）

### Q7: 如何切换回本地模式？

**A**: 两种方式：
1. 点击 Header "远程"徽章 → 点击"断开"
2. 关闭 Viewer 重启（自动使用本地模式）

---

## 🔒 安全建议

### 推荐认证方式

1. **SSH 密钥**（最推荐）
   ```bash
   # 在本地生成密钥对
   ssh-keygen -t rsa -b 4096
   
   # 复制公钥到服务器
   ssh-copy-id user@server.edu
   
   # 在 Runicorn 中使用私钥
   ```

2. **SSH Agent**（便捷）
   ```bash
   # 启动 SSH Agent
   eval "$(ssh-agent -s)"
   
   # 添加密钥
   ssh-add ~/.ssh/id_rsa
   
   # Runicorn 自动使用
   ```

3. **密码**（不推荐，仅测试）

### 私钥安全

- ✅ 私钥只在内存中，不保存到磁盘
- ✅ 关闭 Viewer 后私钥自动清除
- ✅ 使用标准 SSH 加密协议
- ❌ 不要在公共计算机上粘贴私钥

---

## 🐛 故障排查

### 问题：连接失败

**症状**: "Connection failed: timeout"

**排查**:
1. 检查服务器地址和端口是否正确
2. 测试网络连通性: `ping gpu-server.edu`
3. 测试 SSH 连接: `ssh user@server.edu`
4. 检查防火墙设置

### 问题：同步失败

**症状**: "Sync failed: permission denied"

**排查**:
1. 检查远程目录路径是否正确
2. 验证目录权限: `ls -ld /home/user/runicorn_data`
3. 确保 SSH 密钥有读取权限
4. 检查服务器上是否有 Python 3.8+

### 问题：下载失败

**症状**: "Download failed: checksum mismatch"

**排查**:
1. 重新同步元数据: 点击"立即同步"
2. 清空缓存: `POST /api/remote/cache/clear`
3. 检查网络稳定性
4. 查看错误详情: 下载进度窗口中显示

### 问题：无法查看 artifacts

**症状**: 远程模式下 artifacts 列表为空

**排查**:
1. 确认已连接: Header 显示"远程 🌩️"
2. 检查同步是否完成: 查看同步进度
3. 验证远程目录结构: 
   ```bash
   # 在服务器上检查
   ls -la /home/user/runicorn_data/artifacts/
   ```
4. 查看错误日志: 浏览器控制台（F12）

---

## 📊 性能参考

### 初始化时间（元数据同步）

| Artifacts 数量 | 元数据大小 | 预计时间 | 网速 100Mbps |
|---------------|----------|---------|-------------|
| 10 | ~10MB | 30秒 | ✅ 很快 |
| 50 | ~50MB | 2分钟 | ✅ 快 |
| 200 | ~200MB | 5分钟 | ✅ 可接受 |
| 1000 | ~1GB | 20分钟 | ⚠️ 需耐心 |

### 下载时间（实际文件）

| 文件大小 | 网速 10Mbps | 网速 100Mbps | 网速 1Gbps |
|---------|------------|-------------|-----------|
| 100MB | 80秒 | 8秒 | <1秒 |
| 1GB | 13分钟 | 80秒 | 8秒 |
| 8GB | 1.7小时 | 10分钟 | 1分钟 |
| 50GB | 11小时 | 1.1小时 | 6分钟 |

---

## 💡 最佳实践

### 实践1：合理的同步间隔

- **训练频繁**（每小时新实验）: 5-10 分钟
- **训练偶尔**（每天几个实验）: 30-60 分钟
- **只查看**（不训练新实验）: 关闭自动同步

### 实践2：选择性下载

不要下载所有 artifacts，只下载需要的：
- ✅ 需要使用的模型
- ✅ 需要分析的数据
- ❌ 已废弃的旧版本
- ❌ 仅供参考的备份

### 实践3：定期清理缓存

缓存会自动 LRU 清理，但也可以手动：
- 清理旧下载: `POST /api/remote/cache/cleanup`
- 完全清空: `POST /api/remote/cache/clear`

### 实践4：使用别名管理

为重要版本设置别名：
```bash
# 设置生产版本
curl -X POST .../artifacts/resnet50/v10/alias \
  -d '{"alias": "production"}'

# 下次使用
run.use_artifact("resnet50:production")
```

---

## 📱 UI 功能说明

### 远程配置页面

**位置**: 菜单 → 远程存储

**功能**:
- ⚙️ 配置 SSH 连接
- 🔌 连接/断开服务器
- 🔄 手动同步元数据
- 📊 查看同步进度
- ℹ️ 功能说明和帮助

### 状态指示器

**位置**: Header 右侧

**显示**:
- 本地模式: `[本地]` (灰色徽章)
- 远程模式: `[远程 🌩️]` (绿色徽章)
- 同步中: `[远程 🌩️ 🔄]` (蓝色动画)

**点击后**:
- 查看详细状态
- 快捷同步操作
- 快捷断开连接

### Artifacts 页面

**远程模式特点**:
- 列表显示远程 artifacts
- 点击查看详情（从缓存，秒级）
- 文件列表标记 `is_remote: true`
- 下载按钮替代"打开文件夹"

### 下载进度弹窗

**显示内容**:
- 📊 实时进度条
- 📁 文件数量统计
- 💾 字节数量统计
- ⏱️ 预计剩余大小
- 📍 下载保存位置
- ⚠️ 错误信息（如有）

**操作**:
- ⏹️ 取消下载
- 📁 查看下载位置
- ➖ 最小化窗口

---

## 🔄 工作流示例

### 场景1：查看训练结果

```
目标: 查看今天训练的模型性能

步骤:
1. 打开 Runicorn Viewer
2. Header 显示"远程 🌩️"（已自动同步）
3. 点击 "Artifacts" → 看到所有模型
4. 点击 "resnet50" → 查看详情
5. 查看元数据: {"accuracy": 0.95, "loss": 0.05}
6. 查看版本历史: v1, v2, v3 (最新)
7. 查看血缘图: 了解依赖关系

耗时: <1分钟（全部从缓存）
下载: 0 字节
```

### 场景2：下载模型进行推理

```
目标: 下载最新模型到本地进行推理

步骤:
1. 在 artifact 详情页
2. 点击"下载到本地 (8.00 GB)"
3. 等待10分钟下载
4. 下载完成，得到路径
5. 在推理脚本中加载:
   model = torch.load('/path/to/downloaded/model.pth')

耗时: 10分钟
下载: 8 GB（一次性）
```

### 场景3：清理旧版本

```
目标: 删除服务器上的旧模型释放空间

步骤:
1. 浏览 artifacts
2. 查看版本历史: v1(旧), v2(旧), v3(最新)
3. 选择 v1，点击"删除版本"
4. 确认（提示：远程服务器执行）
5. 2秒后完成
6. 服务器上 v1 已删除，空间释放

耗时: <5秒
效果: 释放8GB服务器空间
```

---

## 🎓 深入理解

### 元数据 vs 大文件

**元数据**（会同步）:
- `versions.json` - artifact 版本索引
- `metadata.json` - artifact 元信息
- `manifest.json` - 文件清单
- `meta.json`, `status.json`, `summary.json` - 实验元数据

**大文件**（不同步，按需下载）:
- `model.pth` - 模型权重文件
- `dataset/*` - 数据集文件
- `media/*` - 图片、视频

### 缓存结构

```
~/.runicorn_remote_cache/{host}_{user}/
├── index.db                    # SQLite 索引
├── metadata/                   # 缓存的元数据
│   ├── artifacts/
│   │   ├── model/
│   │   │   └── resnet50/
│   │   │       ├── versions.json
│   │   │       ├── v1/metadata.json
│   │   │       └── v2/metadata.json
│   │   └── dataset/...
│   └── experiments/...
└── downloads/                  # 下载的文件
    └── resnet50/
        └── v3/
            └── model.pth       # 实际模型文件
```

### 数据流

**浏览时**:
```
UI → API → RemoteAdapter → LocalCache → SQLite/JSON
                                          ↓
                                    <100ms 响应
```

**下载时**:
```
UI → API → RemoteAdapter → FileFetcher → SFTP
                                          ↓
                                    实时进度反馈
                                          ↓
                                    本地文件系统
```

**管理时**:
```
UI → API → RemoteAdapter → RemoteExecutor → SSH
                                          ↓
                                    服务器执行
                                          ↓
                                    自动同步元数据
```

---

## 📚 相关资源

### 文档

- **快速开始**: 查看项目文档
- **集成指南**: 查看开发者文档  
- **API 参考**: 查看 API 文档

### API 文档

- **Swagger UI**: `http://localhost:23300/docs`
- **OpenAPI JSON**: `http://localhost:23300/openapi.json`

### 示例代码

- **Python 示例**: `examples/remote_storage_demo.py`
- **API 测试**: Swagger UI 中在线测试

---

## 🎉 开始使用！

**立即体验远程存储的便利**:

1. ⚙️ 配置 SSH 连接（2分钟）
2. 🔄 同步元数据（5分钟）
3. 📊 浏览 artifacts（秒级）
4. 📥 按需下载文件（按需）
5. 🗑️ 管理远程 artifacts（2秒）

**总用时**: 10-15 分钟即可完全上手

**收益**: 
- 节省时间 **96倍**
- 节省空间 **99.94%**
- 提升体验 **∞**

---

**文档版本**: v1.0  
**更新日期**: 2025-10-03  
**适用版本**: Runicorn v0.5.0+ (Remote Storage)

