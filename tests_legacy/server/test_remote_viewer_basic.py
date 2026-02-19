#!/usr/bin/env python3
"""
Basic Tests for Remote Viewer (Server-Side)

Tests that should run on the WSL server to verify remote viewer basics.
"""
import sys
import time
import requests
from pathlib import Path


def test_viewer_health(port: int = 8080):
    """Test if viewer is running and healthy."""
    url = f"http://127.0.0.1:{port}/api/health"
    
    print(f"🔍 Testing viewer health at {url}")
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Viewer is healthy")
            print(f"   Status: {data}")
            return True
        else:
            print(f"❌ Viewer returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to viewer (is it running?)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_list_experiments(port: int = 8080):
    """Test listing experiments."""
    url = f"http://127.0.0.1:{port}/api/experiments"
    
    print(f"\n🔍 Testing experiment listing at {url}")
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            experiments = data.get("experiments", [])
            print(f"✅ Found {len(experiments)} experiments")
            for exp in experiments[:5]:  # Show first 5
                print(f"   - {exp.get('project')}/{exp.get('name')}: {exp.get('run_id')}")
            return True
        else:
            print(f"❌ Failed with status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_get_metrics(port: int = 8080):
    """Test getting metrics from an experiment."""
    # First, get experiment list
    url_list = f"http://127.0.0.1:{port}/api/experiments"
    
    try:
        response = requests.get(url_list, timeout=5)
        if response.status_code != 200:
            print(f"❌ Could not list experiments")
            return False
        
        experiments = response.json().get("experiments", [])
        if not experiments:
            print(f"⚠️  No experiments found to test")
            return True
        
        # Get first experiment
        exp = experiments[0]
        project = exp.get("project")
        name = exp.get("name")
        run_id = exp.get("run_id")
        
        print(f"\n🔍 Testing metrics for {project}/{name}/{run_id}")
        
        url_metrics = f"http://127.0.0.1:{port}/api/metrics"
        params = {
            "project": project,
            "name": name,
            "run_id": run_id
        }
        
        response = requests.get(url_metrics, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            metrics = data.get("metrics", [])
            print(f"✅ Retrieved {len(metrics)} metric points")
            if metrics:
                print(f"   Sample: {metrics[0]}")
            return True
        else:
            print(f"❌ Failed with status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def run_all_tests(port: int = 8080):
    """Run all basic tests."""
    print("="*60)
    print("🧪 Running Remote Viewer Basic Tests")
    print("="*60)
    
    tests = [
        ("Health Check", lambda: test_viewer_health(port)),
        ("List Experiments", lambda: test_list_experiments(port)),
        ("Get Metrics", lambda: test_get_metrics(port)),
    ]
    
    results = []
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))
        time.sleep(0.5)
    
    print("\n" + "="*60)
    print("📊 Test Results")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Remote Viewer basic functionality")
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Viewer port (default: 8080)"
    )
    
    args = parser.parse_args()
    
    exit_code = run_all_tests(args.port)
    sys.exit(exit_code)
