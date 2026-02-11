-- Runicorn SQLite Database Schema
-- Modern storage schema for high-performance experiment tracking

-- =====================================================
-- Experiments Main Table: Core experiment metadata
-- =====================================================
CREATE TABLE IF NOT EXISTS experiments (
    -- Primary identification
    id TEXT PRIMARY KEY,                    -- Experiment ID (format: YYYYMMDD_HHMMSS_XXXXXX)
    path TEXT NOT NULL DEFAULT 'default',   -- Flexible hierarchy path (e.g., "cv/detection/yolo")
    alias TEXT,                             -- Optional user-friendly alias (can be repeated)
    
    -- Timestamps
    created_at REAL NOT NULL,              -- Creation time (Unix timestamp)
    updated_at REAL NOT NULL,              -- Last update time
    started_at REAL,                       -- Start time
    ended_at REAL,                         -- End time
    
    -- Status management
    status TEXT NOT NULL DEFAULT 'running', -- 'running', 'finished', 'failed', 'interrupted'
    exit_reason TEXT,                       -- Exit reason for failed runs
    
    -- Process information
    pid INTEGER,                           -- Process ID
    python_version TEXT,                   -- Python version string
    platform TEXT,                        -- Operating system info
    hostname TEXT,                         -- Host machine name
    
    -- Best metric tracking system
    best_metric_name TEXT,                 -- Primary metric name
    best_metric_value REAL,               -- Best metric value achieved
    best_metric_step INTEGER,              -- Step where best value was achieved
    best_metric_mode TEXT,                 -- 'max' or 'min' optimization mode
    
    -- Soft delete support
    deleted_at REAL,                       -- Deletion timestamp (NULL = not deleted)
    delete_reason TEXT,                    -- Reason for deletion
    
    -- File system integration
    run_dir TEXT NOT NULL,                 -- Absolute path to run directory
    
    -- Computed fields for analytics
    duration_seconds REAL,                 -- Total experiment duration
    metric_count INTEGER DEFAULT 0,        -- Number of metric data points
    
    -- Performance indexes
    CHECK (status IN ('running', 'finished', 'failed', 'interrupted'))
);

-- Performance indexes for common queries
CREATE INDEX IF NOT EXISTS idx_experiments_path ON experiments(path);
CREATE INDEX IF NOT EXISTS idx_experiments_alias ON experiments(alias);
CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_experiments_created_desc ON experiments(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_experiments_best_metric ON experiments(best_metric_name, best_metric_value DESC);
CREATE INDEX IF NOT EXISTS idx_experiments_deleted ON experiments(deleted_at);
CREATE INDEX IF NOT EXISTS idx_experiments_active ON experiments(status, deleted_at) WHERE deleted_at IS NULL;

-- =====================================================
-- Metrics Time Series: High-performance metric storage
-- =====================================================
CREATE TABLE IF NOT EXISTS metrics (
    -- Composite primary key for uniqueness
    experiment_id TEXT NOT NULL,           -- Reference to experiment
    timestamp REAL NOT NULL,               -- Event timestamp
    metric_name TEXT NOT NULL,             -- Metric name (e.g., 'loss', 'accuracy')
    
    -- Metric data
    metric_value REAL,                     -- Metric value (NULL for NaN/Inf)
    step INTEGER,                          -- Training step number
    stage TEXT,                           -- Training stage ('warmup', 'train', 'eval')
    
    -- Metadata
    recorded_at REAL NOT NULL DEFAULT (unixepoch()), -- When this was recorded to DB
    
    PRIMARY KEY (experiment_id, timestamp, metric_name),
    FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
);

-- Optimized indexes for metric queries
CREATE INDEX IF NOT EXISTS idx_metrics_exp_metric ON metrics(experiment_id, metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_step ON metrics(experiment_id, step);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_stage ON metrics(stage);
CREATE INDEX IF NOT EXISTS idx_metrics_value ON metrics(metric_name, metric_value DESC);

-- =====================================================
-- Experiment Tags: Flexible tagging system
-- =====================================================
CREATE TABLE IF NOT EXISTS experiment_tags (
    experiment_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    created_at REAL NOT NULL DEFAULT (unixepoch()),
    created_by TEXT,                       -- Future: user who added the tag
    
    PRIMARY KEY (experiment_id, tag),
    FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tags_tag ON experiment_tags(tag);
CREATE INDEX IF NOT EXISTS idx_tags_experiment ON experiment_tags(experiment_id);

-- =====================================================
-- Environment Information: Reproducibility tracking
-- =====================================================
CREATE TABLE IF NOT EXISTS environments (
    experiment_id TEXT PRIMARY KEY,
    
    -- Git information
    git_commit TEXT,
    git_branch TEXT,
    git_dirty BOOLEAN,
    git_remote TEXT,
    git_last_commit_message TEXT,
    
    -- Python environment
    python_executable TEXT,
    pip_packages TEXT,                     -- JSON array of pip packages
    conda_env TEXT,
    conda_packages TEXT,                   -- JSON array of conda packages
    
    -- System information
    cpu_count INTEGER,
    memory_total_gb REAL,
    gpu_info TEXT,                         -- JSON array of GPU information
    
    -- Environment variables (ML-relevant only)
    env_variables TEXT,                    -- JSON object of key environment variables
    
    -- Capture metadata
    captured_at REAL NOT NULL DEFAULT (unixepoch()),
    
    FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
);

-- =====================================================
-- File References: Track files in file system
-- =====================================================
CREATE TABLE IF NOT EXISTS experiment_files (
    experiment_id TEXT NOT NULL,
    file_type TEXT NOT NULL,               -- 'log', 'media', 'environment', 'custom'
    file_path TEXT NOT NULL,               -- Relative path from run_dir
    file_size INTEGER,                     -- File size in bytes
    file_hash TEXT,                        -- Optional: file content hash
    created_at REAL NOT NULL DEFAULT (unixepoch()),
    
    PRIMARY KEY (experiment_id, file_type, file_path),
    FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_files_type ON experiment_files(file_type);
CREATE INDEX IF NOT EXISTS idx_files_experiment ON experiment_files(experiment_id);

-- =====================================================
-- Query Cache: Performance optimization
-- =====================================================
CREATE TABLE IF NOT EXISTS query_cache (
    cache_key TEXT PRIMARY KEY,
    query_result TEXT,                     -- JSON serialized result
    created_at REAL NOT NULL DEFAULT (unixepoch()),
    expires_at REAL NOT NULL,
    query_params TEXT,                     -- JSON serialized query parameters
    
    CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS idx_cache_expires ON query_cache(expires_at);

-- =====================================================
-- Analytics Views: Pre-computed analytics
-- =====================================================

-- Path summary view (replaces project_stats)
CREATE VIEW IF NOT EXISTS v_path_stats AS
SELECT 
    path,
    COUNT(*) as total_experiments,
    COUNT(CASE WHEN status = 'finished' THEN 1 END) as finished_count,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count,
    COUNT(CASE WHEN status = 'running' THEN 1 END) as running_count,
    AVG(CASE WHEN best_metric_value IS NOT NULL THEN best_metric_value END) as avg_best_metric,
    MAX(created_at) as last_experiment_time,
    MIN(created_at) as first_experiment_time,
    COUNT(CASE WHEN deleted_at IS NULL THEN 1 END) as active_count
FROM experiments 
GROUP BY path;

-- Best performing experiments view
CREATE VIEW IF NOT EXISTS v_best_experiments AS
SELECT 
    e.*,
    RANK() OVER (PARTITION BY path, best_metric_name ORDER BY 
        CASE WHEN best_metric_mode = 'max' THEN best_metric_value END DESC,
        CASE WHEN best_metric_mode = 'min' THEN best_metric_value END ASC
    ) as rank_in_path,
    RANK() OVER (PARTITION BY best_metric_name ORDER BY 
        CASE WHEN best_metric_mode = 'max' THEN best_metric_value END DESC,
        CASE WHEN best_metric_mode = 'min' THEN best_metric_value END ASC
    ) as global_rank
FROM experiments e
WHERE status = 'finished' 
  AND deleted_at IS NULL 
  AND best_metric_value IS NOT NULL;

-- Recent activity view
CREATE VIEW IF NOT EXISTS v_recent_activity AS
SELECT 
    id,
    path,
    alias,
    status,
    created_at,
    updated_at,
    best_metric_name,
    best_metric_value,
    CASE 
        WHEN updated_at > unixepoch() - 3600 THEN 'last_hour'
        WHEN updated_at > unixepoch() - 86400 THEN 'last_day' 
        WHEN updated_at > unixepoch() - 604800 THEN 'last_week'
        ELSE 'older'
    END as recency
FROM experiments
WHERE deleted_at IS NULL
ORDER BY updated_at DESC;

-- =====================================================
-- Storage Statistics: Monitor storage health
-- =====================================================
CREATE TABLE IF NOT EXISTS storage_stats (
    stat_name TEXT PRIMARY KEY,
    stat_value TEXT,                       -- JSON serialized value
    updated_at REAL NOT NULL DEFAULT (unixepoch())
);

-- Initial storage statistics
INSERT OR REPLACE INTO storage_stats (stat_name, stat_value) VALUES 
('schema_version', '"1.0"'),
('migration_status', '"file_only"'),
('created_at', json(unixepoch()));

-- =====================================================
-- Performance optimization: Write-Ahead Logging
-- =====================================================
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = memory;
PRAGMA mmap_size = 268435456;  -- 256MB memory map
PRAGMA cache_size = 10000;     -- 10MB cache
