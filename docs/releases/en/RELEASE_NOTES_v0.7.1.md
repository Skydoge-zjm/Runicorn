# Release Notes v0.7.1

**Release date**: 2026-05-10

---

## Summary

Runicorn v0.7.1 is a stabilization release on top of the v0.7.0 line. It focuses on tightening reliability, security boundaries, release metadata, and desktop build reproducibility rather than adding a new product surface.

---

## Highlights

### Reliability and API alignment

- Metrics write identity handling tightened to avoid overwrite risk in the legacy schema path
- Remote API surface cleaned up around the current unified Remote Viewer model
- Remote API and architecture documentation realigned to the actual shipped routes and session states

### Security and compatibility

- Legacy XOR credential migration boundary tightened
- Saved-credential compatibility path clarified and hardened

### Test and CI hardening

- Frontend loading/baseline/smoke coverage expanded
- CI validation improved for current frontend and desktop build surfaces

### Desktop build hardening

- Layered desktop build configuration added
- Sidecar packaging workflow made more reproducible
- Bilingual desktop build documentation added

---

## Upgrade notes

### If you are coming from v0.7.0

The main differences are operational rather than workflow-level:

- current docs now track the real remote API surface more closely
- desktop build and sidecar packaging are more deterministic
- test and CI coverage are stronger around current reliability risks
- credential migration and legacy compatibility boundaries are tighter
