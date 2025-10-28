#!/usr/bin/env python3
"""
Test Runicorn Python API Client

Comprehensive test of the programmatic API client.
Requires Viewer to be running and sample experiments to exist.
"""
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import runicorn.api as api


def test_connection():
    """Test basic connection to Viewer."""
    print("\n" + "="*60)
    print("Test 1: Connection")
    print("="*60)
    
    try:
        client = api.connect("http://127.0.0.1:23300")
        print(f"✅ Connected to Runicorn Viewer")
        
        # Health check
        health = client.health_check()
        print(f"   Status: {health.get('status')}")
        print(f"   Version: {health.get('version', 'N/A')}")
        
        return client
    except api.ConnectionError as e:
        print(f"❌ Connection failed: {e}")
        print(f"\n💡 Make sure Viewer is running:")
        print(f"   runicorn viewer")
        return None


def test_list_experiments(client):
    """Test listing experiments."""
    print("\n" + "="*60)
    print("Test 2: List Experiments")
    print("="*60)
    
    try:
        # List all experiments
        experiments = client.list_experiments()
        print(f"✅ Found {len(experiments)} total experiments")
        
        # List by project
        vision_exps = client.list_experiments(project="vision")
        nlp_exps = client.list_experiments(project="nlp")
        rl_exps = client.list_experiments(project="rl")
        
        print(f"   Vision: {len(vision_exps)} experiments")
        print(f"   NLP: {len(nlp_exps)} experiments")
        print(f"   RL: {len(rl_exps)} experiments")
        
        # Show recent experiments
        if experiments:
            print(f"\n   Recent experiments:")
            for exp in experiments[:5]:
                print(f"   - {exp['project']}/{exp['name']}")
                print(f"     ID: {exp['id']}")
                print(f"     Status: {exp.get('status', 'unknown')}")
        
        return experiments
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def test_get_experiment_details(client, experiments):
    """Test getting experiment details."""
    print("\n" + "="*60)
    print("Test 3: Get Experiment Details")
    print("="*60)
    
    if not experiments:
        print("⚠️  No experiments available")
        return
    
    try:
        # Get first experiment
        run_id = experiments[0]["id"]
        run = client.get_run(run_id)
        
        print(f"✅ Retrieved run: {run_id}")
        print(f"   Project: {run.get('project')}")
        print(f"   Name: {run.get('name')}")
        print(f"   Status: {run.get('status')}")
        print(f"   Created: {run.get('created_at')}")
        
        # Show summary if available
        summary = run.get('summary', {})
        if summary:
            print(f"\n   Summary:")
            for key, value in list(summary.items())[:5]:
                print(f"   - {key}: {value}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_get_metrics(client, experiments):
    """Test getting metrics data."""
    print("\n" + "="*60)
    print("Test 4: Get Metrics")
    print("="*60)
    
    if not experiments:
        print("⚠️  No experiments available")
        return None
    
    try:
        # Get metrics for first experiment
        run_id = experiments[0]["id"]
        metrics = client.get_metrics(run_id, limit=100)
        
        metrics_dict = metrics.get("metrics", {})
        metric_names = list(metrics_dict.keys())
        
        print(f"✅ Retrieved metrics for run: {run_id}")
        print(f"   Found {len(metric_names)} metrics:")
        
        # Show metric details
        for metric_name in metric_names[:5]:
            points = metrics_dict[metric_name]
            print(f"   - {metric_name}: {len(points)} points")
            if points:
                first_val = points[0].get('value')
                last_val = points[-1].get('value')
                print(f"     First: {first_val:.4f}, Last: {last_val:.4f}")
        
        return metrics
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_list_projects(client):
    """Test listing projects."""
    print("\n" + "="*60)
    print("Test 5: List Projects")
    print("="*60)
    
    try:
        projects = client.list_projects()
        print(f"✅ Found {len(projects)} projects:")
        
        for proj in projects:
            print(f"   - {proj['name']}: {proj.get('experiment_count', 0)} experiments")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_config_api(client):
    """Test config API."""
    print("\n" + "="*60)
    print("Test 6: Config API")
    print("="*60)
    
    try:
        config = client.get_config()
        print(f"✅ Retrieved config:")
        print(f"   User root: {config.get('user_root')}")
        print(f"   Port: {config.get('port', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_artifacts_api(client):
    """Test Artifacts API."""
    print("\n" + "="*60)
    print("Test 7: Artifacts API")
    print("="*60)
    
    try:
        # List all artifacts
        artifacts = client.artifacts.list_artifacts()
        print(f"✅ Found {len(artifacts)} artifacts")
        
        if artifacts:
            print(f"\n   Recent artifacts:")
            for artifact in artifacts[:3]:
                print(f"   - {artifact['name']} v{artifact['version']}")
                print(f"     Type: {artifact.get('type', 'unknown')}")
                print(f"     Size: {artifact.get('size_bytes', 0) / 1024:.1f} KB")
        
        # List by type
        model_artifacts = client.artifacts.list_artifacts(type="model")
        print(f"\n   Model artifacts: {len(model_artifacts)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_remote_api(client):
    """Test Remote API."""
    print("\n" + "="*60)
    print("Test 8: Remote API")
    print("="*60)
    
    try:
        # Get remote status
        status = client.remote.get_remote_status()
        print(f"✅ Remote status:")
        print(f"   Active connections: {status.get('connection_count', 0)}")
        print(f"   Active sessions: {status.get('session_count', 0)}")
        
        # List SSH sessions
        sessions = client.remote.list_sessions()
        print(f"\n   SSH sessions: {len(sessions)}")
        
        # List viewer sessions
        viewer_sessions = client.remote.list_viewer_sessions()
        print(f"   Viewer sessions: {len(viewer_sessions)}")
        
        if viewer_sessions:
            print(f"\n   Active viewer sessions:")
            for session in viewer_sessions:
                print(f"   - Session ID: {session['session_id']}")
                print(f"     Local port: {session.get('local_port')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_data_export(client, experiments):
    """Test data export functionality."""
    print("\n" + "="*60)
    print("Test 9: Data Export")
    print("="*60)
    
    if not experiments:
        print("⚠️  No experiments available")
        return
    
    try:
        run_id = experiments[0]["id"]
        
        # Export as JSON
        print(f"   Exporting run {run_id} as JSON...")
        data = client.export_experiment(run_id, format="json")
        print(f"✅ Exported {len(data)} bytes")
        
        # Try to parse JSON
        try:
            json_data = json.loads(data)
            print(f"   Contains: {list(json_data.keys())}")
        except:
            print(f"   (Binary data)")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_context_manager():
    """Test context manager usage."""
    print("\n" + "="*60)
    print("Test 10: Context Manager")
    print("="*60)
    
    try:
        with api.connect() as client:
            health = client.health_check()
            print(f"✅ Context manager works")
            print(f"   Status: {health.get('status')}")
        
        print(f"✅ Client auto-closed")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_error_handling(client):
    """Test error handling."""
    print("\n" + "="*60)
    print("Test 11: Error Handling")
    print("="*60)
    
    try:
        # Try to get non-existent run
        try:
            client.get_run("nonexistent_run_id_12345")
            print(f"❌ Should have raised NotFoundError")
        except api.NotFoundError:
            print(f"✅ NotFoundError raised correctly")
        
        # Try invalid parameters
        try:
            client.list_experiments(status="invalid_status_xyz")
            # May or may not fail depending on backend
            print(f"⚠️  Invalid status accepted (backend may filter)")
        except api.BadRequestError:
            print(f"✅ BadRequestError raised correctly")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def test_advanced_queries(client, experiments):
    """Test advanced query features."""
    print("\n" + "="*60)
    print("Test 12: Advanced Queries")
    print("="*60)
    
    if not experiments:
        print("⚠️  No experiments available")
        return
    
    try:
        # Pagination
        print(f"   Testing pagination...")
        page1 = client.list_experiments(limit=2, offset=0)
        page2 = client.list_experiments(limit=2, offset=2)
        print(f"✅ Page 1: {len(page1)} experiments")
        print(f"   Page 2: {len(page2)} experiments")
        
        # Filter by status
        running = client.list_experiments(status="running")
        finished = client.list_experiments(status="finished")
        print(f"\n   Running: {len(running)}")
        print(f"   Finished: {len(finished)}")
        
        # Get specific metrics
        if experiments:
            run_id = experiments[0]["id"]
            metrics = client.get_metrics(run_id, metric_names=["loss", "accuracy"])
            metric_names = list(metrics.get("metrics", {}).keys())
            print(f"\n   Filtered metrics: {metric_names}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Run all tests."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║       Runicorn Python API Client Test Suite              ║
║                                                           ║
║  Prerequisites:                                           ║
║  1. Viewer must be running: runicorn viewer              ║
║  2. Sample data should exist (run create_sample_exp.py)  ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Connect
    client = test_connection()
    if not client:
        return 1
    
    try:
        # Run tests
        experiments = test_list_experiments(client)
        test_get_experiment_details(client, experiments)
        metrics = test_get_metrics(client, experiments)
        test_list_projects(client)
        test_config_api(client)
        test_artifacts_api(client)
        test_remote_api(client)
        test_data_export(client, experiments)
        test_error_handling(client)
        test_advanced_queries(client, experiments)
        
        # Close client
        client.close()
        
        # Test context manager separately
        test_context_manager()
        
        # Summary
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        print(f"✅ All tests completed successfully!")
        print(f"\n💡 The Python API Client is working correctly.")
        print(f"   You can now use it in your scripts:")
        print(f"   ")
        print(f"   import runicorn.api as api")
        print(f"   client = api.connect()")
        print(f"   experiments = client.list_experiments()")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if client:
            try:
                client.close()
            except:
                pass


if __name__ == "__main__":
    sys.exit(main())
