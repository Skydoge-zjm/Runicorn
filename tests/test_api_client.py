"""
Test Runicorn API Client

This demonstrates how to use the Runicorn API Client.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import runicorn.api as api


def test_basic_usage():
    """Test basic API client usage."""
    print("="*60)
    print("Testing Runicorn API Client")
    print("="*60)
    
    # Connect to Viewer (make sure viewer is running)
    try:
        client = api.connect("http://127.0.0.1:23300")
        print(f"✅ Connected to Viewer")
    except api.ConnectionError as e:
        print(f"❌ Failed to connect: {e}")
        print("Make sure Viewer is running: runicorn viewer")
        return
    
    # Test 1: Health check
    print(f"\n📊 Test 1: Health Check")
    health = client.health_check()
    print(f"   Status: {health.get('status')}")
    
    # Test 2: List projects
    print(f"\n📊 Test 2: List Projects")
    projects = client.list_projects()
    print(f"   Found {len(projects)} projects")
    for proj in projects[:3]:
        print(f"   - {proj['name']}: {proj['experiment_count']} experiments")
    
    # Test 3: List experiments
    print(f"\n📊 Test 3: List Experiments")
    experiments = client.list_experiments(limit=5)
    print(f"   Found {len(experiments)} experiments")
    
    if experiments:
        for exp in experiments[:3]:
            print(f"   - {exp['project']}/{exp['name']}: {exp['status']}")
        
        # Test 4: Get run details
        print(f"\n📊 Test 4: Get Run Details")
        run_id = experiments[0]["id"]
        run = client.get_run(run_id)
        print(f"   Run ID: {run['id']}")
        print(f"   Project: {run['project']}")
        print(f"   Name: {run['name']}")
        print(f"   Status: {run['status']}")
        
        # Test 5: Get metrics
        print(f"\n📊 Test 5: Get Metrics")
        metrics = client.get_metrics(run_id, limit=10)
        metric_names = list(metrics.get("metrics", {}).keys())
        print(f"   Found {len(metric_names)} metrics: {metric_names[:5]}")
    
    # Test 6: Get config
    print(f"\n📊 Test 6: Get Config")
    config = client.get_config()
    print(f"   User root: {config.get('user_root')}")
    
    # Close client
    client.close()
    print(f"\n✅ All tests passed!")

def test_remote_api():
    """Test Remote API."""
    print("\n" + "="*60)
    print("Testing Remote API")
    print("="*60)
    
    try:
        client = api.connect()
        print(f"✅ Connected to Viewer")
    except api.ConnectionError as e:
        print(f"❌ Failed to connect: {e}")
        return
    
    # Get remote status
    print(f"\n🔌 Remote Status")
    status = client.remote.get_remote_status()
    print(f"   Active connections: {status.get('connection_count', 0)}")
    print(f"   Active sessions: {status.get('session_count', 0)}")
    
    # List sessions
    print(f"\n🔌 SSH Sessions")
    sessions = client.remote.list_sessions()
    print(f"   Found {len(sessions)} SSH sessions")
    
    # List viewer sessions
    print(f"\n🔌 Viewer Sessions")
    viewer_sessions = client.remote.list_viewer_sessions()
    print(f"   Found {len(viewer_sessions)} viewer sessions")
    
    client.close()


def demo_context_manager():
    """Demonstrate context manager usage."""
    print("\n" + "="*60)
    print("Testing Context Manager")
    print("="*60)
    
    # Use with statement
    try:
        with api.connect() as client:
            experiments = client.list_experiments(limit=3)
            print(f"✅ Found {len(experiments)} experiments")
            print("✅ Client will auto-close")
    except api.ConnectionError as e:
        print(f"❌ Failed to connect: {e}")


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║          Runicorn API Client Test Suite                  ║
║                                                           ║
║  Make sure Viewer is running before running tests:       ║
║  $ runicorn viewer                                        ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Run tests
    test_basic_usage()
    test_remote_api()
    demo_context_manager()
    
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)
