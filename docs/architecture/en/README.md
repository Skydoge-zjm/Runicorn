[English](README.md) | [简体中文](../zh/README.md)

---

# Runicorn Architecture Documentation

**Version**: v0.6.0  
**Last Updated**: 2026-01-15  
**Audience**: Developers, Contributors, Architects

---

## Overview

This directory contains comprehensive architecture documentation for the Runicorn system. These documents explain the **design** and **why** behind the implementation, complementing the user guides (how to use) and API documentation (what endpoints exist).

---

## Architecture Documents

### System Design

- **[SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)** - High-level system architecture
  - Overall architecture diagram
  - Technology stack and rationale
  - Core principles and design goals
  - System boundaries

- **[COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md)** - Component breakdown
  - SDK layer design
  - Viewer/API layer design
  - Storage layer design
  - Component interactions

### Data & Storage

- **[DATA_FLOW.md](DATA_FLOW.md)** - Data processing pipeline
  - Experiment lifecycle
  - Metrics logging flow
  - Artifact storage flow
  - Sequence diagrams

- **[STORAGE_DESIGN.md](STORAGE_DESIGN.md)** - Storage architecture
  - Hybrid SQLite + Files approach
  - Database schema design
  - Deduplication algorithm
  - Performance characteristics

### Application Layers

- **[API_DESIGN.md](API_DESIGN.md)** - API layer architecture
  - V1 vs V2 design rationale
  - Route organization
  - Service layer pattern
  - Error handling strategy

- **[FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md)** - Frontend design
  - React application structure
  - State management
  - Component hierarchy
  - Performance optimizations

### Remote & Networking

- **[REMOTE_VIEWER_ARCHITECTURE.md](REMOTE_VIEWER_ARCHITECTURE.md)** - ⭐ Remote Viewer architecture (v0.5.0)
  - SSH tunnel design
  - Remote process management
  - Health check mechanism
  - Security model

- **[SSH_BACKEND_ARCHITECTURE.md](SSH_BACKEND_ARCHITECTURE.md)** - ⭐ SSH backend multi-fallback design (v0.6.0)
  - OpenSSH + AsyncSSH + Paramiko fallback chain
  - Platform-specific strategy
  - Connection management

### Deployment & Decisions

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment options
  - Local deployment
  - Server deployment
  - Desktop app (Tauri)
  - Scaling strategies

- **[DESIGN_DECISIONS.md](DESIGN_DECISIONS.md)** - Technical decisions
  - Why SQLite over PostgreSQL
  - Why Python + FastAPI
  - Why React + Ant Design
  - Trade-offs considered

---

## How to Use This Documentation

### For New Contributors

**Recommended reading order**:
1. Start with [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) - Understand the big picture
2. Read [COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md) - Understand how pieces fit together
3. Dive into specific areas based on your contribution focus

### For System Architects

**Focus on**:
- [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) - Overall design
- [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) - Rationale behind choices
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production considerations

### For Backend Developers

**Focus on**:
- [COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md) - Backend components
- [STORAGE_DESIGN.md](STORAGE_DESIGN.md) - Storage implementation
- [API_DESIGN.md](API_DESIGN.md) - API layer design
- [DATA_FLOW.md](DATA_FLOW.md) - Data processing

### For Frontend Developers

**Focus on**:
- [FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md) - React app design
- [DATA_FLOW.md](DATA_FLOW.md) - How data flows to UI
- [API_DESIGN.md](API_DESIGN.md) - API consumption patterns

---

## Related Documentation

- **User Guides**: [../guides/](../guides/) - How to use Runicorn
- **API Docs**: [../api/](../api/) - REST API reference
- **Reference**: [../reference/](../reference/) - Technical reference materials

---

## Contributing to Architecture Docs

When contributing to architecture documentation:

1. **Focus on design, not usage** - Explain "why" and "how it works", not "how to use"
2. **Include diagrams** - Use Mermaid or ASCII art for visual explanations
3. **Explain trade-offs** - Document alternatives considered and why rejected
4. **Keep updated** - Update when architecture changes significantly

---

**Back to main docs**: [../../README.md](../../README.md)


