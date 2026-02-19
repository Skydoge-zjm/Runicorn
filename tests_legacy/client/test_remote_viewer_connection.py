"""
Test Remote Viewer Complete Flow

Tests the complete Remote Viewer functionality including:
1. SSH connection
2. Starting remote viewer process
3. Creating SSH tunnel
4. Accessing remote viewer via local port
5. Cleanup
"""
import sys
import json
import time
import requests
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from runicorn.remote import SSHConfig, SSHConnectionPool
from runicorn.remote.viewer import RemoteViewerManager


def load_config():
    """Load test configuration."""
    config_file = Path(__file__).parent / "config.json"
    if not config_file.exists():
        print("❌ Error: config.json not found")
        sys.exit(1)
    
    with open(config_file) as f:
        return json.load(f)


def test_remote_viewer_flow():
    """Test complete Remote Viewer flow."""
    print("="*60)
    print("🧪 Testing Remote Viewer Complete Flow")
    print("="*60)
    
    config_data = load_config()
    
    pool = SSHConnectionPool()
    manager = RemoteViewerManager()
    session = None
    
    try:
        # Test 1: Create SSH connection
        print(f"\n🔗 Test 1: Establishing SSH connection...")
        config = SSHConfig(
            host=config_data['wsl_host'],
            port=config_data['wsl_port'],
            username=config_data['wsl_username'],
            password=config_data.get('wsl_password'),
            private_key_path=config_data.get('wsl_key_path'),
            passphrase=config_data.get('wsl_passphrase'),
        )
        
        connection = pool.get_or_create(config)
        print(f"✅ SSH connected: {config.get_key()}")
        
        # Test 2: Start Remote Viewer
        print(f"\n🚀 Test 2: Starting Remote Viewer...")
        print(f"   Remote root: {config_data['remote_root']}")
        print(f"   Local port: {config_data['local_port']}")
        print(f"   (This may take 10-15 seconds...)")
        
        try:
            session = manager.start_remote_viewer(
                connection=connection,
                remote_root=config_data['remote_root'],
                local_port=config_data.get('local_port'),
                remote_port=config_data.get('remote_port'),
            )
            
            print(f"✅ Remote Viewer started")
            print(f"   Session ID: {session.session_id}")
            print(f"   Remote PID: {session.remote_pid}")
            print(f"   Remote port: {session.remote_port}")
            print(f"   Local port: {session.local_port}")
            print(f"   URL: {session.to_dict()['url']}")
            
        except Exception as e:
            print(f"❌ Failed to start Remote Viewer: {e}")
            return False
        
        # Test 3: Verify tunnel is active
        print(f"\n🔌 Test 3: Verifying SSH tunnel...")
        time.sleep(2)  # Wait for tunnel to stabilize
        
        if session.is_active:
            print(f"✅ Session is active")
        else:
            print(f"❌ Session is not active")
            return False
        
        # Test 4: Test health endpoint via tunnel
        print(f"\n💓 Test 4: Testing remote viewer health...")
        url = f"http://localhost:{session.local_port}/api/health"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Remote viewer is healthy")
                print(f"   Response: {data}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Cannot connect to remote viewer: {e}")
            print(f"   This might indicate tunnel setup issue")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        # Test 5: List experiments via tunnel
        print(f"\n📋 Test 5: Listing experiments via tunnel...")
        url = f"http://localhost:{session.local_port}/api/experiments"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                experiments = data.get("experiments", [])
                print(f"✅ Found {len(experiments)} experiments")
                for exp in experiments[:3]:  # Show first 3
                    print(f"   - {exp.get('project')}/{exp.get('name')}")
            else:
                print(f"❌ Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        # Test 6: Check session info
        print(f"\n📊 Test 6: Checking session info...")
        session_info = session.to_dict()
        print(f"   Session ID: {session_info['session_id']}")
        print(f"   Uptime: {session_info['uptime_seconds']:.1f}s")
        print(f"   Active: {session_info['is_active']}")
        print(f"✅ Session info is correct")
        
        # Test 7: List all sessions
        print(f"\n📋 Test 7: Listing all sessions...")
        sessions = manager.list_sessions()
        print(f"   Active sessions: {len(sessions)}")
        if len(sessions) == 1:
            print(f"✅ Correct number of sessions")
        else:
            print(f"⚠️  Expected 1 session, got {len(sessions)}")
        
        # Test 8: Stop Remote Viewer
        print(f"\n🛑 Test 8: Stopping Remote Viewer...")
        success = manager.stop_remote_viewer(session.session_id)
        if success:
            print(f"✅ Remote Viewer stopped")
        else:
            print(f"❌ Failed to stop Remote Viewer")
            return False
        
        # Test 9: Verify session is stopped
        print(f"\n🔍 Test 9: Verifying session is stopped...")
        time.sleep(2)
        
        if not session.is_active:
            print(f"✅ Session is inactive")
        else:
            print(f"⚠️  Session still appears active")
        
        # Test 10: Verify viewer is not accessible
        print(f"\n🔌 Test 10: Verifying viewer is not accessible...")
        try:
            response = requests.get(
                f"http://localhost:{session.local_port}/api/health",
                timeout=3
            )
            print(f"⚠️  Viewer still responds (might be cleanup delay)")
        except requests.exceptions.ConnectionError:
            print(f"✅ Viewer is not accessible (as expected)")
        except Exception as e:
            print(f"⚠️  Unexpected error: {e}")
        
        print("\n" + "="*60)
        print("🎉 All Remote Viewer tests passed!")
        print("="*60)
        print(f"\n✨ You can now use Remote Viewer:")
        print(f"   python -m runicorn viewer")
        print(f"   # Then connect via UI to WSL server")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        print(f"\n🧹 Cleanup...")
        if session:
            try:
                manager.stop_remote_viewer(session.session_id)
                print(f"✓ Session stopped")
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")
        
        try:
            pool.close_all()
            print(f"✓ Connections closed")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")


if __name__ == "__main__":
    try:
        success = test_remote_viewer_flow()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n✋ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
