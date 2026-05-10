# Runicorn Documentation System Overview

- **Version**: v0.7.2
- **Last Updated**: 2026-05-11
- **Purpose**: Complete overview of all documentation in the Runicorn project

**Current release context**: v0.7.2 is a patch follow-up to the v0.7.1 stabilization release. The main product-facing changes are still the v0.7.1 reliability, remote API/documentation alignment, credential-boundary tightening, stronger CI/smoke coverage, and more reproducible desktop builds. v0.7.2 focuses on post-release packaging, CI, and cross-platform test fixes.

---

## 📚 Documentation Categories

Runicorn has **five main documentation systems**, each serving different audiences:

```
Documentation/
│
├── 1. User Guides (docs/guides/)
│   └─ Target: All users
│   └─ Language: English/Chinese
│   └─ Purpose: Tutorials, quickstart, migration guides
│
├── 2. Reference Docs (docs/reference/)
│   └─ Target: All users
│   └─ Language: English/Chinese
│   └─ Purpose: Configuration, CLI, FAQ
│
├── 3. Architecture Docs (docs/architecture/)
│   └─ Target: Developers, contributors
│   └─ Language: English/Chinese
│   └─ Purpose: System design, Remote Viewer architecture
│
├── 4. API Documentation (docs/api/)
│   └─ Target: Developers (integrators)
│   └─ Language: English/Chinese
│   └─ Purpose: REST API technical reference
│
└── 5. User Guide Website (docs/user-guide/)
    └─ Target: End users (ML practitioners)
    └─ Language: English
    └─ Purpose: MkDocs-based comprehensive guide
```

---

## 1️⃣ User Guides

**Location**: `docs/guides/`
**Audience**: All users
**Format**: Markdown
**Language**: English/Chinese

### Purpose

Practical guides for:
- Getting started with Runicorn
- Using Remote Viewer (v0.5.0)
- Working with assets, snapshots, and reusable training context
- Migrating from 0.4.x to 0.5.0
- Example code walkthroughs

### Documents

| Document | Purpose | Language |
|----------|---------|----------|
| `QUICKSTART.md` | 5-minute quick start | EN/ZH |
| `REMOTE_STORAGE_USER_GUIDE.md` | Deprecated remote storage reference | EN/ZH |
| `REMOTE_VIEWER_GUIDE.md` | ⭐ Remote Viewer usage (v0.5.0) | EN/ZH |
| `ENHANCED_LOGGING_GUIDE.md` | ⭐ Console capture, logging handler, MetricLogger | EN/ZH |
| `ASSETS_GUIDE.md` | ⭐ Workspace snapshots and asset tracking | EN/ZH |
| `MIGRATION_GUIDE_v0.4_to_v0.5.md` | Migration guide (v0.5.0) | EN/ZH |
| `DEMO_EXAMPLES_GUIDE.md` | Example code explanations | EN/ZH |

**Total**: 7 guides × 2 languages = 14 files

> ⚠️ `REMOTE_STORAGE_USER_GUIDE.md` (deprecated in v0.5.0) still exists for reference but is no longer recommended. Use Remote Viewer instead.

### Features

- ✅ Step-by-step tutorials
- ✅ Complete code examples
- ✅ Troubleshooting tips
- ✅ Bilingual (EN/ZH)
- ✅ Remote Viewer comprehensive coverage

---

## 2️⃣ Reference Documentation

**Location**: `docs/reference/`
**Audience**: All users
**Format**: Markdown
**Language**: English/Chinese

### Purpose

Technical reference for:
- Complete configuration options
- All CLI commands
- Frequently asked questions
- Rate limiting configuration

### Documents

| Document | Purpose | Language |
|----------|---------|----------|
| `CONFIGURATION.md` | ⭐ Complete config reference | EN/ZH |
| `CLI_REFERENCE.md` | ⭐ All CLI commands | EN/ZH |
| `FAQ.md` | ⭐ 30+ common questions (v0.5.0) | EN/ZH |
| `RATE_LIMIT_CONFIGURATION.md` | Rate limiting setup | EN/ZH |

**Total**: 4 references × 2 languages = 8 files

### Features

- ✅ Exhaustive configuration docs
- ✅ Command-line reference
- ✅ 30+ FAQ entries
- ✅ Troubleshooting guides
- ✅ Environment variables

---

## 3️⃣ Architecture Documentation

**Location**: `docs/architecture/`
**Audience**: Developers, contributors
**Format**: Markdown
**Language**: English/Chinese

### Purpose

System design documentation:
- System architecture overview
- Remote Viewer architecture (v0.5.0)
- Component design
- Data flow
- Storage design
- API design
- Frontend architecture
- Deployment options
- Design decisions

### Documents

| Document | Purpose | Language |
|----------|---------|----------|
| `SYSTEM_OVERVIEW.md` | High-level architecture | EN/ZH |
| `REMOTE_VIEWER_ARCHITECTURE.md` | ⭐ Remote Viewer design (v0.5.0) | EN/ZH |
| `SSH_BACKEND_ARCHITECTURE.md` | ⭐ SSH backend multi-fallback design | EN/ZH |
| `COMPONENT_ARCHITECTURE.md` | Component design | EN/ZH |
| `STORAGE_DESIGN.md` | Storage architecture | EN/ZH |
| `DATA_FLOW.md` | Data processing pipeline | EN/ZH |
| `API_DESIGN.md` | API layer design | EN/ZH |
| `FRONTEND_ARCHITECTURE.md` | Frontend design | EN/ZH |
| `DEPLOYMENT.md` | Deployment options | EN/ZH |
| `DESIGN_DECISIONS.md` | Technical decisions | EN/ZH |

**Total**: 10 docs × 2 languages = 20 files

### Features

- ✅ Complete system design
- ✅ Remote Viewer deep dive
- ✅ Architecture diagrams
- ✅ Design rationale
- ✅ Implementation details

---

## 4️⃣ API Documentation

**Location**: `docs/api/`
**Audience**: Developers building integrations
**Format**: Markdown (API spec)
**Language**: English/Chinese
**Access**: File-based or via FastAPI auto-docs

### Purpose

Technical reference for:
- REST API endpoints
- Request/response formats
- Error codes
- Authentication
- Rate limiting
- Code examples in multiple languages

### Documents

| Document | Purpose | Endpoints |
|----------|---------|-----------|
| `README.md` | API overview | - |
| `QUICK_REFERENCE.md` | Quick lookup | All |
| `API_INDEX.md` | Complete index | REST + Python Client |
| `python_client_api.md` | Python client usage | SDK |
| `runs_api.md` | Experiment CRUD | 6 |
| `metrics_api.md` | Metrics & logs | 4 |
| `config_api.md` | Configuration | 6 |
| `ssh_api.md` | Remote sync (deprecated) | 12 |
| `remote_api.md` | ⭐ Remote Viewer API (v0.5.0+) | 8+ |
| `REMOTE_API_EXAMPLES.md` | Remote Viewer examples | Examples |
| `logging_api.md` | ⭐ Enhanced Logging API | SDK |
| `paths_api.md` | ⭐ Path-based Hierarchy API | 5 |
| `runicorn_api.postman_collection.json` | Postman import | All |

**Total**: 12 API modules × 2 languages, plus a shared Postman collection
**Content**: 50,000+ words, 150+ code examples

### Features

- ✅ Standard REST API documentation format
- ✅ OpenAPI/Swagger compatible
- ✅ cURL, Python, JavaScript examples
- ✅ Postman collection included
- ✅ Error handling documentation
- ✅ Rate limiting specifications

### When to Update

- ✅ API endpoint changes (added/modified/deprecated)
- ✅ Request/response format changes
- ✅ New error codes
- ✅ Authentication changes
- ❌ Internal implementation changes (unless affects API behavior)

### Access

**Static files**:
```bash
docs/api/README.md
```

**Interactive** (when viewer running):
```
http://127.0.0.1:23300/docs  # Swagger UI
http://127.0.0.1:23300/redoc # ReDoc alternative
```

---

## 5️⃣ User Guide (Website)

**Location**: `docs/user-guide/`
**Audience**: End users (ML researchers, data scientists)
**Format**: MkDocs (Material theme)
**Language**: English
**Hosting**: GitHub Pages

### Purpose

User-facing documentation:
- Installation instructions
- Python SDK usage
- CLI commands
- Web UI guides
- Step-by-step tutorials
- Troubleshooting

### Structure

```
docs/user-guide/
├── mkdocs.yml               # Site configuration
├── requirements.txt         # Python dependencies
├── docs/                    # Documentation source
│   ├── index.md            # Homepage
│   ├── getting-started/    # Quickstart, installation
│   ├── sdk/                # Python SDK reference
│   ├── cli/                # CLI reference
│   ├── ui/                 # Web UI guide
│   ├── tutorials/          # Step-by-step tutorials
│   ├── reference/          # FAQ, glossary, best practices
│   └── assets/             # Images, screenshots
│
└── .github/workflows/
    └── deploy-docs.yml     # Auto-deployment
```

### Features

- ✅ Beautiful Material Design theme
- ✅ Responsive (mobile-friendly)
- ✅ Full-text search
- ✅ Dark/light mode
- ✅ Syntax highlighting
- ✅ Copy code buttons
- ✅ Emoji support
- ✅ Mermaid diagrams
- ✅ Auto-deployment via GitHub Actions

### When to Update

- ✅ New features released
- ✅ CLI commands added/changed
- ✅ SDK functions added/changed
- ✅ Common questions from users
- ✅ Tutorial requests
- ❌ Internal code refactoring (unless changes user-facing behavior)

### Access

**Online** (after deployment):
```
https://Skydoge-zjm.github.io/runicorn
```

**Local preview**:
```bash
cd docs/user-guide
mkdocs serve
# Open http://127.0.0.1:8000
```

---

## 🎯 Documentation for Different Audiences

### New User (Never used Runicorn)

**Start here**:
1. `docs/user-guide/` → Homepage
2. Getting Started → Quick Start
3. Your First Experiment
4. SDK Overview

**Goal**: Running first experiment in 10 minutes

---

### ML Practitioner (Daily use)

**Use**:
1. `docs/user-guide/` → Tutorials
2. SDK Reference
3. CLI Reference
4. FAQ for common issues

**Goal**: Efficient experiment tracking

---

### Developer (Building integrations)

**Use**:
1. `docs/api/` → API Overview
2. Specific module docs (runs_api.md, etc.)
3. Postman collection for testing
4. Code examples

**Goal**: Integrate Runicorn into their tools

---

### Contributor (Open source)

**Use**:
1. `docs/architecture/en/SYSTEM_OVERVIEW.md` → Understand system design
2. `CONTRIBUTING.md` → Contribution process
3. `docs/api/` → Understand APIs
4. Code in `src/runicorn/` → Review implementation

**Goal**: Submit quality PRs

---

## 📊 Documentation Statistics

### Total Documentation

| Category | Files | Words | Code Examples |
|----------|-------|-------|---------------|
| **User Guides** | 14 | 15,000+ | 50+ |
| **Reference Docs** | 8 | 15,000+ | 60+ |
| **Architecture** | 20 | 25,000+ | 40+ |
| **API Docs** | 30 | 50,000+ | 150+ |
| **User Guide (Website)** | 40+ | TBD | 100+ |
| **Total** | **112+** | **105,000+** | **400+** |

### Coverage

- ✅ **Python SDK**: 100% (all functions documented)
- ✅ **CLI Commands**: 100% (comprehensive CLI reference)
- ✅ **REST API**: 100% (50+ endpoints including Remote API, Paths API, Logging API)
- ✅ **Architecture**: 100% (including Remote Viewer, SSH Backend architecture)
- ✅ **Configuration**: 100% (complete config reference)
- ✅ **FAQ**: 100% (30+ questions answered)
- ✅ **Migration**: 100% (0.4→0.5 guide complete)
- ✅ **Web UI**: ~70% (core features documented)
- ⏳ **Tutorials**: ~40% (4 complete; coverage is still partial)

---

**Maintained by**: Runicorn Documentation Team

