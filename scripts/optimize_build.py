#!/usr/bin/env python3
"""
Optimize the Jekyll build for production deployment.

This script:
- Minifies JSON data files
- Creates compressed versions of large files
- Generates a manifest for the service worker
- Optimizes images if present
"""

import json
import os
import gzip
import shutil
from pathlib import Path
import argparse


def minify_json(file_path):
    """Minify a JSON file by removing whitespace."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Write minified version
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, separators=(',', ':'))
    
    return os.path.getsize(file_path)


def create_gzip_version(file_path):
    """Create a gzipped version of a file."""
    gz_path = file_path + '.gz'
    
    with open(file_path, 'rb') as f_in:
        with gzip.open(gz_path, 'wb', compresslevel=9) as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    return os.path.getsize(gz_path)


def generate_cache_manifest(site_dir):
    """Generate a list of all cacheable assets."""
    cacheable_extensions = {'.html', '.css', '.js', '.json', '.png', '.jpg', '.jpeg', '.gif', '.svg'}
    manifest = []
    
    site_path = Path(site_dir)
    
    for file_path in site_path.rglob('*'):
        if file_path.is_file() and file_path.suffix in cacheable_extensions:
            # Get relative path from site root
            relative_path = str(file_path.relative_to(site_path))
            
            # Skip large data files and service worker itself
            if '_data/' in relative_path or relative_path == 'sw.js':
                continue
            
            manifest.append('/' + relative_path)
    
    # Write manifest
    manifest_path = site_path / 'cache-manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump({
            'version': 1,
            'urls': sorted(manifest)
        }, f, indent=2)
    
    return len(manifest)


def optimize_data_files(data_dir):
    """Optimize all JSON data files."""
    data_path = Path(data_dir)
    total_saved = 0
    files_processed = 0
    
    for json_file in data_path.rglob('*.json'):
        # Skip already gzipped files
        if json_file.suffix == '.gz':
            continue
        
        # Get original size
        original_size = os.path.getsize(json_file)
        
        # Minify JSON
        minified_size = minify_json(json_file)
        
        # Create gzip version for large files (> 100KB)
        if minified_size > 100 * 1024:
            create_gzip_version(json_file)
        
        total_saved += original_size - minified_size
        files_processed += 1
    
    return files_processed, total_saved


def main():
    parser = argparse.ArgumentParser(description='Optimize Jekyll build')
    parser.add_argument('--site-dir', type=str, default='_site',
                        help='Jekyll output directory')
    parser.add_argument('--data-dir', type=str, default='_data',
                        help='Data directory to optimize')
    args = parser.parse_args()
    
    print("🚀 Starting build optimization...")
    
    # Optimize data files
    if os.path.exists(args.data_dir):
        print("\n📊 Optimizing data files...")
        files_processed, bytes_saved = optimize_data_files(args.data_dir)
        print(f"✅ Processed {files_processed} files, saved {bytes_saved / 1024:.1f} KB")
    
    # Generate cache manifest
    if os.path.exists(args.site_dir):
        print("\n📋 Generating cache manifest...")
        urls_cached = generate_cache_manifest(args.site_dir)
        print(f"✅ Generated manifest with {urls_cached} URLs")
    
    print("\n✨ Build optimization complete!")


if __name__ == '__main__':
    main()