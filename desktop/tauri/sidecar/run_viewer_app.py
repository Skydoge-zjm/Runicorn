import argparse
import os
import sys
from typing import Optional

# Simple file logger (works even when running as a frozen exe without console)
def _log_path() -> str:
    base = os.getenv("APPDATA") or os.getcwd()
    d = os.path.join(base, "Runicorn")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        d = os.getcwd()
    return os.path.join(d, "sidecar.log")

def log(*parts: object) -> None:
    try:
        msg = " ".join(str(p) for p in parts)
        with open(_log_path(), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

try:
    import uvicorn
except Exception as e:  # pragma: no cover
    log("[runicorn-viewer] failed importing uvicorn:", repr(e))
    print("[runicorn-viewer] failed importing uvicorn:", e)
    raise
# Eagerly import common C-extensions so PyInstaller picks them up in analysis
try:
    import ssl as _ssl_mod  # noqa: F401
    import hashlib as _hashlib_mod  # noqa: F401
    import bz2 as _bz2_mod  # noqa: F401
    import lzma as _lzma_mod  # noqa: F401
except Exception as _e:  # pragma: no cover
    print("[runicorn-viewer] pre-import stdlib modules failed:", _e)

# Ensure form parser dependency is importable inside the frozen exe
try:
    import multipart as _multipart_pkg  # provided by python-multipart
    log("[runicorn-viewer] multipart available, version:", getattr(_multipart_pkg, "__version__", "?"))
except Exception as _e:
    log("[runicorn-viewer] multipart import failed:", repr(_e))

try:
    # Ensure the module is importable when frozen
    import runicorn.viewer as viewer  # type: ignore
except Exception as e:  # pragma: no cover
    log("[runicorn-viewer] failed importing runicorn.viewer:", repr(e))
    print("[runicorn-viewer] failed importing runicorn.viewer:", e)
    # Best-effort: add repo src to sys.path when running from source layout
    here = os.path.abspath(os.path.dirname(__file__))
    repo_src = os.path.abspath(os.path.join(here, "..", "..", "..", "src"))
    if os.path.isdir(repo_src) and repo_src not in sys.path:
        sys.path.insert(0, repo_src)
    import runicorn.viewer as viewer  # type: ignore


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Runicorn viewer sidecar (uvicorn)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args(argv)

    # create_app is a factory
    app_factory = getattr(viewer, "create_app")
    if not callable(app_factory):
        log("[runicorn-viewer] create_app not found on runicorn.viewer")
        print("[runicorn-viewer] create_app not found on runicorn.viewer")
        return 2
    try:
        log("[runicorn-viewer] starting uvicorn:", args.host, args.port)
        # Disable uvicorn's default logging config to avoid "Unable to configure formatter 'default'" under PyInstaller
        uvicorn.run(app_factory, host=args.host, port=args.port, factory=True, log_level="info", log_config=None)
    except Exception as e:
        log("[runicorn-viewer] uvicorn run failed:", repr(e))
        print("[runicorn-viewer] uvicorn run failed:", e)
        print("Environment diagnostics:")
        print("  sys.path:", sys.path)
        print("  sys.executable:", sys.executable)
        print("  os.getcwd():", os.getcwd())
        try:
            log("  sys.path:", sys.path)
            log("  sys.executable:", sys.executable)
            log("  os.getcwd():", os.getcwd())
        except Exception:
            pass
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
