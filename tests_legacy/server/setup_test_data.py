#!/usr/bin/env python3
"""
Setup Test Data for Remote Viewer Testing

Creates sample experiments in WSL for testing Remote Viewer functionality.
"""
import os
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import runicorn as rn


def create_test_experiments(root_dir: str = "~/runicorn_test_data"):
    """Create sample experiments for testing."""
    root = Path(root_dir).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    
    print(f"📦 Creating test data in: {root}")
    
    # Set environment variable for runicorn
    os.environ["RUNICORN_DIR"] = str(root)
    
    # Create 3 sample experiments
    experiments = [
        {
            "project": "vision",
            "name": "resnet50_training",
            "metrics": {
                "train_loss": [2.5, 2.1, 1.8, 1.5, 1.2, 1.0, 0.8],
                "val_loss": [2.6, 2.2, 1.9, 1.6, 1.4, 1.2, 1.1],
                "accuracy": [0.65, 0.72, 0.78, 0.82, 0.85, 0.87, 0.89],
            },
            "config": {
                "model": "resnet50",
                "batch_size": 32,
                "learning_rate": 0.001,
                "epochs": 50,
            }
        },
        {
            "project": "nlp",
            "name": "bert_finetuning",
            "metrics": {
                "train_loss": [1.8, 1.5, 1.2, 1.0, 0.8, 0.6],
                "val_loss": [1.9, 1.6, 1.3, 1.1, 0.9, 0.7],
                "f1_score": [0.70, 0.75, 0.80, 0.83, 0.85, 0.87],
            },
            "config": {
                "model": "bert-base-uncased",
                "batch_size": 16,
                "learning_rate": 2e-5,
                "max_seq_length": 512,
            }
        },
        {
            "project": "reinforcement",
            "name": "dqn_cartpole",
            "metrics": {
                "episode_reward": [20, 35, 50, 80, 120, 180, 200],
                "loss": [0.5, 0.4, 0.3, 0.25, 0.2, 0.18, 0.15],
            },
            "config": {
                "algorithm": "DQN",
                "gamma": 0.99,
                "epsilon": 0.1,
                "replay_buffer_size": 10000,
            }
        }
    ]
    
    created_runs = []
    
    for exp in experiments:
        print(f"\n🔬 Creating experiment: {exp['project']}/{exp['name']}")
        
        # Initialize run
        run = rn.init(
            project=exp["project"],
            name=exp["name"]
        )
        
        # Log metrics
        metric_names = list(exp["metrics"].keys())
        max_steps = max(len(values) for values in exp["metrics"].values())
        
        for step in range(max_steps):
            time.sleep(0.1)  # Simulate training time
            metrics = {}
            for metric_name, values in exp["metrics"].items():
                if step < len(values):
                    metrics[metric_name] = values[step]
            
            # Add config info to first step only
            if step == 0:
                metrics.update(exp["config"])
            
            run.log(metrics, step=step)
            print(f"  Step {step}: {metrics}")
        
        # Add summary using summary() method
        run.summary({
            "best_metric": max(exp["metrics"][metric_names[0]]),
            "total_steps": max_steps,
            "status": "completed",
        })
        
        # Finish run
        run.finish()
        
        created_runs.append({
            "project": exp["project"],
            "name": exp["name"],
            "run_id": run.id,
        })
        
        print(f"  ✅ Run created: {run.id}")
    
    print(f"\n✅ Created {len(created_runs)} test experiments")
    print(f"📂 Data location: {root}")
    print("\n📋 Created runs:")
    for r in created_runs:
        print(f"  - {r['project']}/{r['name']}: {r['run_id']}")
    
    return root, created_runs


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup test data for Remote Viewer")
    parser.add_argument(
        "--root",
        default="~/runicorn_test_data",
        help="Root directory for test data (default: ~/runicorn_test_data)"
    )
    args = parser.parse_args()
    
    try:
        root, runs = create_test_experiments(args.root)
        print("\n" + "="*60)
        print("🎉 Test data setup complete!")
        print("="*60)
        print(f"\nNext steps:")
        print(f"1. Start remote viewer:")
        print(f"   python -m runicorn viewer --root {root} --remote-mode --port 8080")
        print(f"\n2. Run client tests from Windows:")
        print(f"   python tests/client/test_remote_viewer_connection.py")
    except Exception as e:
        print(f"\n❌ Error creating test data: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
