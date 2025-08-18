#!/usr/bin/env python3
"""
Process FrameNet ontology data to create searchable indices.

This script:
- Parses ontology.json containing frame definitions
- Extracts frame definitions, core roles, and role definitions
- Creates searchable frame ontology index
- Generates frame hierarchy data for browsing
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict
import argparse


def process_frame(frame_name, frame_data):
    """Process a single frame from the ontology."""
    processed = {
        'name': frame_name,
        'definition': frame_data.get('definition', ''),
        'ancestors': frame_data.get('ancestors', []),
        'descendants': frame_data.get('descendants', []),
        'core_roles': {},
        'all_roles': {}
    }
    
    # Extract core roles
    core_roles = frame_data.get('core roles', {})
    for role_name, role_info in core_roles.items():
        if isinstance(role_info, dict) and 'definition' in role_info:
            processed['core_roles'][role_name] = role_info['definition']
    
    # Extract all roles (including non-core)
    all_roles = frame_data.get('roles', {})
    for role_name, role_info in all_roles.items():
        if isinstance(role_info, dict) and 'definition' in role_info:
            processed['all_roles'][role_name] = role_info['definition']
    
    return processed


def create_hierarchy_index(frames):
    """Create an index for frame hierarchy navigation."""
    hierarchy = {
        'roots': [],  # Frames with no ancestors
        'children': defaultdict(set),  # Parent -> {children} (using set to avoid duplicates)
        'parents': defaultdict(set)     # Child -> {parents} (using set to avoid duplicates)
    }
    
    for frame_name, frame_data in frames.items():
        ancestors = frame_data.get('ancestors', [])
        descendants = frame_data.get('descendants', [])
        
        # Find root frames
        if not ancestors:
            hierarchy['roots'].append(frame_name)
        
        # Build parent-child relationships
        # Only use ancestor relationships to avoid duplication
        # (since each frame lists its ancestors, we don't need to also process descendants)
        for ancestor in ancestors:
            hierarchy['children'][ancestor].add(frame_name)
            hierarchy['parents'][frame_name].add(ancestor)
    
    # Convert sets to sorted lists and defaultdicts to regular dicts for JSON serialization
    hierarchy['children'] = {k: sorted(list(v)) for k, v in hierarchy['children'].items()}
    hierarchy['parents'] = {k: sorted(list(v)) for k, v in hierarchy['parents'].items()}
    
    # Remove duplicates from roots
    hierarchy['roots'] = sorted(list(set(hierarchy['roots'])))
    
    return hierarchy


def create_search_index(frames):
    """Create search index for frame semantic search."""
    search_entries = []
    
    for frame_name, frame_data in frames.items():
        # Create search entry for each frame
        entry = {
            'id': frame_name,
            'frame_name': frame_name,
            'frame_definition': frame_data['definition'],
            'core_roles': list(frame_data['core_roles'].keys()),
            'all_roles': list(frame_data['all_roles'].keys()),
            'role_definitions': ' '.join(frame_data['all_roles'].values()),
            'ancestors': frame_data['ancestors'],
            'descendants': frame_data['descendants']
        }
        search_entries.append(entry)
    
    return search_entries


def main():
    parser = argparse.ArgumentParser(description='Process FrameNet ontology')
    parser.add_argument('--input-file', type=str, required=True,
                        help='Path to ontology.json file')
    parser.add_argument('--output-dir', type=str, default='assets/data/ontology',
                        help='Output directory for processed data')
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    output_path = Path(args.output_dir)
    
    if not input_path.exists():
        print(f"Error: Input file {input_path} not found")
        sys.exit(1)
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Loading ontology from {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        ontology = json.load(f)
    
    print(f"Processing {len(ontology)} frames...")
    
    # Process all frames
    processed_frames = {}
    for frame_name, frame_data in ontology.items():
        processed_frames[frame_name] = process_frame(frame_name, frame_data)
    
    # Create hierarchy index
    hierarchy = create_hierarchy_index(ontology)
    
    # Create search index
    search_index = create_search_index(processed_frames)
    
    # Save processed frames
    frames_file = output_path / 'frames.json'
    with open(frames_file, 'w', encoding='utf-8') as f:
        json.dump(processed_frames, f, indent=2)
    print(f"Saved processed frames to {frames_file}")
    
    # Save hierarchy index
    hierarchy_file = output_path / 'hierarchy.json'
    with open(hierarchy_file, 'w', encoding='utf-8') as f:
        json.dump(hierarchy, f, indent=2)
    print(f"Saved hierarchy index to {hierarchy_file}")
    
    # Save search index
    search_file = output_path / 'search_index.json'
    with open(search_file, 'w', encoding='utf-8') as f:
        json.dump(search_index, f, separators=(',', ':'))
    print(f"Saved search index to {search_file}")
    
    # Create metadata
    metadata = {
        'total_frames': len(processed_frames),
        'total_core_roles': sum(len(f['core_roles']) for f in processed_frames.values()),
        'total_roles': sum(len(f['all_roles']) for f in processed_frames.values()),
        'root_frames': len(hierarchy['roots']),
        'frame_names': sorted(processed_frames.keys())
    }
    
    metadata_file = output_path / 'metadata.json'
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nOntology processing complete!")
    print(f"Total frames: {metadata['total_frames']}")
    print(f"Total core roles: {metadata['total_core_roles']}")
    print(f"Total roles: {metadata['total_roles']}")
    print(f"Root frames: {metadata['root_frames']}")


if __name__ == '__main__':
    main()