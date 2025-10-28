#!/bin/bash
# Cleanup script for Remote Viewer tests (WSL)

echo "🧹 Cleaning up Remote Viewer test environment..."

# Kill any running runicorn viewer processes
echo "Stopping any running viewer processes..."
pkill -f "runicorn viewer" && echo "✓ Stopped viewer processes" || echo "ℹ No viewer processes found"

# Remove test data directory
TEST_DATA_DIR="${1:-$HOME/runicorn_test_data}"
if [ -d "$TEST_DATA_DIR" ]; then
    echo "Removing test data: $TEST_DATA_DIR"
    rm -rf "$TEST_DATA_DIR"
    echo "✓ Test data removed"
else
    echo "ℹ Test data directory not found: $TEST_DATA_DIR"
fi

# Remove log files
echo "Removing log files..."
rm -f /tmp/runicorn_viewer_*.log 2>/dev/null && echo "✓ Log files removed" || echo "ℹ No log files found"

echo ""
echo "✅ Cleanup complete!"
