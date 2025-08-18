#!/usr/bin/env python3
"""
Process and unify FAMuS 1.0 and 1.1 datasets into a single format.

This script:
- Loads FAMuS 1.0 from JSONL files
- Loads FAMuS 1.1 from JSON files  
- Normalizes both to identical structure
- Compares annotations to detect differences
- Creates unified JSON files with both versions
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


def normalize_annotation(annotation):
    """Normalize annotation to standard format."""
    return {
        'text': annotation.get('text', ''),
        'span': annotation.get('span', [0, 0]),
        'token_span': annotation.get('token_span', [0, 0]),
        'role': annotation.get('role', ''),
        'label': annotation.get('label', annotation.get('role', '')),
        'role_definition': annotation.get('role_definition', '')
    }


def normalize_trigger(trigger):
    """Normalize trigger to standard format."""
    if not trigger:
        return None
    
    return {
        'text': trigger.get('text', ''),
        'start_char': trigger.get('start_char', 0),
        'end_char': trigger.get('end_char', 0),
        'start_token': trigger.get('start_token', 0),
        'end_token': trigger.get('end_token', 0),
        'frame': trigger.get('frame', '')
    }


def annotations_differ(ann1_list, ann2_list):
    """Check if two annotation lists differ."""
    if len(ann1_list) != len(ann2_list):
        return True
    
    # Create sets of (role, text, span) tuples for comparison
    ann1_set = {
        (ann['role'], ann['text'], tuple(ann.get('span', [])))
        for ann in ann1_list
    }
    ann2_set = {
        (ann['role'], ann['text'], tuple(ann.get('span', [])))
        for ann in ann2_list
    }
    
    return ann1_set != ann2_set


def triggers_differ(trigger1, trigger2):
    """Check if two triggers differ."""
    if (trigger1 is None) != (trigger2 is None):
        return True
    
    if trigger1 is None:
        return False
    
    return (
        trigger1.get('text') != trigger2.get('text') or
        trigger1.get('start_char') != trigger2.get('start_char') or
        trigger1.get('end_char') != trigger2.get('end_char')
    )


def versions_differ(v1_0, v1_1):
    """Check if two versions have different annotations."""
    # Check report annotations
    if annotations_differ(v1_0['report']['annotations'], v1_1['report']['annotations']):
        return True
    
    # Check source annotations
    if annotations_differ(v1_0['source']['annotations'], v1_1['source']['annotations']):
        return True
    
    # Check triggers
    if triggers_differ(v1_0['report'].get('trigger'), v1_1['report'].get('trigger')):
        return True
    
    if triggers_differ(v1_0['source'].get('trigger'), v1_1['source'].get('trigger')):
        return True
    
    return False


def process_famus_10_instance(instance, ontology=None):
    """Process a FAMuS 1.0 instance."""
    frame_name = instance.get('frame', '')
    
    # Extract and normalize annotations
    def convert_role_annotations(role_dict):
        annotations = []
        for role, spans_list in role_dict.items():
            if role == 'role-spans-indices-in-all-spans':
                continue
            for span_info in spans_list:
                if len(span_info) >= 6:
                    annotations.append({
                        'text': span_info[0],
                        'span': [span_info[1], span_info[2]],
                        'token_span': [span_info[3], span_info[4]],
                        'role': role,
                        'label': span_info[5] if span_info[5] else role
                    })
        return annotations
    
    # Extract trigger
    def extract_trigger(text_dict, frame_name):
        trigger_span = text_dict.get('frame-trigger-span')
        if not trigger_span or len(trigger_span) < 5:
            return None
        
        return {
            'text': trigger_span[0],
            'start_char': trigger_span[1],
            'end_char': trigger_span[2],
            'start_token': trigger_span[3],
            'end_token': trigger_span[4],
            'frame': frame_name
        }
    
    report_dict = instance.get('report_dict', {})
    source_dict = instance.get('source_dict', {})
    
    # Build normalized structure
    processed = {
        'report': {
            'text': report_dict.get('doctext', ''),
            'annotations': convert_role_annotations(report_dict.get('role_annotations', {})),
            'trigger': extract_trigger(report_dict, frame_name)
        },
        'source': {
            'text': source_dict.get('doctext', ''),
            'annotations': convert_role_annotations(source_dict.get('role_annotations', {})),
            'trigger': extract_trigger(source_dict, frame_name)
        }
    }
    
    # Enrich with ontology if available
    if ontology and frame_name in ontology:
        frame_data = ontology[frame_name]
        all_roles = frame_data.get('all_roles', {})
        
        for ann in processed['report']['annotations']:
            if ann['role'] in all_roles:
                ann['role_definition'] = all_roles[ann['role']]
        
        for ann in processed['source']['annotations']:
            if ann['role'] in all_roles:
                ann['role_definition'] = all_roles[ann['role']]
    
    # Normalize all annotations
    processed['report']['annotations'] = [
        normalize_annotation(ann) for ann in processed['report']['annotations']
    ]
    processed['source']['annotations'] = [
        normalize_annotation(ann) for ann in processed['source']['annotations']
    ]
    processed['report']['trigger'] = normalize_trigger(processed['report']['trigger'])
    processed['source']['trigger'] = normalize_trigger(processed['source']['trigger'])
    
    return processed


def process_famus_11_instance(instance, ontology=None):
    """Process a FAMuS 1.1 instance."""
    trigger_data = instance.get('trigger', {})
    frame_name = trigger_data.get('frame', '')
    
    # Get tokens for text reconstruction
    report_tokens = instance.get('report', [])
    source_tokens = instance.get('source', [])
    
    # Reconstruct text
    report_text = ' '.join(report_tokens)
    source_text = ' '.join(source_tokens)
    
    # Convert template to annotations
    def convert_template(template_dict, tokens):
        annotations = []
        
        # Calculate character positions
        char_positions = []
        current_pos = 0
        for i, token in enumerate(tokens):
            char_positions.append(current_pos)
            current_pos += len(token)
            if i < len(tokens) - 1:
                current_pos += 1
        
        for role, role_data in template_dict.items():
            if 'arguments' in role_data:
                for arg in role_data['arguments']:
                    if 'start_token' in arg and 'end_token' in arg:
                        arg_tokens = arg.get('tokens', [])
                        text = ' '.join(arg_tokens) if arg_tokens else ''
                        
                        start_token = arg['start_token']
                        end_token = arg['end_token']
                        
                        # Calculate character span (inclusive end like FAMuS 1.0)
                        if start_token < len(char_positions) and end_token < len(char_positions):
                            start_char = char_positions[start_token]
                            if end_token < len(tokens) - 1:
                                # Not the last token - end at last char of end_token (before space)
                                end_char = char_positions[end_token + 1] - 2
                            else:
                                # Last token - end at last character
                                end_char = char_positions[end_token] + len(tokens[end_token]) - 1
                        else:
                            start_char = 0
                            end_char = len(text)
                        
                        annotations.append({
                            'text': text,
                            'span': [start_char, end_char],
                            'token_span': [start_token, end_token],
                            'role': role,
                            'label': role
                        })
        
        return annotations
    
    # Extract trigger
    def extract_trigger_11(trigger_dict, tokens):
        if not trigger_dict:
            return None
        
        # Calculate character positions
        char_positions = []
        current_pos = 0
        for i, token in enumerate(tokens):
            char_positions.append(current_pos)
            current_pos += len(token)
            if i < len(tokens) - 1:
                current_pos += 1
        
        start_token = trigger_dict.get('start_token')
        end_token = trigger_dict.get('end_token')
        
        if start_token is not None and end_token is not None and start_token < len(char_positions):
            start_char = char_positions[start_token]
            if end_token < len(tokens) - 1:
                # Not the last token - end at last char of end_token (before space)
                end_char = char_positions[end_token + 1] - 2
            else:
                # Last token - end at last character
                end_char = char_positions[end_token] + len(tokens[end_token]) - 1
        else:
            start_char = None
            end_char = None
        
        return {
            'text': ' '.join(trigger_dict.get('tokens', [])),
            'start_char': start_char,
            'end_char': end_char,
            'start_token': start_token,
            'end_token': end_token,
            'frame': trigger_dict.get('frame', '')
        }
    
    # Build normalized structure
    processed = {
        'report': {
            'text': report_text,
            'annotations': convert_template(instance.get('report_template', {}), report_tokens),
            'trigger': extract_trigger_11(trigger_data, report_tokens)
        },
        'source': {
            'text': source_text,
            'annotations': convert_template(instance.get('source_template', {}), source_tokens),
            'trigger': None  # Source trigger not in FAMuS 1.1
        }
    }
    
    # Enrich with ontology if available
    if ontology and frame_name in ontology:
        frame_data = ontology[frame_name]
        all_roles = frame_data.get('all_roles', {})
        
        for ann in processed['report']['annotations']:
            if ann['role'] in all_roles:
                ann['role_definition'] = all_roles[ann['role']]
        
        for ann in processed['source']['annotations']:
            if ann['role'] in all_roles:
                ann['role_definition'] = all_roles[ann['role']]
    
    # Normalize all annotations
    processed['report']['annotations'] = [
        normalize_annotation(ann) for ann in processed['report']['annotations']
    ]
    processed['source']['annotations'] = [
        normalize_annotation(ann) for ann in processed['source']['annotations']
    ]
    processed['report']['trigger'] = normalize_trigger(processed['report']['trigger'])
    processed['source']['trigger'] = normalize_trigger(processed['source']['trigger'])
    
    return processed


def create_unified_instance(instance_id, frame, v10_data, v11_data, ontology=None):
    """Create a unified instance with both versions."""
    # Get frame data from ontology
    frame_definition = ''
    frame_gloss = ''
    frame_ancestors = []
    frame_descendants = []
    
    if ontology and frame in ontology:
        frame_data = ontology[frame]
        frame_definition = frame_data.get('definition', '')
        frame_ancestors = frame_data.get('ancestors', [])
        frame_descendants = frame_data.get('descendants', [])
    
    # Check if versions differ
    has_differences = versions_differ(v10_data, v11_data)
    
    return {
        'instance_id': instance_id,
        'frame': frame,
        'frame_gloss': frame_gloss,
        'frame_definition': frame_definition,
        'frame_ancestors': frame_ancestors,
        'frame_descendants': frame_descendants,
        'has_differences': has_differences,
        'v1_0': v10_data,
        'v1_1': v11_data
    }


def chunk_data(data, chunk_size=100):
    """Split data into chunks."""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]


def main():
    parser = argparse.ArgumentParser(description='Process and unify FAMuS datasets')
    parser.add_argument('--famus10-dir', type=str, required=True,
                        help='Directory containing FAMuS 1.0 JSONL files')
    parser.add_argument('--famus11-dir', type=str, required=True,
                        help='Directory containing FAMuS 1.1 JSON files')
    parser.add_argument('--output-dir', type=str, default='assets/data/famus',
                        help='Output directory for unified JSON files')
    parser.add_argument('--ontology-dir', type=str, default='assets/data/ontology',
                        help='Directory containing processed ontology data')
    parser.add_argument('--chunk-size', type=int, default=100,
                        help='Number of records per JSON file')
    args = parser.parse_args()
    
    v10_path = Path(args.famus10_dir)
    v11_path = Path(args.famus11_dir)
    output_path = Path(args.output_dir)
    ontology_path = Path(args.ontology_dir)
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load ontology
    ontology = load_ontology(ontology_path)
    
    # Load FAMuS 1.0 data
    print("Loading FAMuS 1.0 data...")
    v10_instances = {}
    splits_10 = {}
    
    for split in ['train', 'dev', 'test']:
        split_file = v10_path / f'{split}.jsonl'
        if split_file.exists():
            print(f"  Processing {split} split...")
            with open(split_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        instance = json.loads(line)
                        instance_id = instance['instance_id']
                        frame = instance.get('frame', '')
                        v10_instances[instance_id] = {
                            'data': process_famus_10_instance(instance, ontology),
                            'frame': frame,
                            'split': split
                        }
                        splits_10[instance_id] = split
    
    print(f"  Loaded {len(v10_instances)} FAMuS 1.0 instances")
    
    # Load FAMuS 1.1 data
    print("Loading FAMuS 1.1 data...")
    v11_instances = {}
    
    for split in ['train', 'dev', 'test']:
        split_file = v11_path / f'{split}.json'
        if split_file.exists():
            print(f"  Processing {split} split...")
            with open(split_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for instance in data:
                    instance_id = instance['instance_id']
                    v11_instances[instance_id] = process_famus_11_instance(instance, ontology)
    
    print(f"  Loaded {len(v11_instances)} FAMuS 1.1 instances")
    
    # Create unified instances
    print("Creating unified instances...")
    unified_instances = []
    instances_with_differences = 0
    
    # Use FAMuS 1.0 as the base (it has split information)
    for instance_id, v10_info in v10_instances.items():
        v10_data = v10_info['data']
        frame = v10_info['frame']
        split = v10_info['split']
        
        # Get corresponding v1.1 data
        v11_data = v11_instances.get(instance_id)
        
        if v11_data:
            unified = create_unified_instance(instance_id, frame, v10_data, v11_data, ontology)
            unified['split'] = split
            unified_instances.append(unified)
            
            if unified['has_differences']:
                instances_with_differences += 1
        else:
            print(f"  Warning: No FAMuS 1.1 data for {instance_id}")
    
    print(f"Created {len(unified_instances)} unified instances")
    print(f"Instances with differences: {instances_with_differences} ({instances_with_differences/len(unified_instances)*100:.1f}%)")
    
    # Create metadata
    metadata = {
        'total_instances': len(unified_instances),
        'chunk_size': args.chunk_size,
        'num_chunks': (len(unified_instances) + args.chunk_size - 1) // args.chunk_size,
        'instances_with_differences': instances_with_differences,
        'percentage_with_differences': round(instances_with_differences / len(unified_instances) * 100, 2),
        'frames': list(set(inst['frame'] for inst in unified_instances)),
        'splits': {
            'train': sum(1 for inst in unified_instances if inst['split'] == 'train'),
            'dev': sum(1 for inst in unified_instances if inst['split'] == 'dev'),
            'test': sum(1 for inst in unified_instances if inst['split'] == 'test')
        }
    }
    
    # Save metadata
    with open(output_path / 'metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    # Save chunked data
    for idx, chunk in enumerate(chunk_data(unified_instances, args.chunk_size)):
        chunk_file = output_path / f'chunk_{idx:04d}.json'
        with open(chunk_file, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, separators=(',', ':'))
        print(f"Saved chunk {idx} with {len(chunk)} instances")
    
    # Create frame index
    frame_index = defaultdict(list)
    for idx, instance in enumerate(unified_instances):
        frame = instance['frame']
        frame_index[frame].append({
            'instance_id': instance['instance_id'],
            'idx': idx,
            'has_differences': instance['has_differences']
        })
    
    with open(output_path / 'frame_index.json', 'w', encoding='utf-8') as f:
        json.dump(dict(frame_index), f, indent=2)
    
    # Create search index
    search_data = []
    for idx, instance in enumerate(unified_instances):
        # Use v1.0 for search by default
        v10 = instance['v1_0']
        search_entry = {
            'id': idx,
            'instance_id': instance['instance_id'],
            'frame_name': instance['frame'],
            'frame_gloss': instance['frame_gloss'],
            'frame_definition': instance['frame_definition'],
            'frame_ancestors': instance['frame_ancestors'],
            'report_text': v10['report']['text'][:500],
            'source_text': v10['source']['text'][:500],
            'roles': list(set(
                ann['role'] for ann in 
                v10['report']['annotations'] + v10['source']['annotations']
                if 'role' in ann
            )),
            'has_differences': instance['has_differences']
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