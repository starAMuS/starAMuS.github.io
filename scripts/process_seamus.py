#!/usr/bin/env python3
"""
Process SEAMuS dataset files and create JSON files for web display.

This script:
- Parses train/dev/test JSON files
- Extracts summaries, templates, and annotations
- Links to FAMuS instances via instance_id
- Enriches with frame definitions from ontology
- Creates summary search index
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict
import argparse


def load_ontology(ontology_path):
    """Load processed ontology data."""
    frames_file = ontology_path / 'frames.json'
    if not frames_file.exists():
        print(f"Warning: Ontology file {frames_file} not found. Running without ontology enrichment.")
        return None
    
    with open(frames_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_famus_frames(famus_path):
    """Load frame information from FAMuS data."""
    frame_index_file = famus_path / 'frame_index.json'
    if not frame_index_file.exists():
        print(f"Warning: FAMuS frame index not found. Cannot link frames to SEAMuS instances.")
        return None
    
    with open(frame_index_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_frame_from_instance_id(instance_id):
    """Extract frame name from FAMuS instance ID.
    Example: 'EN-1282-352-frame-Abandonment' -> 'Abandonment'
    """
    parts = instance_id.split('-frame-')
    if len(parts) == 2:
        return parts[1]
    return None


def process_seamus_instance(instance, ontology=None, famus_frames=None):
    """Process a single SEAMuS instance with optional ontology enrichment."""
    # Get instance_id - handle both singular and plural forms
    instance_id = instance.get('instance_id', '')
    instance_ids = [instance_id] if instance_id else instance.get('instance_ids', [])
    
    processed = {
        'id': instance_id,  # Use instance_id as the id
        'instance_ids': instance_ids,
        'report_summary': instance.get('report_summary', ''),
        'report_summary_template': instance.get('report_summary_template', {}),
        'combined_summary': instance.get('combined_summary', ''),
        'combined_summary_template': instance.get('combined_summary_template', {}),
        'template_roles': instance.get('template_roles', {}),
        'annotations': instance.get('annotations', []),
        'split': instance.get('split', 'unknown'),
        'frames': []  # Frames associated with this SEAMuS instance
    }
    
    # Extract frames from instance IDs
    frame_set = set()
    for instance_id in processed['instance_ids']:
        frame = extract_frame_from_instance_id(instance_id)
        if frame:
            frame_set.add(frame)
    
    processed['frames'] = list(frame_set)
    
    # Enrich with ontology data if available
    if ontology:
        processed['frame_definitions'] = {}
        processed['role_definitions'] = {}
        
        for frame in processed['frames']:
            if frame in ontology:
                frame_data = ontology[frame]
                processed['frame_definitions'][frame] = frame_data.get('definition', '')
                
                # Collect role definitions for template roles
                all_roles = frame_data.get('all_roles', {})
                for role in processed['template_roles']:
                    if role in all_roles:
                        processed['role_definitions'][role] = all_roles[role]
    
    return processed


def create_instance_mapping(seamus_data):
    """Create mapping from FAMuS instance_id to SEAMuS entries."""
    instance_to_seamus = defaultdict(list)
    
    for idx, entry in enumerate(seamus_data):
        for instance_id in entry.get('instance_ids', []):
            instance_to_seamus[instance_id].append({
                'seamus_id': entry['id'],
                'idx': idx,
                'report_summary': entry.get('report_summary', ''),
                'combined_summary': entry.get('combined_summary', '')
            })
    
    return dict(instance_to_seamus)


def chunk_data(data, chunk_size=1000):
    """Split data into chunks for pagination."""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]


def main():
    parser = argparse.ArgumentParser(description='Process SEAMuS dataset')
    parser.add_argument('--input-dir', type=str, required=True,
                        help='Directory containing SEAMuS JSON files')
    parser.add_argument('--output-dir', type=str, default='assets/data/seamus',
                        help='Output directory for processed JSON files')
    parser.add_argument('--ontology-dir', type=str, default='assets/data/ontology',
                        help='Directory containing processed ontology data')
    parser.add_argument('--famus-dir', type=str, default='assets/data/famus',
                        help='Directory containing processed FAMuS data')
    parser.add_argument('--chunk-size', type=int, default=1000,
                        help='Number of records per JSON file')
    args = parser.parse_args()
    
    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)
    ontology_path = Path(args.ontology_dir)
    famus_path = Path(args.famus_dir)
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load ontology and FAMuS data if available
    ontology = load_ontology(ontology_path)
    famus_frames = load_famus_frames(famus_path)
    
    # Process all splits
    all_instances = []
    splits = ['train', 'dev', 'test']
    
    for split in splits:
        split_file = input_path / f'{split}.json'
        if not split_file.exists():
            print(f"Warning: {split_file} not found, skipping...")
            continue
        
        print(f"Processing {split} split...")
        with open(split_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # Handle both list and dict formats
            if isinstance(data, list):
                instances = data
            elif isinstance(data, dict) and 'data' in data:
                instances = data['data']
            else:
                print(f"Warning: Unexpected format in {split_file}")
                continue
            
            for instance in instances:
                instance['split'] = split
                processed = process_seamus_instance(instance, ontology, famus_frames)
                all_instances.append(processed)
    
    print(f"Processed {len(all_instances)} SEAMuS instances total")
    
    # Create metadata
    metadata = {
        'total_instances': len(all_instances),
        'chunk_size': args.chunk_size,
        'num_chunks': (len(all_instances) + args.chunk_size - 1) // args.chunk_size,
        'splits': {split: sum(1 for inst in all_instances if inst['split'] == split) 
                   for split in splits},
        'total_famus_links': sum(len(inst['instance_ids']) for inst in all_instances)
    }
    
    # Save metadata
    with open(output_path / 'metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    # Save chunked data
    for idx, chunk in enumerate(chunk_data(all_instances, args.chunk_size)):
        chunk_file = output_path / f'chunk_{idx:04d}.json'
        with open(chunk_file, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, separators=(',', ':'))
        print(f"Saved chunk {idx} with {len(chunk)} instances")
    
    # Create FAMuS instance mapping
    instance_mapping = create_instance_mapping(all_instances)
    with open(output_path / 'instance_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(instance_mapping, f, indent=2)
    
    # Create search index for summaries
    search_data = []
    for idx, instance in enumerate(all_instances):
        search_entry = {
            'id': idx,
            'seamus_id': instance['id'],
            'report_summary': instance['report_summary'],
            'combined_summary': instance['combined_summary'],
            'instance_ids': instance['instance_ids'],
            'num_instances': len(instance['instance_ids']),
            'frames': instance['frames'],
            'frame_definitions': list(instance.get('frame_definitions', {}).values()),
            'template_roles': list(instance.get('template_roles', {}).keys())
        }
        search_data.append(search_entry)
    
    with open(output_path / 'search_index.json', 'w', encoding='utf-8') as f:
        json.dump(search_data, f, separators=(',', ':'))
    
    print(f"\nProcessing complete!")
    print(f"Output saved to: {output_path}")
    print(f"Total chunks created: {metadata['num_chunks']}")
    print(f"Total FAMuS links: {metadata['total_famus_links']}")


if __name__ == '__main__':
    main()