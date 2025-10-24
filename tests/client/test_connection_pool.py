"""
Test SSH Connection Pool

Tests connection pooling and reuse.
"""
import sys
import json
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from runicorn.remote import SSHConfig, SSHConnectionPool


def load_config():
    """Load test configuration."""
    config_file = Path(__file__).parent / "config.json"
    if not config_file.exists():
        print("❌ Error: config.json not found")
        sys.exit(1)
    
    with open(config_file) as f:
        return json.load(f)


def test_connection_pool():
    """Test connection pool."""
    print("="*60)
    print("🧪 Testing SSH Connection Pool")
    print("="*60)
    
    config_data = load_config()
    
    # Create pool
    pool = SSHConnectionPool()
    
    # Create config
    config = SSHConfig(
        host=config_data['wsl_host'],
        port=config_data['wsl_port'],
        username=config_data['wsl_username'],
        password=config_data.get('wsl_password'),
        private_key_path=config_data.get('wsl_key_path'),
        passphrase=config_data.get('wsl_passphrase'),
    )
    
    # Test 1: Get or create connection
    print(f"\n🔗 Test 1: Getting connection from pool...")
    try:
        conn1 = pool.get_or_create(config)
        print(f"✅ Got connection 1: {config.get_key()}")
        print(f"   Connected: {conn1.is_connected}")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Test 2: Reuse connection
    print(f"\n♻️  Test 2: Reusing connection...")
    try:
        conn2 = pool.get_or_create(config)
        if conn1 is conn2:
            print(f"✅ Connection was reused (same object)")
        else:
            print(f"❌ Got different connection object")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Test 3: List connections
    print(f"\n📋 Test 3: Listing connections...")
    try:
        connections = pool.list_connections()
        print(f"   Active connections: {len(connections)}")
        for conn_info in connections:
            print(f"   - {conn_info['key']}: connected={conn_info['connected']}")
        if len(connections) == 1:
            print(f"✅ Correct number of connections")
        else:
            print(f"❌ Expected 1 connection, got {len(connections)}")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Test 4: Execute command via pooled connection
    print(f"\n💻 Test 4: Executing command...")
    try:
        stdout, stderr, exit_code = conn1.exec_command("whoami")
        print(f"   User: {stdout.strip()}")
        print(f"✅ Command executed successfully")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Test 5: Remove connection
    print(f"\n🗑️  Test 5: Removing connection from pool...")
    try:
        removed = pool.remove(config.host, config.port, config.username)
        if removed:
            print(f"✅ Connection removed")
        else:
            print(f"❌ Connection not found")
            return False
        
        # Verify connection is closed
        if not conn1.is_connected:
            print(f"✅ Connection was closed")
        else:
            print(f"⚠️  Connection still shows as connected")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Test 6: Pool is now empty
    print(f"\n📋 Test 6: Verifying pool is empty...")
    try:
        connections = pool.list_connections()
        if len(connections) == 0:
            print(f"✅ Pool is empty")
        else:
            print(f"❌ Pool still has {len(connections)} connections")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Test 7: Create new connection again
    print(f"\n🔗 Test 7: Creating new connection...")
    try:
        conn3 = pool.get_or_create(config)
        if conn3.is_connected:
            print(f"✅ New connection created")
        else:
            print(f"❌ Connection not active")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Test 8: Close all connections
    print(f"\n🔌 Test 8: Closing all connections...")
    try:
        pool.close_all()
        connections = pool.list_connections()
        if len(connections) == 0:
            print(f"✅ All connections closed")
        else:
            print(f"❌ Still have {len(connections)} connections")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    print("\n" + "="*60)
    print("🎉 All connection pool tests passed!")
    print("="*60)
    
    return True


if __name__ == "__main__":
    try:
        success = test_connection_pool()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n✋ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
