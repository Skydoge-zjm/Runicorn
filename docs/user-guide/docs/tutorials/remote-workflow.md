# Remote Workflow

This tutorial walks through a practical laptop-to-server workflow using the current Remote Viewer stack.

---

## Scenario

You train on a remote GPU machine but want to browse runs from your local machine without syncing the whole storage directory.

---

## 1. Prepare the remote machine

Install Runicorn into the Python environment you actually train with:

```bash
conda activate train-env
pip install runicorn
```

Write runs into a stable remote storage root:

```python
import runicorn as rn

run = rn.init(
    path="remote-demo/resnet50",
    storage="/data/runicorn",
    alias="seed-42",
)

run.log_config(extra={"machine": "gpu-server-01", "epochs": 3})

latest_val_acc = 0.0

for epoch in range(1, 4):
    for _ in range(5):
        run.log({
            "train_loss": 1.0 / epoch,
            "val_acc": latest_val_acc,
        }, stage=f"epoch_{epoch}")

    latest_val_acc = 0.70 + 0.05 * epoch

run.summary({
    "final_val_acc": latest_val_acc,
    "remote_root": "/data/runicorn",
})

run.finish()
```

---

## 2. Start local browsing

On your local machine:

```bash
runicorn viewer
```

Open the **Remote** page.

---

## 3. Add the server and connect

Create a saved server entry, authenticate, confirm the host key if prompted, and choose the remote environment.

---

## 4. Start the remote session

After the session starts, the remote runs appear through the forwarded viewer just like local runs.

Watch for statuses such as:

- running
- reconnecting
- degraded

---

## 5. Monitor the training job

Use the normal UI once connected:

- experiments page
- run detail charts
- logs
- images
- assets

---

## 6. Stop cleanly

Use the **Stop** action in the Remote page when you are done. Runicorn 0.7.0 also cleans up the SSH connection when that session is the last one using it.

---

## Next steps

- [Remote Viewer Guide](../getting-started/remote-viewer.md)
- [Desktop App](../reference/desktop-app.md)
- [Troubleshooting](../reference/troubleshooting.md)
