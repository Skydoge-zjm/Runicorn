# v0.7.0 发布说明

**发布日期**: 2026-03

---

## 概览

v0.7.0 是 Runicorn 在 v0.6.0 之后的下一条发布线。当前开发分支的重点主要集中在三个方向：

1. 强化 Remote Viewer 的真实使用稳定性
2. 将 Web UI 打磨成更适合日常使用的产品界面
3. 扩展对常见训练日志与兼容写法的支持

---

## 主要更新

### Remote Viewer

- 新的模态式远程向导，步骤更清晰
- 更快的环境探测与批量 Runicorn 检查
- 在 UI 中确认 Host Key
- 会话健康监控，以及重连/降级状态展示
- 更合理的 Stop 行为与 SSH 清理
- 支持 OpenSSH 密码认证

### Web UI

- 更专业化的默认主题
- 更完善的路径树与文件夹操作
- 基于 URL 的对比模式与更顺手的对比体验
- ZIP 导出，以及带冲突预览的导入流程
- 统一的回收站模型
- 更一致的暗色模式与弹窗主题

### 日志、主题与监控

- 大日志场景下的虚拟滚动
- 更合理的日志布局与自动滚动体验
- 主题预设与 surface color 控制
- 后端采集的 GPU 遥测历史

### SDK 与日志兼容

- 新增 ImageNet 风格 meter 兼容
- 新增 TensorBoard SummaryWriter 兼容
- 新增 tensorboardX 兼容
- 更安全的 finish 和输出监控清理逻辑

### 桌面端

- 当前桌面构建可为远程会话打开原生窗口
- 外部链接可以交给系统浏览器打开

---

## 升级说明

### 如果你从 v0.6.0 升级

最明显的用户可见变化有：

- Remote Viewer 更完整也更稳定
- experiments、compare、import/export、recycle bin 的交互都发生了变化
- settings 与主题能力明显增强
