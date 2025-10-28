"""
Allow running runicorn as a module: python -m runicorn
"""
from .cli import main

if __name__ == "__main__":
    exit(main())
