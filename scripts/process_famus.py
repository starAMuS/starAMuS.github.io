#!/usr/bin/env python3
"""
Process FAMuS dataset files and create JSON files for web display.

This script:
- Parses JSONL files from train/dev/test splits
- Extracts instance_id, frame, report_dict, source_dict
- Enriches with frame definitions from ontology
- Creates paginated JSON files (1000 records per file)
- Generates frame index for search
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


def convert_role_annotations(role_dict):
    """Convert role_annotations format to list of annotations."""
    annotations = []
    for role, spans_list in role_dict.items():
        if role == 'role-spans-indices-in-all-spans':
            continue
        for span_info in spans_list:
            # span_info is [text, start_char, end_char, start_token, end_token, label]
            if len(span_info) >= 6:
                annotations.append({
                    'text': span_info[0],
                    'span': [span_info[1], span_info[2]],
                    'token_span': [span_info[3], span_info[4]],
                    'role': role,
                    'label': span_info[5] if span_info[5] else role
                })
    return annotations


def extract_trigger_info(text_dict, frame_name):
    """Extract trigger information from text dictionary."""
    trigger_span = text_dict.get('frame-trigger-span')
    if not trigger_span:
        return None
        
    # Format: [word, start_char, end_char, start_token, end_token, extra]
    if len(trigger_span) >= 5:
        return {
            'text': trigger_span[0],
            'start_char': trigger_span[1],
            'end_char': trigger_span[2],
            'start_token': trigger_span[3],
            'end_token': trigger_span[4],
            'frame': frame_name
        }
    
    return None


def enrich_annotations_with_roles(annotations, frame_roles):
    """Add role definitions to annotations."""
    enriched = []
    for ann in annotations:
        enriched_ann = ann.copy()
        role = ann.get('role')
        if role and frame_roles and role in frame_roles:
            enriched_ann['role_definition'] = frame_roles[role]
        enriched.append(enriched_ann)
    return enriched


def process_famus_instance(instance, ontology=None):
    """Process a single FAMuS instance with optional ontology enrichment."""
    frame_name = instance.get('frame')
    
    processed = {
        'instance_id': instance.get('instance_id'),
        'frame': frame_name,
        'frame_gloss': instance.get('frame_gloss', ''),
        'report': {
            'text': instance.get('report_dict', {}).get('doctext', ''),
            'annotations': convert_role_annotations(instance.get('report_dict', {}).get('role_annotations', {})),
            'trigger': extract_trigger_info(instance.get('report_dict', {}), frame_name)
        },
        'source': {
            'text': instance.get('source_dict', {}).get('doctext', ''),
            'annotations': convert_role_annotations(instance.get('source_dict', {}).get('role_annotations', {})),
            'trigger': extract_trigger_info(instance.get('source_dict', {}), frame_name)
        },
        'split': instance.get('split', 'unknown')
    }
    
    # Enrich with ontology data if available
    if ontology and frame_name in ontology:
        frame_data = ontology[frame_name]
        processed['frame_definition'] = frame_data.get('definition', '')
        processed['frame_ancestors'] = frame_data.get('ancestors', [])
        processed['frame_descendants'] = frame_data.get('descendants', [])
        
        # Enrich annotations with role definitions
        all_roles = frame_data.get('all_roles', {})
        processed['report']['annotations'] = enrich_annotations_with_roles(
            processed['report']['annotations'], all_roles
        )
        processed['source']['annotations'] = enrich_annotations_with_roles(
            processed['source']['annotations'], all_roles
        )
    
    return processed


def create_frame_index(instances):
    """Create an index of frames for search."""
    frame_index = defaultdict(list)
    
    for idx, instance in enumerate(instances):
        frame = instance['frame']
        frame_index[frame].append({
            'instance_id': instance['instance_id'],
            'idx': idx
        })
    
    return dict(frame_index)


def chunk_data(data, chunk_size=1000):
    """Split data into chunks for pagination."""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]


def main():
    parser = argparse.ArgumentParser(description='Process FAMuS dataset')
    parser.add_argument('--input-dir', type=str, required=True,
                        help='Directory containing FAMuS JSONL files')
    parser.add_argument('--output-dir', type=str, default='assets/data/famus',
                        help='Output directory for processed JSON files')
    parser.add_argument('--ontology-dir', type=str, default='assets/data/ontology',
                        help='Directory containing processed ontology data')
    parser.add_argument('--chunk-size', type=int, default=1000,
                        help='Number of records per JSON file')
    args = parser.parse_args()
    
    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)
    ontology_path = Path(args.ontology_dir)
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load ontology if available
    ontology = load_ontology(ontology_path)
    
    # Process all splits
    all_instances = []
    splits = ['train', 'dev', 'test']
    
    for split in splits:
        split_file = input_path / f'{split}.jsonl'
        if not split_file.exists():
            print(f"Warning: {split_file} not found, skipping...")
            continue
        
        print(f"Processing {split} split...")
        with open(split_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    instance = json.loads(line)
                    instance['split'] = split
                    processed = process_famus_instance(instance, ontology)
                    all_instances.append(processed)
    
    print(f"Processed {len(all_instances)} instances total")
    
    # Create metadata
    metadata = {
        'total_instances': len(all_instances),
        'chunk_size': args.chunk_size,
        'num_chunks': (len(all_instances) + args.chunk_size - 1) // args.chunk_size,
        'frames': list(set(inst['frame'] for inst in all_instances)),
        'splits': {split: sum(1 for inst in all_instances if inst['split'] == split) 
                   for split in splits}
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
    
    # Create frame index
    frame_index = create_frame_index(all_instances)
    with open(output_path / 'frame_index.json', 'w', encoding='utf-8') as f:
        json.dump(frame_index, f, indent=2)
    
    # Create search index data
    search_data = []
    for idx, instance in enumerate(all_instances):
        search_entry = {
            'id': idx,
            'instance_id': instance['instance_id'],
            'frame_name': instance['frame'],
            'frame_gloss': instance['frame_gloss'],
            'frame_definition': instance.get('frame_definition', ''),
            'frame_ancestors': instance.get('frame_ancestors', []),
            'report_text': instance['report']['text'][:500],  # First 500 chars
            'source_text': instance['source']['text'][:500],
            'roles': list(set(ann['role'] for ann in instance['report']['annotations'] + 
                            instance['source']['annotations'] if 'role' in ann))
        }
        search_data.append(search_entry)
    
    with open(output_path / 'search_index.json', 'w', encoding='utf-8') as f:
        json.dump(search_data, f, separators=(',', ':'))
    
    print(f"\nProcessing complete!")
    print(f"Output saved to: {output_path}")
    print(f"Total chunks created: {metadata['num_chunks']}")
    print(f"Unique frames: {len(metadata['frames'])}")


if __name__ == '__main__':
    main()