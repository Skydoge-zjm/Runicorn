# Runicorn Architecture (v0.3.1)

## 🏗️ Modular Architecture

Runicorn v0.3.1 features a modern modular architecture for better maintainability and performance.

### Directory Structure
```
src/runicorn/
├── sdk.py                 # Main SDK with integrated modern storage
├── viewer/                # Web interface (modular)
│   ├── __init__.py       # FastAPI app factory
│   ├── api/              # API route modules
│   ├── services/         # Business logic layer
│   └── utils/            # Helper functions
├── storage/              # High-performance storage system
│   ├── backends.py       # Storage backend implementations
│   ├── models.py         # Data models
│   └── schema.sql        # SQLite database schema
└── (other modules)       # Existing functionality
```

## 💾 Hybrid Storage System

### Storage Architecture
- **SQLite Database**: Fast queries, metadata, and metrics indexing
- **File System**: Large files, logs, and human-readable data
- **Automatic Migration**: Seamless upgrade from file-only storage

### File Layout
```
user_root_dir/
├── runicorn.db                    # SQLite database (NEW)
├── <project>/
│   └── <name>/
│       └── runs/
│           └── <run_id>/
│               ├── meta.json      # Experiment metadata
│               ├── status.json    # Run status
│               ├── events.jsonl   # Metrics data
│               ├── logs.txt       # Text logs
│               └── media/         # Images and files
```

## 🔧 API Versions

### V1 API (Backward Compatible)
- `/api/runs` - Traditional file-based queries
- `/api/config` - Configuration management
- All existing endpoints maintained

### V2 API (High Performance)
- `/api/v2/experiments` - SQLite-powered experiment queries
- `/api/v2/analytics` - Real-time analytics and insights
- Advanced filtering, pagination, and search capabilities

## ⚡ Performance Improvements

- **Query Speed**: 10-500x faster experiment listing
- **Scalability**: Support for 10,000+ experiments
- **Concurrent Access**: 100+ simultaneous users
- **Advanced Queries**: Complex filtering and search in milliseconds
