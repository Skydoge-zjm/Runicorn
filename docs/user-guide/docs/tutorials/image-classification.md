# Tutorial: Image Classification with PyTorch

Learn how to track a complete image classification experiment using Runicorn with PyTorch and CIFAR-10.

**What you'll learn**:

- ✅ Track training progress
- ✅ Log images and visualizations
- ✅ Snapshot workspace with code versioning
- ✅ Compare multiple runs
- ✅ Export results

**Time**: ~30 minutes

---

## Prerequisites

Install required packages:

```bash
pip install runicorn torch torchvision matplotlib
```

---

## Step 1: Setup and Initialization

```python
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
from PIL import Image
import numpy as np
import runicorn as rn

# Initialize experiment
run = rn.init(
    path="image_classification/cifar10_resnet18",
    snapshot_code=True,     # Snapshot workspace code
    capture_console=True    # Capture console output
)

# Console header
print("=" * 50)
print("CIFAR-10 Classification with ResNet18")
print("=" * 50)

# Set primary metric
run.set_primary_metric("test_accuracy", mode="max")

# Log hyperparameters
hyperparams = {
    "model": "ResNet18",
    "dataset": "CIFAR-10",
    "batch_size": 128,
    "learning_rate": 0.001,
    "optimizer": "Adam",
    "epochs": 50
}

run.log_config(extra=hyperparams)
print(f"Hyperparameters: {hyperparams}")
```

---

## Step 2: Prepare Data

```python
# Data transforms
transform_train = transforms.Compose([
    transforms.RandomCrop(32, padding=4),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])

transform_test = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])

# Load CIFAR-10
trainset = torchvision.datasets.CIFAR10(
    root='./data', train=True, download=True, transform=transform_train
)
trainloader = torch.utils.data.DataLoader(
    trainset, batch_size=128, shuffle=True, num_workers=2
)

testset = torchvision.datasets.CIFAR10(
    root='./data', train=False, download=True, transform=transform_test
)
testloader = torch.utils.data.DataLoader(
    testset, batch_size=128, shuffle=False, num_workers=2
)

print(f"Training samples: {len(trainset)}")
print(f"Test samples: {len(testset)}")
```

---

## Step 3: Define Model

```python
from torchvision.models import resnet18

# Create model
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = resnet18(num_classes=10)
model = model.to(device)

# Log model info
total_params = sum(p.numel() for p in model.parameters())
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

print(f"Model: ResNet18")
print(f"Total parameters: {total_params:,}")
print(f"Trainable parameters: {trainable_params:,}")
print(f"Device: {device}")

# Criterion and optimizer
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50)
```

---

## Step 4: Training Loop with Logging

```python
import time

best_test_acc = 0.0
latest_test_loss = 0.0
latest_test_accuracy = 0.0
latest_epoch_time = 0.0
training_start = time.time()

for epoch in range(50):
    epoch_start = time.time()
    
    # ===== Training Phase =====
    model.train()
    train_loss = 0.0
    train_correct = 0
    train_total = 0
    
    for batch_idx, (inputs, targets) in enumerate(trainloader):
        inputs, targets = inputs.to(device), targets.to(device)
        
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()
        
        train_loss += loss.item()
        _, predicted = outputs.max(1)
        train_total += targets.size(0)
        train_correct += predicted.eq(targets).sum().item()
        
        # Log once per training step (one optimizer update == one step)
        run.log({
            "batch_loss": loss.item(),
            "batch_acc": 100.0 * predicted.eq(targets).sum().item() / targets.size(0),
            "train_loss": loss.item(),
            "train_accuracy": 100.0 * predicted.eq(targets).sum().item() / targets.size(0),
            "test_loss": latest_test_loss,
            "test_accuracy": latest_test_accuracy,
            "learning_rate": optimizer.param_groups[0]['lr'],
            "epoch_time": latest_epoch_time,
        }, stage=f"epoch_{epoch+1}")

        if batch_idx % 50 == 0:
            print(
                f"Epoch {epoch+1} Batch {batch_idx}: "
                f"loss={loss.item():.4f}, "
                f"acc={100.0 * predicted.eq(targets).sum().item() / targets.size(0):.2f}%"
            )
    
    train_loss = train_loss / len(trainloader)
    train_acc = 100.0 * train_correct / train_total
    
    # ===== Validation Phase =====
    model.eval()
    test_loss = 0.0
    test_correct = 0
    test_total = 0
    
    with torch.no_grad():
        for inputs, targets in testloader:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            
            test_loss += loss.item()
            _, predicted = outputs.max(1)
            test_total += targets.size(0)
            test_correct += predicted.eq(targets).sum().item()
    
    test_loss = test_loss / len(testloader)
    test_acc = 100.0 * test_correct / test_total
    
    # ===== Update Latest Eval Snapshot =====
    epoch_time = time.time() - epoch_start
    latest_test_loss = test_loss
    latest_test_accuracy = test_acc
    latest_epoch_time = epoch_time
    current_lr = optimizer.param_groups[0]['lr']
    
    # Console progress (captured because capture_console=True)
    print(
        f"Epoch {epoch+1}/50: "
        f"train_loss={train_loss:.4f}, train_acc={train_acc:.2f}%, "
        f"test_loss={test_loss:.4f}, test_acc={test_acc:.2f}%, "
        f"lr={current_lr:.6f}, time={epoch_time:.1f}s"
    )
    
    # Save checkpoint if best
    if test_acc > best_test_acc:
        best_test_acc = test_acc
        
        # Save checkpoint
        checkpoint_path = f"checkpoint_best.pth"
        torch.save({
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'test_accuracy': test_acc,
        }, checkpoint_path)
        
        print(f"✓ New best accuracy: {test_acc:.2f}%")
    
    # Update learning rate
    scheduler.step()

print("Training completed!")
```

---

## Step 5: Save Model and Summary

```python
# Save final model
final_model_path = "resnet18_cifar10_final.pth"
torch.save(model.state_dict(), final_model_path)

print(f"✓ Model saved to {final_model_path}")

# Save final summary
run.summary({
    "final_test_accuracy": test_acc,
    "best_test_accuracy": best_test_acc,
    "total_epochs": 50,
    "total_training_time": time.time() - training_start,
    "model_path": final_model_path
})

run.finish()
print(f"\n✓ Experiment completed: {run.id}")
print(f"✓ View results: http://127.0.0.1:23300/runs/{run.id}")
```

---

## Step 6: View Results

### Start Viewer

```bash
runicorn viewer
```

### Explore Your Results

1. **Experiments Page**: Find your run "cifar10_resnet18"
2. **Click to view details**:
   - Training/test loss curves
   - Accuracy progression
   - Learning rate schedule
   - Real-time logs
3. **Assets tab**: See workspace code snapshot
4. **Summary**: View saved model path and best metrics

---

## Step 7: Use Saved Model

Create a new script `inference.py`:

```python
import torch
from torchvision.models import resnet18

# Load model directly
model = resnet18(num_classes=10)
state_dict = torch.load("resnet18_cifar10_final.pth")
model.load_state_dict(state_dict)
model.eval()

print("✓ Model loaded successfully")

# Run inference
# ... your inference code ...
```

---

## Next Steps

### Compare Experiments

Run the same experiment with different hyperparameters:

```python
# Experiment 1: Baseline
run1 = rn.init(path="image_classification/resnet18_lr0-001", alias="baseline")
# ... training with lr=0.001 ...
run1.finish()

# Experiment 2: Higher learning rate
run2 = rn.init(path="image_classification/resnet18_lr0-01", alias="high-lr")
# ... training with lr=0.01 ...
run2.finish()
```

Then compare in Web UI:
1. Go to experiment detail page
2. Select multiple runs
3. View overlaid charts

### Try Different Models

```python
# ResNet34
run = rn.init(path="image_classification/cifar10_resnet34", alias="resnet34")
model = torchvision.models.resnet34(num_classes=10)
# ... training ...
run.finish()

# EfficientNet
run = rn.init(path="image_classification/cifar10_efficientnet", alias="efficientnet")
model = torchvision.models.efficientnet_b0(num_classes=10)
# ... training ...
run.finish()
```

---

<div class="rn-page-nav">
  <a href="../../reference/faq/">FAQ →</a> &middot;
  <a href="../../sdk/overview/">Python SDK →</a>
</div>

