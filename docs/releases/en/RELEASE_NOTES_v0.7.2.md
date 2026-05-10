# Release Notes v0.7.2

**Release date**: 2026-05-11

---

## Summary

Runicorn v0.7.2 is a patch release published immediately after v0.7.1. It does not introduce a new product surface. Instead, it fixes post-release issues found in packaging, CI, dependency metadata, and cross-platform test assumptions.

---

## Highlights

### Packaging and release workflow fixes

- publish script updated to use the centralized version source instead of the old `pyproject.toml` version field
- release flow validated again against the `runicorn_dev` environment and current build backend

### CI and dependency fixes

- missing `Path` import fixed in CLI export code paths
- missing `requests` runtime dependency declared for the Python client
- missing `pandas` dev dependency declared for client utility tests

### Cross-platform test fixes

- OpenSSH askpass test updated to accept both Windows and non-Windows wrapper variants
- current CI surface brought back to green after the v0.7.1 release

---

## Relationship to v0.7.1

If you are looking for the main user-facing changes in this release line, read [RELEASE_NOTES_v0.7.1.md](RELEASE_NOTES_v0.7.1.md) first. v0.7.2 is the follow-up patch release that stabilizes the shipped 0.7.1 package and release pipeline.
