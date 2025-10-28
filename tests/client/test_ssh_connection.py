"""
Test SSH Connection

Tests basic SSH connection to WSL server.
"""
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from runicorn.remote import SSHConfig, SSHConnection


def load_config():
    """Load test configuration."""
    config_file = Path(__file__).parent / "config.json"
    if not config_file.exists():
        print("❌ Error: config.json not found")
        print("   Copy config.json.example to config.json and fill in your credentials")
        sys.exit(1)
    
    with open(config_file) as f:
        return json.load(f)


def test_ssh_connection():
    """Test SSH connection."""
    print("="*60)
    print("🧪 Testing SSH Connection to WSL")
    print("="*60)
    
    config_data = load_config()
    
    print(f"\n📋 Connection Info:")
    print(f"   Host: {config_data['wsl_host']}")
    print(f"   Port: {config_data['wsl_port']}")
    print(f"   Username: {config_data['wsl_username']}")
    print(f"   Auth: {'password' if config_data['wsl_password'] else 'key'}")
    
    # Create SSH config
    config = SSHConfig(
        host=config_data['wsl_host'],
        port=config_data['wsl_port'],
        username=config_data['wsl_username'],
        password=config_data.get('wsl_password'),
        private_key_path=config_data.get('wsl_key_path'),
        passphrase=config_data.get('wsl_passphrase'),
    )
    
    connection = SSHConnection(config)
    
    # Test 1: Connect
    print(f"\n🔗 Test 1: Connecting...")
    try:
        connection.connect()
        print(f"✅ Connected successfully")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    # Test 2: Check health
    print(f"\n💓 Test 2: Checking connection health...")
    if connection.is_connected:
        print(f"✅ Connection is healthy")
    else:
        print(f"❌ Connection is not healthy")
        return False
    
    # Test 3: Execute command
    print(f"\n💻 Test 3: Executing test command...")
    try:
        stdout, stderr, exit_code = connection.exec_command("echo 'Hello from WSL'")
        print(f"   Command output: {stdout.strip()}")
        print(f"   Exit code: {exit_code}")
        if exit_code == 0:
            print(f"✅ Command executed successfully")
        else:
            print(f"❌ Command failed with exit code: {exit_code}")
            return False
    except Exception as e:
        print(f"❌ Command execution failed: {e}")
        return False
    
    # Test 4: Check Python
    print(f"\n🐍 Test 4: Checking Python on remote...")
    try:
        stdout, stderr, exit_code = connection.exec_command("python3 --version")
        if exit_code == 0:
            version = stdout.strip()
            print(f"   Python version: {version}")
            print(f"✅ Python is available")
        else:
            print(f"❌ Python not found")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 5: Check runicorn installation
    print(f"\n📦 Test 5: Checking runicorn installation...")
    try:
        stdout, stderr, exit_code = connection.exec_command(
            "python3 -c 'import runicorn; print(runicorn.__version__)'"
        )
        if exit_code == 0:
            version = stdout.strip()
            print(f"   Runicorn version: {version}")
            print(f"✅ Runicorn is installed")
        else:
            print(f"⚠️  Runicorn not installed on remote")
            print(f"   Run: pip install -e /mnt/e/pycharm_project/Runicorn")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 6: Check test data directory
    print(f"\n📂 Test 6: Checking test data directory...")
    remote_root = config_data['remote_root']
    try:
        stdout, stderr, exit_code = connection.exec_command(f"test -d {remote_root} && echo 'exists' || echo 'not_exists'")
        exists = stdout.strip() == "exists"
        if exists:
            print(f"   Directory: {remote_root}")
            print(f"✅ Test data directory exists")
        else:
            print(f"⚠️  Test data directory not found: {remote_root}")
            print(f"   Run on WSL: python tests/server/setup_test_data.py")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 7: Get SFTP client
    print(f"\n📁 Test 7: Testing SFTP...")
    try:
        sftp = connection.get_sftp()
        # List home directory
        home_items = sftp.listdir(".")
        print(f"   Home directory has {len(home_items)} items")
        print(f"✅ SFTP is working")
    except Exception as e:
        print(f"❌ SFTP failed: {e}")
        return False
    
    # Cleanup
    print(f"\n🔌 Disconnecting...")
    connection.disconnect()
    print(f"✅ Disconnected")
    
    print("\n" + "="*60)
    print("🎉 All SSH connection tests passed!")
    print("="*60)
    
    return True


if __name__ == "__main__":
    try:
        success = test_ssh_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n✋ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
