# Runicorn 用户指南

**目录**: `docs/guides/`  
**用途**: 实用的用户指南和工作流文档

---

## 📚 指南列表

### 🚀 快速开始

#### [QUICKSTART_REMOTE_TRAINING.md](./QUICKSTART_REMOTE_TRAINING.md) ⭐
**5 分钟快速上手**

适合：首次使用 Runicorn 的用户

内容：
- 3 步开始远程训练监控
- 最简单的配置方式
- 常见场景示例
- 快速故障排除

**推荐**: 所有新用户先看这个！

---

### 📊 完整工作流

#### [REALTIME_MONITORING_WORKFLOW.md](./REALTIME_MONITORING_WORKFLOW.md) ⭐
**完整的端到端工作流指南**

适合：需要详细了解完整流程的用户

内容：
- 完整的系统架构图
- 详细的步骤说明
- 服务器端和客户端配置
- 高级用法和最佳实践
- 完整的故障排除
- 真实场景案例

**推荐**: 深度使用 Runicorn 必读

---

## 🎯 按需求选择

### 我是新用户

**推荐路径**:
1. ✅ [QUICKSTART_REMOTE_TRAINING.md](./QUICKSTART_REMOTE_TRAINING.md) (5 分钟)
2. 开始使用
3. 遇到问题时查看 [REALTIME_MONITORING_WORKFLOW.md](./REALTIME_MONITORING_WORKFLOW.md)

### 我要部署到生产

**推荐路径**:
1. ✅ [REALTIME_MONITORING_WORKFLOW.md](./REALTIME_MONITORING_WORKFLOW.md)
2. ✅ [../future/SERVER_SETUP_GUIDE.md](../future/SERVER_SETUP_GUIDE.md)
3. ✅ [../api/zh/manifest_api.md](../api/zh/manifest_api.md)

### 我要优化性能

**推荐路径**:
1. ✅ [../api/zh/manifest_api.md](../api/zh/manifest_api.md) - Manifest Sync
2. ✅ [../future/PHASE2_COMPLETE_SUMMARY.md](../future/PHASE2_COMPLETE_SUMMARY.md) - 性能指标

### 我遇到了问题

**推荐路径**:
1. ✅ [REALTIME_MONITORING_WORKFLOW.md#故障排除](./REALTIME_MONITORING_WORKFLOW.md#故障排除)
2. ✅ [../api/zh/manifest_api.md#故障排除](../api/zh/manifest_api.md#故障排除)

---

## 📖 其他文档

### API 文档
- [../api/zh/README.md](../api/zh/README.md) - API 总览
- [../api/zh/manifest_api.md](../api/zh/manifest_api.md) - Manifest API
- [../api/zh/ssh_api.md](../api/zh/ssh_api.md) - SSH API

### 技术文档
- [../future/](../future/) - 实现计划和技术细节
- [../PROJECT_COMPLETION_SUMMARY.md](../PROJECT_COMPLETION_SUMMARY.md) - 项目总结

---

## 🔥 热门话题

### 如何在本地实时查看远程训练？

👉 [QUICKSTART_REMOTE_TRAINING.md](./QUICKSTART_REMOTE_TRAINING.md)

### 如何提升同步速度？

👉 [../api/zh/manifest_api.md](../api/zh/manifest_api.md) - 启用 Manifest Sync

### 如何对比多个实验？

👉 [REALTIME_MONITORING_WORKFLOW.md#对比多个实验](./REALTIME_MONITORING_WORKFLOW.md#步骤-3-实时查看指标)

### 如何在多台服务器间切换？

👉 [REALTIME_MONITORING_WORKFLOW.md#监控多个服务器](./REALTIME_MONITORING_WORKFLOW.md#监控多个服务器)

---

## 💡 使用技巧

### 技巧 1: 使用有意义的实验名称

```python
# ❌ 不好
run = runicorn.init(project="test", name="exp1")

# ✅ 好
run = runicorn.init(
    project="image_classification",
    name="resnet50_lr0.001_bs32",
    tags=["baseline", "production"]
)
```

### 技巧 2: 记录完整的配置

```python
run = runicorn.init(...)
run.config.update({
    "model": "resnet50",
    "learning_rate": 0.001,
    "batch_size": 32,
    "optimizer": "Adam",
    # ... 所有超参数
})
```

### 技巧 3: 使用 tmux 保持训练

```bash
# 启动训练会话
tmux new -s training
python train.py

# Detach (训练继续运行)
Ctrl+B, then D

# 重新连接
tmux attach -t training
```

### 技巧 4: 启用 Manifest Sync

```bash
# 服务器端一次性设置
crontab -e
# 添加: */5 * * * * cd ~/experiments && runicorn generate-manifest

# 客户端自动使用（无需配置）
```

---

## 🎓 学习路径

### 初级（第 1 天）

1. ✅ 阅读 [QUICKSTART_REMOTE_TRAINING.md](./QUICKSTART_REMOTE_TRAINING.md)
2. ✅ 在本地安装 Runicorn
3. ✅ 尝试运行一个简单的训练脚本
4. ✅ 配置 SSH 连接
5. ✅ 在浏览器中查看实验

**目标**: 能够进行基本的远程训练监控

### 中级（第 2-3 天）

1. ✅ 阅读 [REALTIME_MONITORING_WORKFLOW.md](./REALTIME_MONITORING_WORKFLOW.md)
2. ✅ 理解完整的工作流
3. ✅ 配置 Manifest Sync
4. ✅ 对比多个实验
5. ✅ 使用标签和项目组织实验

**目标**: 熟练使用所有核心功能

### 高级（第 4-7 天）

1. ✅ 阅读 [../api/zh/manifest_api.md](../api/zh/manifest_api.md)
2. ✅ 优化服务器端配置
3. ✅ 自定义同步策略
4. ✅ 集成到团队工作流
5. ✅ 性能调优

**目标**: 深度定制和优化使用体验

---

## 📞 获取帮助

### 问题排查顺序

1. **查看快速开始**: [QUICKSTART_REMOTE_TRAINING.md#故障排除](./QUICKSTART_REMOTE_TRAINING.md#故障排除)
2. **查看完整故障排除**: [REALTIME_MONITORING_WORKFLOW.md#故障排除](./REALTIME_MONITORING_WORKFLOW.md#故障排除)
3. **查看 API 文档**: [../api/zh/](../api/zh/)
4. **提交 Issue**: GitHub Issues

### 常见问题 FAQ

**Q: Runicorn 支持哪些 ML 框架？**  
A: 支持所有 Python ML 框架（PyTorch, TensorFlow, JAX, scikit-learn 等）

**Q: 需要修改很多代码吗？**  
A: 只需添加 3-5 行代码即可

**Q: 同步会影响训练速度吗？**  
A: 不会。数据异步写入，对训练无影响

**Q: 支持多用户吗？**  
A: 当前版本支持个人使用，团队功能在路线图中

**Q: 数据存储在哪里？**  
A: 本地缓存在 `~/.runicorn/cache/`

---

## 🚀 开始使用

选择一个指南，开始你的 Runicorn 之旅：

- **新用户**: 👉 [QUICKSTART_REMOTE_TRAINING.md](./QUICKSTART_REMOTE_TRAINING.md)
- **深度用户**: 👉 [REALTIME_MONITORING_WORKFLOW.md](./REALTIME_MONITORING_WORKFLOW.md)

**Happy Training! 🎉**

---

**最后更新**: 2025-10-23  
**维护者**: Runicorn 开发团队
