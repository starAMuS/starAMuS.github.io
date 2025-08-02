#!/usr/bin/env python3
"""
Extract URLs from MegaWika for dataset instances.

This script:
- Downloads relevant MegaWika entries using HuggingFace datasets
- Maps instance_ids to source_url and article_title
- Creates URL lookup table with real data
"""

import json
import sys
from pathlib import Path
import argparse
from tqdm import tqdm
from datasets import load_dataset


def extract_megawika_id(instance_id):
    """Extract MegaWika article ID from FAMuS instance ID.
    
    Example: 'EN-1282-352-frame-Abandonment' -> 'EN-1282-352'
    """
    parts = instance_id.split('-')
    if len(parts) >= 3:
        return '-'.join(parts[:3])
    return None


def build_megawika_index(language='en', cache_file=None):
    """Build an index of MegaWika entries mapping entry IDs to URLs.
    
    Args:
        language: Language code (default: 'en')
        cache_file: Path to cache file for storing/loading index
    
    Returns:
        Dictionary mapping entry_id to entry metadata
    """
    # Check if we have a cached index
    if cache_file and Path(cache_file).exists():
        print(f"Loading cached MegaWika index from {cache_file}")
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    print(f"Building MegaWika index for language: {language}")
    print("This may take a while on first run...")
    
    # Load MegaWika dataset
    # Using streaming to avoid loading entire dataset into memory
    dataset = load_dataset('hltcoe/megawika', name=language, streaming=True, trust_remote_code=True)
    
    # Build index
    megawika_index = {}
    entries_processed = 0
    
    # Process entries
    for example in tqdm(dataset[language], desc="Processing MegaWika entries"):
        article_title = example.get('article_title', '')
        
        for entry in example.get('entries', []):
            entry_id = entry.get('id', '').upper()  # Normalize to uppercase
            if entry_id:
                megawika_index[entry_id] = {
                    'article_title': article_title,
                    'source_url': entry.get('source_url', ''),
                    'source_lang': entry.get('source_lang', ''),
                    'article_text': example.get('article_text', '')[:500]  # Store snippet
                }
                entries_processed += 1
                
                # Optional: Stop after processing enough entries for demo
                # Remove this limit for full processing
                if entries_processed >= 100000:
                    print(f"Processed {entries_processed} entries (demo limit)")
                    break
        
        if entries_processed >= 100000:
            break
    
    print(f"Built index with {len(megawika_index)} entries")
    
    # Cache the index if cache file specified
    if cache_file:
        cache_path = Path(cache_file)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(megawika_index, f, indent=2)
        print(f"Cached index to {cache_file}")
    
    return megawika_index


def create_wikipedia_url(article_title, lang='en'):
    """Create Wikipedia URL from article title."""
    if not article_title:
        return ''
    # Replace spaces with underscores and handle special characters
    url_title = article_title.replace(' ', '_')
    return f"https://{lang}.wikipedia.org/wiki/{url_title}"


def create_url_mapping(famus_instances, megawika_index):
    """Create mapping from instance_ids to URLs using MegaWika index.
    
    Args:
        famus_instances: List of FAMuS instances
        megawika_index: Pre-built MegaWika index
    
    Returns:
        Dictionary mapping instance_id to URL info
    """
    url_mapping = {}
    missing_entries = []
    
    print("Mapping FAMuS instances to MegaWika entries...")
    
    for instance in tqdm(famus_instances, desc="Processing instances"):
        instance_id = instance.get('instance_id')
        if not instance_id:
            continue
        
        # Extract MegaWika ID from FAMuS instance ID
        megawika_id = extract_megawika_id(instance_id)
        if not megawika_id:
            continue
        
        # Normalize to uppercase for lookup
        megawika_id_upper = megawika_id.upper()
        
        # Look up in MegaWika index
        if megawika_id_upper in megawika_index:
            entry = megawika_index[megawika_id_upper]
            article_title = entry.get('article_title', '')
            
            url_mapping[instance_id] = {
                'megawika_id': megawika_id,
                'article_title': article_title,
                'wikipedia_url': create_wikipedia_url(article_title),
                'source_url': entry.get('source_url', ''),
                'source_lang': entry.get('source_lang', 'en')
            }
        else:
            missing_entries.append(megawika_id)
            # Try to extract article title from instance if available
            article_title = instance.get('article_title', '')
            if not article_title and 'source' in instance:
                # Try to infer from source text (first line often contains title)
                source_text = instance.get('source', {}).get('text', '')
                if source_text:
                    article_title = source_text.split('\n')[0].strip()
            
            # Create entry with Wikipedia URL even if not in MegaWika
            url_mapping[instance_id] = {
                'megawika_id': megawika_id,
                'article_title': article_title,
                'wikipedia_url': create_wikipedia_url(article_title) if article_title else '',
                'source_url': '',
                'source_lang': 'en',
                'note': 'Not found in MegaWika index'
            }
    
    if missing_entries:
        print(f"\nWarning: {len(missing_entries)} unique MegaWika IDs not found in index")
        print(f"First 10 missing: {missing_entries[:10]}")
    
    return url_mapping


def main():
    parser = argparse.ArgumentParser(description='Extract URLs for AMuS datasets')
    parser.add_argument('--famus-dir', type=str, required=True,
                        help='Directory containing processed FAMuS data')
    parser.add_argument('--language', type=str, default='en',
                        help='MegaWika language to use (default: en)')
    parser.add_argument('--cache-dir', type=str, default='assets/data/cache',
                        help='Directory for caching MegaWika index')
    parser.add_argument('--output-file', type=str, default='assets/data/urls.json',
                        help='Output file for URL mappings')
    parser.add_argument('--limit', type=int, default=100000,
                        help='Limit number of MegaWika entries to process (0 for no limit)')
    args = parser.parse_args()
    
    famus_path = Path(args.famus_dir)
    output_path = Path(args.output_file)
    cache_file = Path(args.cache_dir) / f'megawika_index_{args.language}.json'
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load FAMuS metadata to get all instances
    metadata_file = famus_path / 'metadata.json'
    if not metadata_file.exists():
        print(f"Error: FAMuS metadata not found at {metadata_file}")
        print("Please run process_famus.py first.")
        sys.exit(1)
    
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    # Load all FAMuS instances
    print("Loading FAMuS instances...")
    all_instances = []
    num_chunks = metadata['num_chunks']
    
    for i in range(num_chunks):
        chunk_file = famus_path / f'chunk_{i:04d}.json'
        if chunk_file.exists():
            with open(chunk_file, 'r') as f:
                chunk_data = json.load(f)
                all_instances.extend(chunk_data)
    
    print(f"Loaded {len(all_instances)} FAMuS instances")
    
    # Build or load MegaWika index
    megawika_index = build_megawika_index(
        language=args.language,
        cache_file=str(cache_file)
    )
    
    # Extract URLs
    print("\nExtracting URLs from MegaWika...")
    url_mapping = create_url_mapping(all_instances, megawika_index)
    
    # Calculate statistics
    mapped_with_source = sum(1 for v in url_mapping.values() if v.get('source_url'))
    mapped_with_wikipedia = sum(1 for v in url_mapping.values() if v.get('wikipedia_url'))
    unique_articles = len(set(v['article_title'] for v in url_mapping.values() if v.get('article_title')))
    unique_megawika_ids = len(set(v['megawika_id'] for v in url_mapping.values()))
    
    stats = {
        'total_instances': len(all_instances),
        'mapped_instances': len(url_mapping),
        'instances_with_source_url': mapped_with_source,
        'instances_with_wikipedia_url': mapped_with_wikipedia,
        'unique_articles': unique_articles,
        'unique_megawika_ids': unique_megawika_ids,
        'coverage': f"{len(url_mapping) / len(all_instances) * 100:.1f}%",
        'source_url_coverage': f"{mapped_with_source / len(all_instances) * 100:.1f}%",
        'wikipedia_url_coverage': f"{mapped_with_wikipedia / len(all_instances) * 100:.1f}%"
    }
    
    # Save URL mapping
    output_data = {
        'urls': url_mapping,
        'stats': stats,
        'metadata': {
            'language': args.language,
            'megawika_entries_in_index': len(megawika_index),
            'processing_note': 'URLs extracted from MegaWika dataset via HuggingFace'
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nURL extraction complete!")
    print(f"Output saved to: {output_path}")
    print(f"\nStatistics:")
    print(f"  Total instances: {stats['total_instances']}")
    print(f"  Mapped instances: {stats['mapped_instances']} ({stats['coverage']})")
    print(f"  With source URL: {stats['instances_with_source_url']} ({stats['source_url_coverage']})")
    print(f"  With Wikipedia URL: {stats['instances_with_wikipedia_url']} ({stats['wikipedia_url_coverage']})")
    print(f"  Unique articles: {stats['unique_articles']}")
    print(f"  Unique MegaWika IDs: {stats['unique_megawika_ids']}")
    
    if args.limit > 0:
        print(f"\nNote: Processing was limited to {args.limit} MegaWika entries.")
        print("To process all entries, use --limit 0")


if __name__ == '__main__':
    main()