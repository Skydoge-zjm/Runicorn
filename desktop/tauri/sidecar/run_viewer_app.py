import argparse
import os
import sys
from typing import Optional

import uvicorn

try:
    # Ensure the module is importable when frozen
    import runicorn.viewer as viewer  # type: ignore
except Exception as e:  # pragma: no cover
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
        print("[runicorn-viewer] create_app not found on runicorn.viewer")
        return 2
    try:
        uvicorn.run(app_factory, host=args.host, port=args.port, factory=True, log_level="info")
    except Exception as e:
        print("[runicorn-viewer] uvicorn run failed:", e)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
