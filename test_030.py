# 或在Python中：
import runicorn as rn

# 生成测试实验
run = rn.init(project="test_project", name="experiment_1", capture_env=True)
print(f"Created run: id={run.id} dir={run.run_dir}")
run.log_text(f"[info] Starting dummy run '{run.name}' (project={run.project})")

# 设置主要指标为准确率（最大化）
run.set_primary_metric("accuracy_123", mode="max")

if hasattr(run, 'MetricsExporter'):
    exporter = rn.MetricsExporter(run.run_dir)
    
# 模拟训练
import random
import math
import time
for epoch in range(200):
    # 模拟指标
    time.sleep(1)
    
    # 测试异常处理：取消注释下行来模拟程序崩溃
    # if epoch == 50: raise ValueError("Test crash")
    
    loss = 2.0 * math.exp(-epoch/20) + random.random() * 0.1 if epoch < 500 else float('nan')
    #loss = 2.0 * math.exp(-epoch/20) + random.random() * 0.1
    acc = 100 * (1 - math.exp(-epoch/30)) + random.random() * 2
    
    # 记录指标
    run.log({
        "loss_": loss,
        "accuracy_": acc,
        "learning_rate_": 0.001 * (0.95 ** epoch),
    }, stage=f"epoch {epoch // 10}")
    run.log_text(f"epoch {epoch // 10} | loss {loss:.4f} | accuracy {acc:.2f}")
    print(f"epoch {epoch // 10} | loss {loss:.4f} | accuracy {acc:.2f}")



# 记录摘要（best metric会自动记录）
run.summary({
    "final_loss": 0.05,
    "total_epochs": 100,
    "notes": "Demo run with auto-tracked accuracy metric"
})
run.log_text("[info] Summary metrics recorded")
run.log_text("[info] Run finished successfully with auto-tracked best metrics.")

run.finish()