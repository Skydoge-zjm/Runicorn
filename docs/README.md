[English](README.md) | [简体中文](README_zh.md)

# Runicorn Documentation Map

This directory contains the maintained project documentation for Runicorn.

## Authoritative Entry Points

Use these as the primary documentation entry points:

- `README.md`: package overview and installation
- `docs/user-guide/`: published MkDocs site for end users
- `docs/api/`: long-form API reference
- `docs/architecture/`: system and implementation design
- `docs/guides/`: task-oriented guides
- `docs/reference/`: reference material such as configuration and FAQ
- `docs/releases/`: release notes and version history

## Published Site

The published documentation site lives in:

```text
docs/user-guide/
```

Important pages inside the site:

- `docs/user-guide/docs/cli/overview.md`
- `docs/user-guide/docs/reference/cli-reference.md`
- `docs/user-guide/docs/reference/api-surface.md`
- `docs/user-guide/docs/reference/documentation-system.md`

Two of those pages are generated from source code by:

```text
scripts/sync_docs_reference.py
```

This reduces drift between the docs and the actual CLI/API surface.

## Non-Authoritative Work Areas

The following locations are not part of the maintained product documentation:

- `docs/future/`
- `.kiro/`
- `.backup/`

They may contain planning notes, scratch work, or historical development artifacts, but they should not be treated as current documentation.

## Maintenance Workflow

When the code changes in a user-facing way:

1. Update the relevant guide pages.
2. Regenerate source-driven reference pages:

```bash
conda run -n runicorn_dev python scripts/sync_docs_reference.py
```

3. Build the site strictly:

```bash
conda run -n runicorn_dev mkdocs build --strict -f docs/user-guide/mkdocs.yml
```

## Deployment

GitHub Pages deployment is handled by:

```text
.github/workflows/deploy-docs.yml
```

That workflow now regenerates the source-driven reference pages before building the MkDocs site.
