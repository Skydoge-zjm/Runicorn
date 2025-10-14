# Runicorn Documentation System Overview

**Last Updated**: 2025-10-14  
**Purpose**: Complete overview of all documentation in the Runicorn project

---

## 📚 Documentation Categories

Runicorn has **two main documentation systems**, each serving different audiences:

```
Documentation/
│
├── 1. API Documentation (docs/api/)
│   └─ Target: Developers (integrators)
│   └─ Language: English
│   └─ Purpose: REST API technical reference
│
└── 2. User Guide (docs/user-guide/)
    └─ Target: End users (ML practitioners)
    └─ Language: English
    └─ Purpose: How to use Runicorn
```

---

## 1️⃣ API Documentation

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
| `ssh_api.md` | Remote sync | 12 |
| `runicorn_api.postman_collection.json` | Postman import | All |

**Total**: 34,000+ words, 90+ code examples

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

## 2️⃣ User Guide (Website)

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
| **API Docs** | 10 | 34,000+ | 90+ |
| **User Guide** | 40+ | TBD | 100+ |
| **Architecture** | 14 | 15,000+ | 50+ |
| **Total** | **64+** | **49,000+** | **240+** |

### Coverage

- ✅ **Python SDK**: 100% (all functions documented in user guide)
- ✅ **CLI Commands**: 100% (all commands documented)
- ✅ **REST API**: 100% (40+ endpoints documented)
- ✅ **Architecture**: 100% (system design documented)
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

**Maintained by**: Runicorn Documentation Team

