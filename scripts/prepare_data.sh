#!/bin/bash
# Prepare data files for processing

set -e

echo "🔍 Checking for data files..."

# Check if data directories exist
if [ ! -d "data/famus" ]; then
    echo "⚠️  Warning: data/famus directory not found"
    echo "   Expected files: train.jsonl, dev.jsonl, test.jsonl"
fi

if [ ! -d "data/seamus" ]; then
    echo "⚠️  Warning: data/seamus directory not found"
    echo "   Expected files: train.json, dev.json, test.json"
fi

if [ ! -f "data/ontology.json" ]; then
    echo "⚠️  Warning: data/ontology.json not found"
fi

# Check for required FAMuS files
if [ -d "data/famus" ]; then
    echo "📁 Checking FAMuS data files..."
    for file in train.jsonl dev.jsonl test.jsonl; do
        if [ -f "data/famus/$file" ]; then
            echo "   ✓ $file found"
        else
            echo "   ✗ $file missing"
        fi
    done
fi

# Check for required SEAMuS files
if [ -d "data/seamus" ]; then
    echo "📁 Checking SEAMuS data files..."
    for file in train.json dev.json test.json; do
        if [ -f "data/seamus/$file" ]; then
            echo "   ✓ $file found"
        else
            echo "   ✗ $file missing"
        fi
    done
fi

# Check for ontology file
echo "📁 Checking ontology file..."
if [ -f "data/ontology.json" ]; then
    echo "   ✓ ontology.json found"
else
    echo "   ✗ ontology.json missing"
fi

echo "✅ Data check complete"
echo ""
echo "📌 Note: After running the processing scripts, you can use extract_urls.py to"
echo "   fetch real Wikipedia and source URLs from the MegaWika dataset."
echo "   This requires an internet connection and the 'datasets' package."