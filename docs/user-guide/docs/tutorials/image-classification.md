# Tutorial: Image Classification with PyTorch

Learn how to track a complete image classification experiment using Runicorn with PyTorch and CIFAR-10.

**What you'll learn**:

- ✅ Track training progress
- ✅ Log images and visualizations
- ✅ Save model checkpoints as artifacts
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
import runicorn as rn
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
from PIL import Image
import numpy as np

# Initialize experiment
run = rn.init(
    project="image_classification",
    name="cifar10_resnet18",
    capture_env=True  # Capture Git, packages, system info
)

# Log configuration
rn.log_text("="*50)
rn.log_text("CIFAR-10 Classification with ResNet18")
rn.log_text("="*50)

# Set primary metric
rn.set_primary_metric("test_accuracy", mode="max")

# Log hyperparameters
hyperparams = {
    "model": "ResNet18",
    "dataset": "CIFAR-10",
    "batch_size": 128,
    "learning_rate": 0.001,
    "optimizer": "Adam",
    "epochs": 50
}

rn.summary(hyperparams)
rn.log_text(f"Hyperparameters: {hyperparams}")
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

rn.log_text(f"Training samples: {len(trainset)}")
rn.log_text(f"Test samples: {len(testset)}")
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

rn.log_text(f"Model: ResNet18")
rn.log_text(f"Total parameters: {total_params:,}")
rn.log_text(f"Trainable parameters: {trainable_params:,}")
rn.log_text(f"Device: {device}")

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
        
        # Log every 50 batches
        if batch_idx % 50 == 0:
            rn.log({
                "batch_loss": loss.item(),
                "batch_acc": 100.0 * predicted.eq(targets).sum().item() / targets.size(0)
            }, stage="train")
    
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
    
    # ===== Log Epoch Metrics =====
    epoch_time = time.time() - epoch_start
    current_lr = optimizer.param_groups[0]['lr']
    
    rn.log({
        "train_loss": train_loss,
        "train_accuracy": train_acc,
        "test_loss": test_loss,
        "test_accuracy": test_acc,
        "learning_rate": current_lr,
        "epoch_time": epoch_time
    }, step=epoch + 1, stage="epoch")
    
    # Log progress
    rn.log_text(
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
        
        rn.log_text(f"✓ New best accuracy: {test_acc:.2f}%")
    
    # Update learning rate
    scheduler.step()

rn.log_text("Training completed!")
```

---

## Step 5: Save Model as Artifact

```python
# Save final model
final_model_path = "resnet18_cifar10_final.pth"
torch.save(model.state_dict(), final_model_path)

# Create artifact
artifact = rn.Artifact("cifar10-resnet18", type="model")
artifact.add_file(final_model_path)
artifact.add_metadata({
    "architecture": "ResNet18",
    "dataset": "CIFAR-10",
    "num_classes": 10,
    "input_size": "32x32",
    "final_test_accuracy": test_acc,
    "best_test_accuracy": best_test_acc,
    "total_epochs": 50,
    "optimizer": "Adam",
    "learning_rate": 0.001
})
artifact.add_tags("baseline", "resnet18", "cifar10")

version = run.log_artifact(artifact)
rn.log_text(f"✓ Model saved as artifact v{version}")

# Save final summary
rn.summary({
    "final_test_accuracy": test_acc,
    "best_test_accuracy": best_test_acc,
    "total_epochs": 50,
    "total_training_time": time.time() - epoch_start,
    "model_artifact": f"cifar10-resnet18:v{version}"
})

rn.finish()
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
3. **Artifacts tab**: See your saved model
4. **Download model**: Click on artifact to download

---

## Step 7: Use Saved Model

Create a new script `inference.py`:

```python
import runicorn as rn
import torch
from torchvision.models import resnet18
from PIL import Image
import torchvision.transforms as transforms

# Initialize inference run
run = rn.init(project="image_classification", name="inference")

# Load model artifact
artifact = run.use_artifact("cifar10-resnet18:latest")
model_dir = artifact.download()

# Load model
model = resnet18(num_classes=10)
state_dict = torch.load(model_dir / "resnet18_cifar10_final.pth")
model.load_state_dict(state_dict)
model.eval()

print(f"✓ Loaded model: {artifact.full_name}")
print(f"  Accuracy: {artifact.get_metadata().metadata['final_test_accuracy']:.2f}%")

# Run inference
# ... your inference code ...

rn.finish()
```

---

## Next Steps

### Compare Experiments

Run the same experiment with different hyperparameters:

```python
# Experiment 1: Baseline
run1 = rn.init(project="image_classification", name="resnet18_lr0.001")
# ... training with lr=0.001 ...

# Experiment 2: Higher learning rate
run2 = rn.init(project="image_classification", name="resnet18_lr0.01")
# ... training with lr=0.01 ...
```

Then compare in Web UI:
1. Go to experiment detail page
2. Select multiple runs
3. View overlaid charts

### Try Different Models

```python
# ResNet34
run = rn.init(project="image_classification", name="cifar10_resnet34")
model = torchvision.models.resnet34(num_classes=10)
# ... training ...

# EfficientNet
run = rn.init(project="image_classification", name="cifar10_efficientnet")
model = torchvision.models.efficientnet_b0(num_classes=10)
# ... training ...
```

---

## Full Code

Download complete example:

```bash
# Clone repository
git clone https://github.com/yourusername/runicorn.git

# Run example
cd runicorn/examples
python image_classification_tutorial.py
```

Or view on GitHub: [image_classification_tutorial.py](https://github.com/yourusername/runicorn/blob/main/examples/image_classification_tutorial.py)

---

## Related Tutorials

- More tutorials coming soon
- Check back for NLP, multi-GPU, and other advanced tutorials

---

<div align="center">
  <p><strong>Ready for more?</strong></p>
  <p><a href="../reference/faq.md">Check FAQ →</a></p>
</div>

