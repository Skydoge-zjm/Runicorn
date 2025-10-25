[English](DESIGN_DECISIONS.md) | [简体中文](../zh/DESIGN_DECISIONS.md)

---

# Design Decisions

**Document Type**: Architecture  
**Purpose**: Document key technical decisions and their rationale

---

## Storage Architecture

### Decision: Hybrid SQLite + File System

**Context**: Need to store both structured metadata and large binary files.

**Alternatives Considered**:
1. **Pure File System** (v0.1-v0.2 approach)
   - Simple, human-readable
   - Slow queries (5-10s for 1000 experiments)
   
2. **Pure SQLite**
   - Fast queries
   - Not suitable for large files (100MB+ models)
   
3. **External Database** (PostgreSQL, MySQL)
   - Best performance for queries
   - Requires server setup, complex for users

**Decision**: Hybrid (SQLite + Files)

**Rationale**:
- SQLite: Fast queries, zero setup, portable
- Files: Natural for large blobs, Git-friendly
- Best of both worlds

**Trade-offs**:
- ✅ 100x faster queries vs pure files
- ✅ No setup vs external DB
- ⚠️ Dual-write complexity
- ⚠️ Single-machine limitation (acceptable for target use case)

---

## Content Deduplication

### Decision: SHA256-based with Hard Links

**Context**: ML models often share pretrained weights, consuming massive storage.

**Alternatives Considered**:
1. **No deduplication**
   - Simple
   - 100GB for 100 checkpoints
   
2. **Git-LFS**
   - Industry standard
   - External dependency, server required
   
3. **Compression** (gzip, zstd)
   - Reduces size
   - CPU cost, still redundant storage
   
4. **Block-level dedup** (ZFS, btrfs)
   - OS-level
   - Not portable, requires specific filesystem

**Decision**: Content-based dedup with hard links

**Rationale**:
- SHA256: Secure, fast, negligible collision risk
- Hard links: Zero-copy, OS-supported
- Works on all platforms (with fallback to copy)

**Trade-offs**:
- ✅ 50-90% space savings
- ✅ Zero CPU overhead after hash
- ⚠️ Cross-filesystem limitation (same drive/filesystem)
- ⚠️ Windows requires admin for hard links (fallback to copy)

---

## API Framework

### Decision: FastAPI over Flask/Django

**Context**: Need async-capable, modern API framework.

**Alternatives Considered**:
1. **Flask**
   - Simple, widely used
   - Sync-only, manual docs, slower
   
2. **Django + DRF**
   - Full-featured
   - Heavy, opinionated, overkill for API-only
   
3. **aiohttp**
   - Pure async
   - Lower-level, more boilerplate

**Decision**: FastAPI

**Rationale**:
- Auto-generated OpenAPI docs (Swagger/ReDoc)
- Native async/await support
- Pydantic validation (type-safe)
- Fast (comparable to Node.js/Go)
- Modern Python 3.8+ features

**Trade-offs**:
- ✅ Best developer experience
- ✅ Auto documentation
- ⚠️ Newer (less mature than Flask)
- ⚠️ Learning curve for async patterns

---

## Frontend Framework

### Decision: React + Ant Design

**Context**: Need modern, component-based UI with professional appearance.

**Alternatives Considered**:
1. **Vue.js**
   - Simpler learning curve
   - Smaller ecosystem for enterprise UI

2. **Angular**
   - Full framework
   - Heavyweight, steep learning curve

3. **Svelte**
   - Innovative, fast
   - Smaller ecosystem

**Decision**: React 18 + Ant Design 5

**Rationale**:
- React: Largest ecosystem, proven for complex UIs
- Ant Design: Enterprise-grade components, i18n built-in
- TypeScript: Type safety, better refactoring
- Vite: Fast dev experience

**Trade-offs**:
- ✅ Best ecosystem and component library
- ✅ Professional appearance out-of-box
- ⚠️ Bundle size larger than Svelte
- ⚠️ More boilerplate than Vue

---

## Database Choice

### Decision: SQLite over PostgreSQL/MySQL

**Context**: Need queryable metadata storage.

**Alternatives Considered**:
1. **PostgreSQL**
   - Best performance
   - Requires server, complex setup
   
2. **MySQL/MariaDB**
   - Good performance
   - Requires server
   
3. **MongoDB**
   - Flexible schema
   - Requires server, different query model
   
4. **In-memory** (Redis, Memcached)
   - Fastest
   - Not persistent

**Decision**: SQLite with WAL mode

**Rationale**:
- Zero setup: Single file database
- Portable: Works everywhere Python works
- ACID: Transaction safety
- Good enough: Handles 100k+ experiments
- Bundled: No external dependencies

**Trade-offs**:
- ✅ Best for single-machine, self-hosted
- ✅ Zero configuration
- ✅ Easy backup (copy one file)
- ⚠️ Not for distributed systems
- ⚠️ Concurrent write limitations (mitigated by WAL)

---

## Versioning Strategy

### Decision: Automatic Sequential Versions (v1, v2, v3...)

**Context**: Need simple, predictable versioning for ML assets.

**Alternatives Considered**:
1. **Semantic Versioning** (1.0.0, 1.1.0)
   - Industry standard for software
   - Complex for ML (what's major vs minor?)
   
2. **Git-like hashes**
   - Unique, distributed
   - Not user-friendly
   
3. **Timestamps**
   - Automatic
   - Hard to reference ("the 2AM version")
   
4. **User-defined**
   - Full control
   - Risk of conflicts, inconsistency

**Decision**: Sequential integers + optional aliases

**Rationale**:
- Simple: v1, v2, v3 easy to understand
- Predictable: No conflicts
- Flexible: Aliases for semantic meaning (latest, production)
- ML-appropriate: Experiments are sequential

**Trade-offs**:
- ✅ Simplest mental model
- ✅ No version conflicts
- ⚠️ Requires coordination for parallel saves (handled by locks)

---

## Desktop App Approach

### Decision: Tauri over Electron

**Context**: Need native Windows desktop application.

**Alternatives Considered**:
1. **Electron**
   - Most popular
   - Heavy (~100MB+ app size)
   - Chromium embedded
   
2. **Qt/PyQt**
   - Native look
   - Different UI code from web
   
3. **PWA** (Progressive Web App)
   - No installation
   - Limited OS integration

**Decision**: Tauri

**Rationale**:
- Lightweight: 3-5MB vs 100MB (Electron)
- Secure: Rust backend, sandboxed
- Reuse web UI: Same codebase
- Modern: Active development

**Trade-offs**:
- ✅ 95% smaller than Electron
- ✅ More secure
- ⚠️ Newer (less mature)
- ⚠️ Requires Rust toolchain for building

---

## Remote Sync Strategy

### Decision: SSH-based Metadata Sync

**Context**: Users train on remote servers, want to view locally.

**Alternatives Considered**:
1. **Full rsync**
   - Complete sync
   - Slow for large datasets (hours)
   
2. **Cloud storage** (S3, GCS)
   - Scalable
   - External dependency, cost
   
3. **Custom protocol**
   - Optimized
   - Requires server-side daemon
   
4. **Database replication**
   - Efficient
   - Complex setup

**Decision**: SSH + Metadata-only sync

**Rationale**:
- SSH: Universal, secure, no special setup
- Metadata-only: Fast (MB vs GB)
- On-demand download: User controls bandwidth
- SFTP: Standard protocol

**Trade-offs**:
- ✅ Works with any SSH server
- ✅ 99% less data to sync
- ⚠️ Requires SSH access
- ⚠️ Files not immediately available (must download)

---

## Internationalization

### Decision: i18next + Separate Language Files

**Context**: Support Chinese and English users.

**Alternatives Considered**:
1. **Hardcoded strings**
   - Simple
   - No i18n
   
2. **gettext** (Python standard)
   - Standard for Python
   - Awkward for React
   
3. **react-intl**
   - React-specific
   - More verbose
   
4. **Inline translations**
   - Simple
   - Unmaintainable

**Decision**: i18next with JSON translation files

**Rationale**:
- Works in both Python and React
- Mature, well-supported
- Clean separation of code and translations
- Browser language detection

**Trade-offs**:
- ✅ Professional i18n solution
- ✅ Easy to add languages
- ⚠️ Separate translation files to maintain

---

## Why Not...?

### Why not use TensorBoard format?

- TensorBoard: Great for visualization, poor for management
- Runicorn: Visualization + version control + collaboration
- TensorBoard can still be used alongside

### Why not integrate with W&B/MLflow?

- Focus: Local-first, privacy-first
- Complexity: Integration adds dependencies
- Philosophy: Self-hosted alternative, not extension
- Future: May add export to these formats

### Why not GraphQL?

- REST: Simpler, more widely understood
- FastAPI: Excellent REST support
- Complexity: GraphQL adds overhead
- Future: May add GraphQL layer in v0.5+

### Why not microservices?

- Scale: Single-machine target doesn't benefit
- Complexity: Overkill for project size
- Deployment: Complicates user setup
- Simplicity: Monolith easier to develop and debug

---

## Lessons Learned

### What Worked Well

1. **Hybrid storage**: Performance + simplicity balance
2. **Content dedup**: Massive space savings, users love it
3. **FastAPI**: Auto-docs invaluable
4. **React + Ant Design**: Professional UI quickly

### What We'd Do Differently

1. **Earlier V2 API**: Should have started with SQLite
2. **More modular**: Some tight coupling in early code
3. **Testing**: Wish we had more integration tests earlier

---

## Remote Viewer Architecture (v0.5.0)

### Decision: Remote Viewer vs File Sync

**Context**: Users need to view experiment data on remote servers (GPU servers) from local machines.

**Alternatives Considered**:
1. **SSH File Sync** (v0.4.x approach) - Sync remote files to local - Issues: Slow for large models, space consumption, not real-time, conflicts
2. **Network File System** (NFS, SMB) - Mount remote directory - Issues: Admin rights needed, complex setup, cross-platform issues
3. **Cloud Hosting** (Self-hosted server) - Run Viewer on remote, HTTP access - Issues: Port exposure, security risks, auth system needed
4. **VNC/RDP** (Remote desktop) - Issues: Full desktop overhead, high latency, poor experience

**Decision**: Remote Viewer (VSCode Remote-style)

**Approach**: Start temporary Viewer on remote (127.0.0.1 only), SSH tunnel for port forwarding, local browser access

**Rationale**:
- ✅ **Zero sync**: No file transfer, direct access
- ✅ **Real-time**: Training data instantly visible
- ✅ **Secure**: SSH encryption, no port exposure
- ✅ **Simple**: Only SSH credentials needed
- ✅ **Low latency**: 50-100ms added (acceptable)
- ✅ **Space saving**: Zero local usage
- ✅ **Auto cleanup**: Automatic resource cleanup

**Tradeoffs**:
- ✅ 100x faster startup than file sync (5s vs 5min)
- ✅ Real-time vs re-sync needed
- ✅ Zero local storage vs GB usage
- ⚠️ Remote needs full Runicorn install (not just SDK)
- ⚠️ SSH access required
- ⚠️ Small latency increase (but much lower than VNC/RDP)

**Inspiration**: VSCode Remote Development success.

---

### Decision: Automatic Environment Detection

**Context**: Remote servers may have multiple Python environments (conda, virtualenv, etc.).

**Alternatives**: Manual path specification (poor UX), system Python only (often fails)

**Decision**: Auto-detect all environments

**Implementation**: Scan conda (`conda env list`), virtualenv (common paths), check each with `python -c "import runicorn; print(__version__)"`, show only compatible

**Rationale**:
- ✅ Zero-config UX
- ✅ Auto-filter incompatible environments
- ✅ Support all common environment managers
- ⚠️ Detection takes 2-5 seconds (first time only)

---

### Decision: SSH Tunnel vs Direct HTTP

**Context**: How to let local browser access remote Viewer?

**Alternatives**: Direct HTTP (security risks), VPN (not all users have)

**Decision**: SSH port forwarding (Local Forwarding)

**Implementation**: `Local port 8081 -> SSH tunnel -> Remote 127.0.0.1:23300`

**Rationale**:
- ✅ Leverage existing SSH connection
- ✅ Auto-encrypted (SSH protocol)
- ✅ No extra port opening
- ✅ No auth needed in Viewer
- ✅ All platforms support (SSH standard)
- ⚠️ Need to keep SSH connection (auto-reconnect implemented)

---

## References

For implementation details, see:
- [STORAGE_DESIGN.md](STORAGE_DESIGN.md) - Storage implementation
- [API_DESIGN.md](API_DESIGN.md) - API implementation
- [COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md) - Component details
- [REMOTE_VIEWER_ARCHITECTURE.md](REMOTE_VIEWER_ARCHITECTURE.md) - Remote Viewer detailed design

---

**Back to**: [Architecture Index](README.md)


