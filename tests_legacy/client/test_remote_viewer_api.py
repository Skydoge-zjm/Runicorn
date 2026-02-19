"""
Test Remote Viewer API Endpoints

Tests the unified Remote API endpoints.
Requires a running local viewer with Remote API enabled.
"""
import sys
import json
import time
import requests
from pathlib import Path


def load_config():
    """Load test configuration."""
    config_file = Path(__file__).parent / "config.json"
    if not config_file.exists():
        print("❌ Error: config.json not found")
        sys.exit(1)
    
    with open(config_file) as f:
        return json.load(f)


def test_remote_api(base_url: str = "http://localhost:23300"):
    """Test Remote API endpoints."""
    print("="*60)
    print("🧪 Testing Remote Viewer API Endpoints")
    print("="*60)
    print(f"Base URL: {base_url}")
    print()
    print("⚠️  Make sure local viewer is running:")
    print("   python -m runicorn viewer --port 23300")
    print()
    
    config_data = load_config()
    session_id = None
    connection_id = None
    
    try:
        # Test 1: Check API health
        print(f"\n💓 Test 1: Checking API health...")
        try:
            response = requests.get(f"{base_url}/api/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ API is healthy")
            else:
                print(f"❌ API returned {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to {base_url}")
            print(f"   Is the viewer running?")
            return False
        
        # Test 2: POST /api/remote/connect
        print(f"\n🔗 Test 2: Testing SSH connection...")
        payload = {
            "host": config_data['wsl_host'],
            "port": config_data['wsl_port'],
            "username": config_data['wsl_username'],
            "password": config_data.get('wsl_password'),
            "private_key_path": config_data.get('wsl_key_path'),
            "passphrase": config_data.get('wsl_passphrase'),
        }
        
        try:
            response = requests.post(
                f"{base_url}/api/remote/connect",
                json=payload,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                connection_id = data.get('connection_id')
                print(f"✅ Connection established")
                print(f"   Connection ID: {connection_id}")
            else:
                print(f"❌ Connection failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        # Test 3: GET /api/remote/sessions
        print(f"\n📋 Test 3: Listing SSH sessions...")
        try:
            response = requests.get(f"{base_url}/api/remote/sessions", timeout=5)
            if response.status_code == 200:
                data = response.json()
                sessions = data.get('sessions', [])
                print(f"✅ Found {len(sessions)} sessions")
                for session in sessions:
                    print(f"   - {session.get('key')}: connected={session.get('connected')}")
            else:
                print(f"❌ Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        # Test 4: GET /api/remote/fs/list
        print(f"\n📂 Test 4: Listing remote directory...")
        try:
            response = requests.get(
                f"{base_url}/api/remote/fs/list",
                params={
                    "connection_id": connection_id,
                    "path": "~"
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                print(f"✅ Found {len(items)} items in home directory")
                for item in items[:5]:  # Show first 5
                    icon = "📁" if item.get('is_dir') else "📄"
                    print(f"   {icon} {item.get('name')}")
            else:
                print(f"❌ Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        # Test 5: GET /api/remote/fs/exists
        print(f"\n🔍 Test 5: Checking if remote path exists...")
        remote_root = config_data['remote_root']
        try:
            response = requests.get(
                f"{base_url}/api/remote/fs/exists",
                params={
                    "connection_id": connection_id,
                    "path": remote_root
                },
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                exists = data.get('exists')
                is_dir = data.get('is_dir')
                if exists and is_dir:
                    print(f"✅ Remote root exists: {remote_root}")
                else:
                    print(f"⚠️  Remote root not found or not a directory")
                    print(f"   Run on WSL: python tests/server/setup_test_data.py")
                    return False
            else:
                print(f"❌ Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        # Test 6: POST /api/remote/viewer/start
        print(f"\n🚀 Test 6: Starting Remote Viewer...")
        print(f"   (This may take 10-15 seconds...)")
        
        payload = {
            "host": config_data['wsl_host'],
            "port": config_data['wsl_port'],
            "username": config_data['wsl_username'],
            "password": config_data.get('wsl_password'),
            "private_key_path": config_data.get('wsl_key_path'),
            "passphrase": config_data.get('wsl_passphrase'),
            "remote_root": remote_root,
            "local_port": config_data.get('local_port'),
        }
        
        try:
            response = requests.post(
                f"{base_url}/api/remote/viewer/start",
                json=payload,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                session = data.get('session', {})
                session_id = session.get('session_id')
                local_port = session.get('local_port')
                print(f"✅ Remote Viewer started")
                print(f"   Session ID: {session_id}")
                print(f"   Local URL: {session.get('url')}")
            else:
                print(f"❌ Failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        # Test 7: GET /api/remote/viewer/sessions
        print(f"\n📋 Test 7: Listing Remote Viewer sessions...")
        try:
            response = requests.get(
                f"{base_url}/api/remote/viewer/sessions",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                sessions = data.get('sessions', [])
                print(f"✅ Found {len(sessions)} active sessions")
                for sess in sessions:
                    print(f"   - {sess.get('session_id')}: {sess.get('url')}")
            else:
                print(f"❌ Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        # Test 8: Access remote viewer via tunnel
        print(f"\n🌐 Test 8: Accessing remote viewer...")
        time.sleep(2)  # Wait for tunnel to stabilize
        
        try:
            response = requests.get(
                f"http://localhost:{local_port}/api/health",
                timeout=10
            )
            if response.status_code == 200:
                print(f"✅ Remote viewer is accessible")
            else:
                print(f"❌ Remote viewer returned {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        # Test 9: GET /api/remote/status
        print(f"\n📊 Test 9: Getting overall remote status...")
        try:
            response = requests.get(f"{base_url}/api/remote/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status retrieved")
                print(f"   Connections: {data.get('connection_count')}")
                print(f"   Viewer sessions: {data.get('viewer_session_count')}")
            else:
                print(f"❌ Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        # Test 10: POST /api/remote/viewer/stop
        print(f"\n🛑 Test 10: Stopping Remote Viewer...")
        try:
            response = requests.post(
                f"{base_url}/api/remote/viewer/stop",
                json={"session_id": session_id},
                timeout=10
            )
            if response.status_code == 200:
                print(f"✅ Remote Viewer stopped")
            else:
                print(f"❌ Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        # Test 11: POST /api/remote/disconnect
        print(f"\n🔌 Test 11: Disconnecting SSH...")
        try:
            parts = connection_id.rsplit(':', 1)
            username_host = parts[0]
            port = int(parts[1])
            username, host = username_host.split('@', 1)
            
            response = requests.post(
                f"{base_url}/api/remote/disconnect",
                json={
                    "host": host,
                    "port": port,
                    "username": username
                },
                timeout=5
            )
            if response.status_code == 200:
                print(f"✅ SSH disconnected")
            else:
                print(f"❌ Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        print("\n" + "="*60)
        print("🎉 All API tests passed!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        print(f"\n🧹 Cleanup...")
        if session_id:
            try:
                requests.post(
                    f"{base_url}/api/remote/viewer/stop",
                    json={"session_id": session_id},
                    timeout=5
                )
                print(f"✓ Session stopped")
            except Exception:
                pass
        
        if connection_id:
            try:
                parts = connection_id.rsplit(':', 1)
                username_host = parts[0]
                port = int(parts[1])
                username, host = username_host.split('@', 1)
                
                requests.post(
                    f"{base_url}/api/remote/disconnect",
                    json={"host": host, "port": port, "username": username},
                    timeout=5
                )
                print(f"✓ Connection closed")
            except Exception:
                pass


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Remote Viewer API")
    parser.add_argument(
        "--url",
        default="http://localhost:23300",
        help="Base URL of local viewer (default: http://localhost:23300)"
    )
    
    args = parser.parse_args()
    
    try:
        success = test_remote_api(args.url)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n✋ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
