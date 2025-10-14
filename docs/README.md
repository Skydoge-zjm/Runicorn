[English](README.md) | [简体中文](README_zh.md)

---

# Runicorn Documentation

**Version**: v0.4.0  
**Last Updated**: 2025-10-14

---

## 📚 Documentation Structure

```
docs/
├── api/                    # REST API Technical Reference (for developers)
├── user-guide/             # User Guide Website (for end users)
├── ARCHITECTURE.md         # System architecture overview
├── ARTIFACTS_GUIDE.md      # Artifacts system guide
├── QUICKSTART.md           # Quick start guide
├── SECURITY_AUDIT_REPORT.md# Security audit and best practices
├── REMOTE_STORAGE_USER_GUIDE.md # Remote sync user guide
├── RATE_LIMIT_CONFIGURATION.md  # Rate limiting configuration
├── DEMO_EXAMPLES_GUIDE.md  # Example code guide
├── RELEASE_NOTES_v0.4.0.md # Release notes
├── CHANGELOG_ARCHIVE.md    # Development history archive
├── DOCUMENTATION_OVERVIEW.md # Complete documentation system overview
└── picture/                # Screenshots and images
```

---

## 🎯 Quick Links

### For End Users

📖 **[User Guide Website](user-guide/)** - Complete usage documentation

- Installation and setup
- Python SDK reference
- CLI commands
- Web UI guide
- Step-by-step tutorials

**Deploy to GitHub Pages**: See [user-guide/mkdocs.yml](user-guide/mkdocs.yml)

---

### For Developers/Integrators

🔌 **[API Documentation](api/)** - REST API reference

- Complete endpoint documentation
- Request/response schemas
- Code examples (cURL, Python, JavaScript)
- Postman collection
- Performance benchmarks

**Interactive API Docs**: Start viewer and visit `http://127.0.0.1:23300/docs`

---

### For Contributors

🤝 **Contributing Guide** - See `../CONTRIBUTING.md`

- Code style and conventions
- Development setup
- Pull request process
- Testing requirements

---

## 📖 Core Documentation

### Getting Started

- **[guides/](guides/)** - User guides and tutorials
  - [QUICKSTART.md](guides/en/QUICKSTART.md) - 5-minute quick start
  - [ARTIFACTS_GUIDE.md](guides/en/ARTIFACTS_GUIDE.md) - Model versioning
  - [REMOTE_STORAGE_USER_GUIDE.md](guides/en/REMOTE_STORAGE_USER_GUIDE.md) - Remote sync
  - [DEMO_EXAMPLES_GUIDE.md](guides/en/DEMO_EXAMPLES_GUIDE.md) - Examples
- **[user-guide/](user-guide/)** - Complete user documentation website (MkDocs)

### Architecture

- **[architecture/](architecture/)** - System architecture documentation
  - [SYSTEM_OVERVIEW.md](architecture/en/SYSTEM_OVERVIEW.md) - High-level architecture
  - [COMPONENT_ARCHITECTURE.md](architecture/en/COMPONENT_ARCHITECTURE.md) - Component design
  - [STORAGE_DESIGN.md](architecture/en/STORAGE_DESIGN.md) - Storage architecture
  - [DATA_FLOW.md](architecture/en/DATA_FLOW.md) - Data processing pipeline
  - [API_DESIGN.md](architecture/en/API_DESIGN.md) - API layer design
  - [FRONTEND_ARCHITECTURE.md](architecture/en/FRONTEND_ARCHITECTURE.md) - Frontend design
  - [DEPLOYMENT.md](architecture/en/DEPLOYMENT.md) - Deployment options
  - [DESIGN_DECISIONS.md](architecture/en/DESIGN_DECISIONS.md) - Technical decisions

### API Documentation

- **[api/](api/)** - REST API reference
  - [README.md](api/en/README.md) - API overview
  - [QUICK_REFERENCE.md](api/en/QUICK_REFERENCE.md) - Quick lookup
  - [API_INDEX.md](api/en/API_INDEX.md) - Complete endpoint index
  - Module docs: runs, artifacts, v2, metrics, config, ssh

### Reference

- **[reference/](reference/)** - Technical reference materials
  - [RATE_LIMIT_CONFIGURATION.md](reference/en/RATE_LIMIT_CONFIGURATION.md) - Rate limiting config

### Releases

- **[releases/](releases/)** - Release information
  - [RELEASE_NOTES_v0.4.0.md](releases/en/RELEASE_NOTES_v0.4.0.md) - v0.4.0 notes

---

## 🗂️ Documentation by Audience

### I'm a User

**Start here**:
1. [QUICKSTART.md](QUICKSTART.md) - Get started in 5 minutes
2. [user-guide/](user-guide/) - Full user documentation
3. [ARTIFACTS_GUIDE.md](ARTIFACTS_GUIDE.md) - Learn model versioning

**Online**: Visit GitHub Pages (after deployment)

---

### I'm a Developer

**Start here**:
1. [api/README.md](api/README.md) - API overview
2. [api/QUICK_REFERENCE.md](api/QUICK_REFERENCE.md) - Quick API reference
3. Specific module docs in `api/`

**Interactive**: `http://127.0.0.1:23300/docs` (Swagger UI)

---

### I'm a Contributor

**Start here**:
1. [ARCHITECTURE.md](ARCHITECTURE.md) - Understand the system
2. [DOCUMENTATION_OVERVIEW.md](DOCUMENTATION_OVERVIEW.md) - Complete documentation map
3. `../CONTRIBUTING.md` - Contribution guidelines
4. Code in `src/runicorn/` - Review implementation

---

## 📦 Additional Resources

### Examples

Located in `../examples/`:
- `quickstart_demo.py` - Minimal example
- `complete_workflow_demo.py` - Full workflow
- `test_artifacts.py` - Artifacts usage
- `remote_storage_demo.py` - Remote sync

See [DEMO_EXAMPLES_GUIDE.md](DEMO_EXAMPLES_GUIDE.md) for details.

### Future Plans

For planned features and development roadmap:
- **GitHub Issues**: Feature requests and enhancements
- **GitHub Projects**: Development timeline and milestones
- **GitHub Discussions**: Community proposals and ideas

---

## 🔄 Changelog

For version history, see:
- **Main Changelog**: `../CHANGELOG.md` - User-facing changes
- **Development Archive**: [CHANGELOG_ARCHIVE.md](CHANGELOG_ARCHIVE.md) - Technical details

---

## 🆘 Need Help?

- 📖 Search documentation
- ❓ Check [user-guide/docs/reference/faq.md](user-guide/docs/reference/faq.md)
- 🐛 [Report issues](https://github.com/yourusername/runicorn/issues)
- 💬 [Ask questions](https://github.com/yourusername/runicorn/discussions)

---

## 📊 Documentation Status

| Category | Status | Files | Coverage |
|----------|--------|-------|----------|
| User Guide | ✅ Ready | 7+ core | 60% |
| API Docs | ✅ Complete | 10 | 100% |
| Architecture | ✅ Complete | 3 | 100% |
| Security | ✅ Complete | 1 | 100% |
| Examples | ✅ Complete | Guide | 100% |

---

**Last Updated**: 2025-10-14  
**Maintained By**: Runicorn Documentation Team

