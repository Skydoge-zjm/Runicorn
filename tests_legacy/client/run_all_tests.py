"""
Run All Client Tests

Runs all Remote Viewer client tests in sequence.
"""
import sys
import subprocess
from pathlib import Path


def run_test(test_file: str, description: str) -> bool:
    """Run a single test file."""
    print("\n" + "="*70)
    print(f"🧪 {description}")
    print("="*70)
    
    test_path = Path(__file__).parent / test_file
    
    try:
        result = subprocess.run(
            [sys.executable, str(test_path)],
            cwd=Path(__file__).parent,
            timeout=120  # 2 minute timeout per test
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"\n❌ Test timed out after 120 seconds")
        return False
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False


def main():
    """Run all tests."""
    print("="*70)
    print("🚀 Running All Remote Viewer Client Tests")
    print("="*70)
    
    # Check config exists
    config_file = Path(__file__).parent / "config.json"
    if not config_file.exists():
        print("\n❌ Error: config.json not found")
        print("   Copy config.json.example to config.json and fill in your credentials")
        return False
    
    tests = [
        ("test_ssh_connection.py", "SSH Connection Test"),
        ("test_connection_pool.py", "SSH Connection Pool Test"),
        ("test_remote_viewer_connection.py", "Remote Viewer Complete Flow Test"),
    ]
    
    results = []
    
    for test_file, description in tests:
        success = run_test(test_file, description)
        results.append((description, success))
        
        if not success:
            print(f"\n⚠️  Test failed: {description}")
            print(f"   Stopping further tests")
            break
    
    # Summary
    print("\n" + "="*70)
    print("📊 Test Summary")
    print("="*70)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {description}")
    
    print(f"\n{passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n🎉 All tests passed!")
        print("\nNext steps:")
        print("1. Test the API endpoints:")
        print("   python -m runicorn viewer --port 23300")
        print("   python tests/client/test_remote_viewer_api.py")
        print("\n2. Ready for Phase 4: Frontend integration")
        return True
    else:
        print(f"\n⚠️  {len(tests) - passed} test(s) failed")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n✋ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
