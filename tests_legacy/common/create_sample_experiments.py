#!/usr/bin/env python3
"""
Create Sample Experiments

Creates sample experiments with various metrics for testing.
Similar to test_030.py but more comprehensive.
"""
import sys
import time
import math
import random
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import runicorn as rn


def create_image_classification_experiment():
    """Create a sample image classification experiment."""
    print("\n" + "="*60)
    print("Creating Image Classification Experiment")
    print("="*60)
    
    # Initialize experiment
    run = rn.init(
        project="vision",
        name="resnet50_baseline",
        capture_env=True
    )
    
    print(f"✅ Created run: {run.id}")
    print(f"   Project: {run.project}")
    print(f"   Name: {run.name}")
    print(f"   Dir: {run.run_dir}")
    
    # Log configuration
    run.log({
        "model": "resnet50",
        "dataset": "ImageNet",
        "batch_size": 256,
        "learning_rate": 0.1,
        "optimizer": "SGD",
        "epochs": 100,
        "weight_decay": 0.0001,
        "momentum": 0.9,
    }, step=0)
    
    # Set primary metric
    run.set_primary_metric("val_accuracy", mode="max")
    
    # Simulate training
    print(f"\n📊 Simulating training...")
    for epoch in range(1, 101):
        time.sleep(0.05)  # Simulate training time
        
        # Training metrics (decreasing loss, increasing accuracy)
        train_loss = 2.5 * math.exp(-epoch/20) + random.uniform(-0.1, 0.1)
        train_acc = min(95.0, 60.0 + epoch * 0.35 + random.uniform(-1, 1))
        
        # Validation metrics (similar but slightly worse)
        val_loss = train_loss + random.uniform(0, 0.2)
        val_acc = train_acc - random.uniform(1, 3)
        
        # Learning rate decay
        lr = 0.1 * (0.1 ** (epoch // 30))
        
        # Log metrics
        run.log({
            "train_loss": train_loss,
            "train_accuracy": train_acc,
            "val_loss": val_loss,
            "val_accuracy": val_acc,
            "learning_rate": lr,
        }, step=epoch)
        
        # Log text
        if epoch % 10 == 0:
            run.log_text(
                f"Epoch {epoch:3d} | "
                f"Train Loss: {train_loss:.4f} | "
                f"Train Acc: {train_acc:.2f}% | "
                f"Val Loss: {val_loss:.4f} | "
                f"Val Acc: {val_acc:.2f}%"
            )
            print(f"   Epoch {epoch:3d}/{100} - Val Acc: {val_acc:.2f}%")
    
    # Add summary
    run.summary({
        "best_val_accuracy": 92.5,
        "best_val_loss": 0.25,
        "final_train_accuracy": 95.2,
        "total_epochs": 100,
        "training_time_hours": 8.5,
        "status": "completed",
    })
    
    # Finish
    run.finish()
    print(f"✅ Experiment completed: {run.id}")
    
    return run.id


def create_nlp_experiment():
    """Create a sample NLP experiment."""
    print("\n" + "="*60)
    print("Creating NLP Experiment")
    print("="*60)
    
    # Initialize
    run = rn.init(
        project="nlp",
        name="bert_finetuning",
        capture_env=True
    )
    
    print(f"✅ Created run: {run.id}")
    
    # Log configuration
    run.log({
        "model": "bert-base-uncased",
        "task": "sentiment_analysis",
        "dataset": "IMDB",
        "batch_size": 32,
        "learning_rate": 2e-5,
        "max_seq_length": 128,
        "num_epochs": 5,
    }, step=0)
    
    run.set_primary_metric("f1_score", mode="max")
    
    # Simulate training (faster convergence)
    print(f"\n📊 Simulating training...")
    for epoch in range(1, 6):
        for step in range(1, 201):
            global_step = (epoch - 1) * 200 + step
            time.sleep(0.01)
            
            # Metrics
            loss = 0.8 * math.exp(-global_step/200) + random.uniform(0, 0.05)
            f1 = min(0.95, 0.5 + global_step * 0.0004 + random.uniform(-0.01, 0.01))
            
            run.log({
                "loss": loss,
                "f1_score": f1,
            }, step=global_step)
            
            if step % 50 == 0:
                print(f"   Epoch {epoch}/5, Step {step}/200 - F1: {f1:.4f}")
    
    # Summary
    run.summary({
        "best_f1_score": 0.94,
        "final_loss": 0.12,
        "total_steps": 1000,
        "status": "completed",
    })
    
    run.finish()
    print(f"✅ Experiment completed: {run.id}")
    
    return run.id


def create_reinforcement_learning_experiment():
    """Create a sample RL experiment."""
    print("\n" + "="*60)
    print("Creating Reinforcement Learning Experiment")
    print("="*60)
    
    # Initialize
    run = rn.init(
        project="rl",
        name="dqn_cartpole",
        capture_env=True
    )
    
    print(f"✅ Created run: {run.id}")
    
    # Configuration
    run.log({
        "algorithm": "DQN",
        "environment": "CartPole-v1",
        "learning_rate": 0.001,
        "gamma": 0.99,
        "epsilon_start": 1.0,
        "epsilon_end": 0.01,
        "epsilon_decay": 0.995,
        "replay_buffer_size": 10000,
        "batch_size": 64,
    }, step=0)
    
    run.set_primary_metric("episode_reward", mode="max")
    
    # Simulate training
    print(f"\n📊 Simulating training...")
    for episode in range(1, 501):
        time.sleep(0.02)
        
        # Reward increases over time
        reward = min(500, 50 + episode * 0.9 + random.uniform(-20, 20))
        epsilon = max(0.01, 1.0 * (0.995 ** episode))
        loss = 0.5 * math.exp(-episode/100) + random.uniform(0, 0.1)
        
        run.log({
            "episode_reward": reward,
            "epsilon": epsilon,
            "loss": loss,
        }, step=episode)
        
        if episode % 50 == 0:
            print(f"   Episode {episode}/500 - Reward: {reward:.1f}")
    
    # Summary
    run.summary({
        "best_reward": 500,
        "average_reward_last_100": 485,
        "total_episodes": 500,
        "status": "completed",
    })
    
    run.finish()
    print(f"✅ Experiment completed: {run.id}")
    
    return run.id


def create_failed_experiment():
    """Create a failed experiment (for testing error handling)."""
    print("\n" + "="*60)
    print("Creating Failed Experiment")
    print("="*60)
    
    # Initialize
    run = rn.init(
        project="vision",
        name="mobilenet_unstable",
        capture_env=True
    )
    
    print(f"✅ Created run: {run.id}")
    
    # Configuration
    run.log({
        "model": "mobilenet_v2",
        "learning_rate": 0.5,  # Too high!
        "batch_size": 128,
    }, step=0)
    
    # Simulate unstable training
    print(f"\n📊 Simulating unstable training...")
    for step in range(1, 51):
        time.sleep(0.05)
        
        # Loss explodes
        loss = 0.5 + step * 0.1 + random.uniform(0, 0.5)
        
        run.log({
            "train_loss": loss,
        }, step=step)
        
        # Simulate NaN after step 30
        if step == 30:
            run.log({"train_loss": float('nan')}, step=step)
            run.log_text("❌ ERROR: Loss became NaN!")
            print(f"   ❌ Training failed at step {step} - Loss NaN")
            break
    
    # Summary
    run.summary({
        "status": "failed",
        "error": "Loss became NaN at step 30",
        "reason": "Learning rate too high",
    })
    
    run.finish(status="failed")
    print(f"❌ Experiment failed: {run.id}")
    
    return run.id


def main():
    """Create all sample experiments."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║         Create Sample Experiments for Testing            ║
║                                                           ║
║  This script creates various sample experiments to       ║
║  test the Runicorn system.                               ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    created_runs = []
    
    # Create experiments
    try:
        run_id = create_image_classification_experiment()
        created_runs.append(("vision/resnet50_baseline", run_id))
        
        run_id = create_nlp_experiment()
        created_runs.append(("nlp/bert_finetuning", run_id))
        
        run_id = create_reinforcement_learning_experiment()
        created_runs.append(("rl/dqn_cartpole", run_id))
        
        run_id = create_failed_experiment()
        created_runs.append(("vision/mobilenet_unstable", run_id))
        
    except Exception as e:
        print(f"\n❌ Error creating experiments: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print(f"✅ Created {len(created_runs)} experiments:")
    for name, run_id in created_runs:
        print(f"   - {name}: {run_id}")
    
    print(f"\n💡 View experiments:")
    print(f"   runicorn viewer")
    print(f"   http://127.0.0.1:23300")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
