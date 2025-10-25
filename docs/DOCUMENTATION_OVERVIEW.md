# Runicorn Documentation System Overview

**Version**: v0.5.0  
**Last Updated**: 2025-10-25  
**Purpose**: Complete overview of all documentation in the Runicorn project

**v0.5.0 Highlights**: Remote Viewer documentation, comprehensive reference docs (Config/CLI/FAQ), migration guide

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
- Model versioning with Artifacts
- Migrating from 0.4.x to 0.5.0
- Example code walkthroughs

### Documents

| Document | Purpose | Language |
|----------|---------|----------|
| `QUICKSTART.md` | 5-minute quick start | EN/ZH |
| `REMOTE_VIEWER_GUIDE.md` | ⭐ Remote Viewer usage (v0.5.0) | EN/ZH |
| `ARTIFACTS_GUIDE.md` | Model versioning | EN/ZH |
| `MIGRATION_GUIDE_v0.4_to_v0.5.md` | ⭐ Migration guide (v0.5.0) | EN/ZH |
| `DEMO_EXAMPLES_GUIDE.md` | Example code explanations | EN/ZH |

**Total**: 6 guides × 2 languages = 12 files

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
| `CONFIGURATION.md` | ⭐ Complete config reference (v0.5.0) | EN/ZH |
| `CLI_REFERENCE.md` | ⭐ All CLI commands (v0.5.0) | EN/ZH |
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
| `COMPONENT_ARCHITECTURE.md` | Component design | EN/ZH |
| `STORAGE_DESIGN.md` | Storage architecture | EN/ZH |
| `DATA_FLOW.md` | Data processing pipeline | EN/ZH |
| `API_DESIGN.md` | API layer design | EN/ZH |
| `FRONTEND_ARCHITECTURE.md` | Frontend design | EN/ZH |
| `DEPLOYMENT.md` | Deployment options | EN/ZH |
| `DESIGN_DECISIONS.md` | Technical decisions | EN/ZH |

**Total**: 9 docs × 2 languages = 18 files

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
**Language**: English  
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
| `API_INDEX.md` | Complete index | 40+ |
| `runs_api.md` | Experiment CRUD | 6 |
| `artifacts_api.md` | Model versioning | 7 |
| `v2_api.md` | High-performance queries | 4 |
| `metrics_api.md` | Metrics & logs | 4 |
| `config_api.md` | Configuration | 6 |
| `ssh_api.md` | Remote sync (deprecated) | 12 |
| `remote_api.md` | ⭐ Remote Viewer API (v0.5.0) | 8+ |
| `runicorn_api.postman_collection.json` | Postman import | All |

**Total**: 13 API modules × 2 languages = 26 files  
**Content**: 45,000+ words, 120+ code examples

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
├── DEPLOYMENT_GUIDE.md      # Deployment instructions
│
├── docs/                    # Documentation source
│   ├── index.md            # Homepage
│   ├── getting-started/    # Quickstart, installation
│   ├── sdk/                # Python SDK reference
│   ├── cli/                # CLI reference
│   ├── ui/                 # Web UI guide
│   ├── tutorials/          # Step-by-step tutorials
│   ├── guides/             # How-to guides
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
https://yourusername.github.io/runicorn
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
1. `docs/ARCHITECTURE.md` → Understand system design
2. `CONTRIBUTING.md` → Contribution process
3. `docs/api/` → Understand APIs
4. Code in `src/runicorn/` → Review implementation

**Goal**: Submit quality PRs

---

## 📊 Documentation Statistics

### Total Documentation

| Category | Files | Words | Code Examples |
|----------|-------|-------|---------------|
| **User Guides** | 12 | 12,000+ | 40+ |
| **Reference Docs** | 8 | 15,000+ | 60+ |
| **Architecture** | 18 | 20,000+ | 30+ |
| **API Docs** | 26 | 45,000+ | 120+ |
| **User Guide (Website)** | 40+ | TBD | 100+ |
| **Total** | **104+** | **92,000+** | **350+** |

### Coverage

- ✅ **Python SDK**: 100% (all functions documented)
- ✅ **CLI Commands**: 100% (comprehensive CLI reference)
- ✅ **REST API**: 100% (48+ endpoints including Remote API)
- ✅ **Architecture**: 100% (including Remote Viewer architecture)
- ✅ **Configuration**: 100% (complete config reference)
- ✅ **FAQ**: 100% (30+ questions answered)
- ✅ **Migration**: 100% (0.4→0.5 guide complete)
- ✅ **Web UI**: ~60% (core features documented)
- ⏳ **Tutorials**: ~30% (3 complete, more planned)

---

## 🔄 Maintenance Workflow

### Regular Updates

**Weekly**:
- [ ] Check for user questions → Update FAQ
- [ ] Review GitHub issues → Add to troubleshooting
- [ ] Test all code examples still work

**Per Release**:
- [ ] Update version numbers
- [ ] Document new features
- [ ] Update API docs for endpoint changes
- [ ] Add release notes to user guide
- [ ] Update screenshots if UI changed

**As Needed**:
- [ ] Fix broken links
- [ ] Update deprecated content
- [ ] Improve unclear explanations
- [ ] Add requested tutorials

### Quality Checks

**Before deploying**:
```bash
# Build with strict mode (fails on warnings)
cd docs/user-guide
mkdocs build --strict

# Check for broken links
# (Use link checker tool)

# Spell check
# (Use spell checker on markdown files)

# Test code examples
python test_all_examples.py
```

---

## 🚀 Deployment Status

### Current Deployments

| Documentation | Status | URL | Auto-Deploy |
|---------------|--------|-----|-------------|
| API Docs (Static) | ✅ File-based | `docs/api/` | No (static files) |
| API Docs (Interactive) | ✅ Runtime | `http://127.0.0.1:23300/docs` | Yes (FastAPI) |
| User Guide | 🔄 Pending | GitHub Pages | Yes (GitHub Actions) |
| Architecture Docs | ✅ File-based | `docs/` | No (static files) |

### Setup GitHub Pages

See [DEPLOYMENT_GUIDE.md](user-guide/DEPLOYMENT_GUIDE.md) for step-by-step instructions.

**Quick command**:
```bash
cd docs/user-guide
mkdocs gh-deploy --force
```

---

## 🎓 Documentation Best Practices

### Writing Style

- ✅ Use simple, clear language
- ✅ Provide context before technical details
- ✅ Include working code examples
- ✅ Add screenshots for UI features
- ✅ Use admonitions for important notes
- ❌ Avoid jargon without explanation
- ❌ Don't assume prior knowledge

### Code Examples

```python
# ✅ Good: Complete, runnable example
import runicorn as rn

run = rn.init(project="demo")
rn.log({"loss": 0.1}, step=1)
rn.finish()

# ❌ Bad: Incomplete, won't run
rn.log(loss)  # Where does 'loss' come from?
```

### Navigation

- ✅ Clear hierarchy (max 3 levels)
- ✅ Logical grouping
- ✅ Cross-references between related topics
- ✅ "Next steps" at end of each page

---

## 📞 Contact

- **Documentation issues**: [GitHub Issues](https://github.com/yourusername/runicorn/issues) with `docs` label
- **Feature requests**: [GitHub Discussions](https://github.com/yourusername/runicorn/discussions)
- **Security issues**: See [SECURITY.md](../SECURITY.md)

---

## 🎉 Summary

Runicorn has **comprehensive, multi-layered documentation**:

1. **API Docs** (docs/api/) - For developers and integrators
2. **User Guide** (docs/user-guide/) - For end users and ML practitioners
3. **Architecture** (docs/) - For contributors and maintainers

Each system serves its audience with appropriate depth, language, and format.

---

**Next Steps**:

- 📖 Review [User Guide Deployment Guide](user-guide/DEPLOYMENT_GUIDE.md)
- 🚀 Deploy to GitHub Pages
- 📣 Share documentation URL with users

---

**v0.5.0 Documentation Additions**:
- ⭐ Remote Viewer complete documentation (user guide + architecture)
- ⭐ Configuration reference (50+ options)
- ⭐ CLI reference (6 commands, 30+ options)
- ⭐ FAQ (30+ questions)
- ⭐ Migration guide (0.4.x → 0.5.0)
- ⭐ Remote API documentation (8+ endpoints)
- ⭐ All docs now bilingual (English/Chinese)

---

**Maintained by**: Runicorn Documentation Team

