"""
Manifest Generation CLI

Command-line interface for generating sync manifests on the server.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .generator import ManifestGenerator, ManifestType

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def generate_manifest_cli() -> int:
    """
    CLI entry point for manifest generation.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description='Generate sync manifest for Runicorn experiments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate full manifest in current directory
  runicorn generate-manifest
  
  # Generate active manifest for recently updated experiments
  runicorn generate-manifest --active
  
  # Generate manifest for specific root directory
  runicorn generate-manifest --root /data/experiments
  
  # Generate with custom output path
  runicorn generate-manifest --output /tmp/manifest.json
  
  # Verbose mode with debug logging
  runicorn generate-manifest --verbose
        """
    )
    
    parser.add_argument(
        '--root',
        type=str,
        default='.',
        help='Root directory of experiments (default: current directory)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output path for manifest file (default: <root>/.runicorn/<type>_manifest.json)'
    )
    
    parser.add_argument(
        '--active',
        action='store_true',
        help='Generate active manifest (only recent experiments, default: full manifest)'
    )
    
    parser.add_argument(
        '--full',
        action='store_true',
        help='Generate full manifest (all experiments, this is the default)'
    )
    
    parser.add_argument(
        '--active-window',
        type=int,
        default=3600,
        help='Time window in seconds for active experiments (default: 3600 = 1 hour)'
    )
    
    parser.add_argument(
        '--no-incremental',
        action='store_true',
        help='Disable incremental generation (always do full scan)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    try:
        # Determine manifest type
        if args.active:
            manifest_type = ManifestType.ACTIVE
        else:
            manifest_type = ManifestType.FULL
        
        # Resolve paths
        root_path = Path(args.root).resolve()
        if not root_path.exists():
            logger.error(f"Root directory does not exist: {root_path}")
            return 1
        
        if not root_path.is_dir():
            logger.error(f"Root path is not a directory: {root_path}")
            return 1
        
        output_path = Path(args.output).resolve() if args.output else None
        
        # Create generator
        generator = ManifestGenerator(
            remote_root=root_path,
            active_window_seconds=args.active_window,
            incremental=not args.no_incremental
        )
        
        # Generate manifest
        logger.info(f"Generating {manifest_type.value} manifest...")
        manifest, output_file = generator.generate(
            manifest_type=manifest_type,
            output_path=output_path
        )
        
        # Print summary
        print("\n" + "=" * 60)
        print("Manifest Generation Complete")
        print("=" * 60)
        print(f"Type:          {manifest_type.value}")
        print(f"Output:        {output_file}")
        print(f"Compressed:    {output_file}.gz")
        print(f"Revision:      {manifest.revision}")
        print(f"Snapshot ID:   {manifest.snapshot_id}")
        print(f"Experiments:   {manifest.total_experiments}")
        print(f"Files:         {manifest.total_files}")
        print(f"Total Size:    {manifest.total_bytes / (1024*1024):.2f} MB")
        print("=" * 60)
        
        return 0
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    
    except Exception as e:
        logger.error(f"Manifest generation failed: {e}", exc_info=args.verbose)
        return 1


if __name__ == '__main__':
    sys.exit(generate_manifest_cli())
