[English](python_client_api.md) | [简体中文](../zh/python_client_api.md)

---

# Python API Client - Programmatic Access

**Module**: Python API Client  
**Package**: `runicorn.api`  
**Version**: v1.0  
**Description**: Programmatic access to Runicorn Viewer REST API through Python code.

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Core Classes](#core-classes)
5. [API Methods](#api-methods)
6. [Extended APIs](#extended-apis)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)
9. [Complete Examples](#complete-examples)

---

## Overview

The Python API Client provides a clean wrapper around the Runicorn Viewer REST API, enabling you to:

- 📊 Query and analyze experiment data
- 📦 Manage Artifact versions
- 🔌 Control Remote Viewer sessions
- 📤 Export data in various formats
- 🐼 Integrate with pandas DataFrames

### Key Features

- ✅ **Type Safe**: Full type hints support
- ✅ **Auto Retry**: Built-in request retry mechanism
- ✅ **Context Manager**: Support `with` statement for automatic cleanup
- ✅ **DataFrame Integration**: Built-in pandas conversion tools
- ✅ **Modular Design**: Artifacts and Remote APIs as independent extensions

---

## Installation

The Python API Client is included in the main Runicorn package:

```bash
# Install Runicorn (includes API Client)
pip install runicorn

# Or install from source
pip install -e .
```

### Dependencies

**Required**:
- `requests` >= 2.25.0
- `urllib3` >= 1.26.0

**Optional**:
- `pandas` >= 1.2.0 (for DataFrame utilities)

```bash
# Install with optional dependencies
pip install "runicorn[pandas]"
```

---

## Quick Start

### Basic Usage

```python
import runicorn.api as api

# Connect to Viewer
client = api.connect("http://127.0.0.1:23300")

# List experiments
experiments = client.list_experiments(project="vision")
print(f"Found {len(experiments)} experiments")

# Get metrics
for exp in experiments[:3]:
    metrics = client.get_metrics(exp["id"])
    print(f"{exp['name']}: {list(metrics['metrics'].keys())}")

# Close connection
client.close()
```

### Using Context Manager

```python
import runicorn.api as api

# Automatically manage connection lifecycle
with api.connect() as client:
    experiments = client.list_experiments()
    # ... use client
# Automatically calls client.close()
```

---

## Core Classes

### RunicornClient

Main client class providing access to Viewer API.

#### Constructor

```python
RunicornClient(
    base_url: str = "http://127.0.0.1:23300",
    timeout: int = 30,
    max_retries: int = 3
)
```

**Parameters**:
- `base_url` (str): Viewer base URL
- `timeout` (int): Request timeout in seconds
- `max_retries` (int): Maximum retry attempts

**Example**:
```python
from runicorn.api import RunicornClient

# Use custom configuration
client = RunicornClient(
    base_url="http://localhost:8080",
    timeout=60,
    max_retries=5
)
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `base_url` | `str` | Viewer base URL |
| `timeout` | `int` | Request timeout |
| `session` | `requests.Session` | HTTP session object |
| `artifacts` | `ArtifactsAPI` | Artifacts API extension |
| `remote` | `RemoteAPI` | Remote API extension |

---

## API Methods

### Experiment Management

#### list_experiments()

List all experiments.

```python
client.list_experiments(
    project: Optional[str] = None,
    name: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> List[Dict[str, Any]]
```

**Parameters**:
- `project`: Filter by project name
- `name`: Filter by experiment name
- `status`: Filter by status (`running`, `finished`, `failed`)
- `limit`: Maximum number of results
- `offset`: Pagination offset

**Returns**: List of experiment records

**Example**:
```python
# List all experiments
all_experiments = client.list_experiments()

# Filter
vision_exps = client.list_experiments(project="vision")
running_exps = client.list_experiments(status="running")

# Pagination
page1 = client.list_experiments(limit=10, offset=0)
page2 = client.list_experiments(limit=10, offset=10)
```

---

#### get_experiment()

Get experiment details.

```python
client.get_experiment(run_id: str) -> Dict[str, Any]
```

**Parameters**:
- `run_id`: Run ID

**Returns**: Detailed experiment information

**Example**:
```python
run = client.get_experiment("20250124_120000_abc123")

print(f"Project: {run['project']}")
print(f"Name: {run['name']}")
print(f"Status: {run['status']}")
print(f"Created: {run['created_at']}")
```

**Alias**: `get_run()`

---

### Metrics Data

#### get_metrics()

Get metrics data for a run.

```python
client.get_metrics(
    run_id: str,
    metric_names: Optional[List[str]] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]
```

**Parameters**:
- `run_id`: Run ID
- `metric_names`: List of specific metric names
- `limit`: Limit number of data points

**Returns**: Metrics data dictionary

**Example**:
```python
# Get all metrics
metrics = client.get_metrics("20250124_120000_abc123")

# Get specific metrics
metrics = client.get_metrics(
    "20250124_120000_abc123",
    metric_names=["loss", "accuracy"]
)

# Process metrics
for metric_name, points in metrics["metrics"].items():
    values = [p["value"] for p in points]
    print(f"{metric_name}: min={min(values)}, max={max(values)}")
```

---

### Configuration

#### get_config()

Get Viewer configuration.

```python
client.get_config() -> Dict[str, Any]
```

**Returns**: Configuration information

---

#### update_config()

Update Viewer configuration.

```python
client.update_config(config: Dict[str, Any]) -> Dict[str, Any]
```

---

### Data Export

#### export_experiment()

Export experiment data.

```python
client.export_experiment(
    run_id: str,
    format: str = "json",
    include_media: bool = False
) -> bytes
```

**Parameters**:
- `run_id`: Run ID
- `format`: Export format (`json`, `csv`)
- `include_media`: Include media files

**Returns**: Exported binary data

**Example**:
```python
# Export as JSON
data = client.export_experiment("run_id", format="json")
with open("experiment.json", "wb") as f:
    f.write(data)

# Export as CSV
data = client.export_experiment("run_id", format="csv")
with open("metrics.csv", "wb") as f:
    f.write(data)
```

---

## Extended APIs

### Artifacts API

Access via `client.artifacts`.

#### list_artifacts()

List all artifacts.

```python
client.artifacts.list_artifacts(
    type: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> List[Dict[str, Any]]
```

**Example**:
```python
# List all artifacts
artifacts = client.artifacts.list_artifacts()

# Filter by type
models = client.artifacts.list_artifacts(type="model")
datasets = client.artifacts.list_artifacts(type="dataset")
```

---

#### get_artifact()

Get artifact details.

```python
client.artifacts.get_artifact(artifact_id: str) -> Dict[str, Any]
```

**Parameters**:
- `artifact_id`: Artifact ID (format: `name:version` or `name:vN`)

**Example**:
```python
artifact = client.artifacts.get_artifact("my-model:v3")

print(f"Name: {artifact['name']}")
print(f"Version: {artifact['version']}")
print(f"Type: {artifact['type']}")
print(f"Size: {artifact['size_bytes'] / 1024 / 1024:.2f} MB")
```

---

### Remote API

Access via `client.remote`.

#### connect()

Establish SSH connection.

```python
client.remote.connect(
    host: str,
    port: int = 22,
    username: str = None,
    password: str = None,
    private_key_path: str = None,
    passphrase: str = None
) -> Dict[str, Any]
```

---

#### start_viewer()

Start remote Viewer.

```python
client.remote.start_viewer(
    connection_id: str,
    remote_root: str,
    local_port: Optional[int] = None,
    remote_port: Optional[int] = None
) -> Dict[str, Any]
```

**Example**:
```python
session = client.remote.start_viewer(
    connection_id="remote-server.com",
    remote_root="/data/runicorn"
)

print(f"Access at: http://localhost:{session['local_port']}")
```

---

## Error Handling

### Exception Hierarchy

```
RunicornAPIError
├── ConnectionError       # Connection failed
├── NotFoundError         # Resource not found (404)
├── BadRequestError       # Invalid parameters (400)
├── ServerError           # Server error (500+)
└── AuthenticationError   # Authentication failed
```

### Example

```python
from runicorn.api import (
    RunicornClient,
    ConnectionError,
    NotFoundError,
    BadRequestError
)

try:
    client = RunicornClient("http://localhost:23300")
    run = client.get_run("nonexistent_id")
    
except ConnectionError as e:
    print(f"Cannot connect to Viewer: {e}")
    print("Make sure Viewer is running: runicorn viewer")
    
except NotFoundError as e:
    print(f"Resource not found: {e}")
    
except BadRequestError as e:
    print(f"Invalid parameters: {e}")
```

---

## Best Practices

### 1. Use Context Manager

```python
# Recommended: Auto resource management
with api.connect() as client:
    experiments = client.list_experiments()
    # ... use client

# Not recommended: Manual management
client = api.connect()
try:
    experiments = client.list_experiments()
finally:
    client.close()
```

### 2. Batch Operations

```python
# Recommended: Batch retrieval
experiments = client.list_experiments()
for exp in experiments:
    metrics = client.get_metrics(exp["id"])
    # ... process

# Not recommended: Frequent reconnection
for i in range(100):
    with api.connect() as client:
        # Creates new connection each time
```

### 3. DataFrame Integration

```python
# Use built-in utilities for DataFrame conversion
from runicorn.api import utils
import pandas as pd

with api.connect() as client:
    # Convert experiments to DataFrame
    experiments = client.list_experiments()
    df_exps = utils.experiments_to_dataframe(experiments)
    
    # Convert metrics to DataFrame
    metrics = client.get_metrics("run_id")
    df_metrics = utils.metrics_to_dataframe(metrics)
    
    # Analysis
    print(df_metrics.describe())
    print(df_exps.groupby("project").size())
```

---

## Complete Examples

### Example 1: Analyze Experiment Performance

```python
import runicorn.api as api

with api.connect() as client:
    # Get all vision experiments
    experiments = client.list_experiments(project="vision")
    
    # Find best experiment
    best_run = None
    best_acc = 0
    
    for exp in experiments:
        metrics = client.get_metrics(exp["id"])
        
        if "accuracy" in metrics["metrics"]:
            acc_points = metrics["metrics"]["accuracy"]
            max_acc = max(p["value"] for p in acc_points)
            
            if max_acc > best_acc:
                best_acc = max_acc
                best_run = exp
    
    if best_run:
        print(f"Best experiment: {best_run['name']}")
        print(f"Accuracy: {best_acc:.2f}%")
```

### Example 2: Export Multiple Experiments

```python
import runicorn.api as api
from pathlib import Path

output_dir = Path("exports")
output_dir.mkdir(exist_ok=True)

with api.connect() as client:
    experiments = client.list_experiments(project="nlp", limit=10)
    
    for exp in experiments:
        # Export as JSON
        data = client.export_experiment(exp["id"], format="json")
        
        # Save file
        filename = f"{exp['name']}_{exp['id']}.json"
        filepath = output_dir / filename
        filepath.write_bytes(data)
        
        print(f"✓ Exported: {filename}")
```

### Example 3: Manage Artifacts

```python
import runicorn.api as api

with api.connect() as client:
    # List all models
    models = client.artifacts.list_artifacts(type="model")
    
    for model in models:
        print(f"\nModel: {model['name']}")
        
        # Get all versions
        versions = client.artifacts.list_versions(model['name'])
        print(f"  Versions: {len(versions)}")
        
        # Show latest version
        latest = versions[0]
        print(f"  Latest: v{latest['version']}")
        print(f"  Size: {latest['size_bytes'] / 1024 / 1024:.2f} MB")
```

---

## Reference

- **REST API Docs**: [README.md](./README.md)
- **SDK Docs**: [../user-guide/docs/sdk/overview.md](../user-guide/docs/sdk/overview.md)
- **Example Code**: `tests/common/test_api_client.py`
- **Source Code**: `src/runicorn/api/`

---

**Last Updated**: 2025-10-24  
**Maintainer**: Runicorn Development Team  
**API Version**: v1.0
