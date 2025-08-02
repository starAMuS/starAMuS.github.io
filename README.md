# *AMuS Dataset Explorer

An interactive web-based explorer for the FAMuS (Frames Across Multiple Sources) and SEAMuS (Summaries of Events Across Multiple Sentences) datasets, built on MegaWika.

🌐 **Live Site**: [https://staramus.github.io](https://staramus.github.io)

## Overview

This website provides an interactive interface for exploring cross-document event extraction and summarization datasets:

- **FAMuS**: Cross-document event extraction with FrameNet annotations
- **SEAMuS**: Event-keyed summarization across multiple documents
- **MegaWika**: The foundation dataset with Wikipedia-source document pairs

## Features

- 🔍 **Interactive Explorer**: Browse and search annotated examples with frame hierarchy
- 🎨 **Annotation Visualization**: Color-coded FrameNet role highlighting
- 📊 **Benchmarks Dashboard**: Interactive comparison of state-of-the-art models
- 🔗 **Source Links**: Direct access to original MegaWika documents
- 📱 **Responsive Design**: Mobile-friendly interface with Material Design
- 🌐 **Offline Support**: Service worker enables offline browsing

## Development

### Prerequisites

- Ruby (2.7+) and Bundler
- Python 3.8+ (for data processing)
- Git

### Local Setup

```bash
# Clone the repository
git clone https://github.com/starAMuS/starAMuS.github.io.git
cd starAMuS.github.io

# Install dependencies
bundle install
pip install -r requirements.txt

# Process datasets with ontology
python scripts/process_ontology.py --input-file data/ontology.json
python scripts/process_famus.py --input-dir data/famus
python scripts/process_seamus.py --input-dir data/seamus
python scripts/extract_urls.py --famus-dir assets/data/famus

# Run locally
bundle exec jekyll serve

# Visit http://localhost:4000
```

### Project Structure

```
├── _layouts/              # Jekyll layouts
│   ├── default.html       # Base layout
│   └── explorer.html      # Explorer-specific layout
├── _includes/             # Reusable components
│   ├── head.html          # HTML head section
│   └── navigation.html    # Site navigation
├── _data/                 # Jekyll data files
│   ├── benchmarks.yml     # Benchmark results data
│   └── model_descriptions.yml  # Model/metric descriptions
├── assets/                # CSS, JS, and processed data
│   ├── css/               # SCSS stylesheets
│   │   └── main.scss      # Main stylesheet
│   ├── js/                # JavaScript files
│   │   └── explorer.js    # Vue.js dataset explorer
│   └── data/              # Processed dataset chunks
│       ├── famus/         # Chunked FAMuS data
│       ├── seamus/        # Chunked SEAMuS data
│       └── ontology/      # FrameNet ontology
├── data/                  # Raw dataset files (JSONL)
│   ├── famus/            # Raw FAMuS data
│   ├── seamus/           # Raw SEAMuS data
│   └── ontology.json     # FrameNet ontology
├── scripts/               # Data processing scripts
│   ├── process_ontology.py
│   ├── process_famus.py
│   ├── process_seamus.py
│   ├── extract_urls.py
│   └── optimize_build.py
├── papers/                # Research papers and bibliography
├── .github/               # GitHub Actions workflows
├── index.html             # Homepage
├── explorer.html          # Dataset explorer
├── benchmarks.html        # Benchmark viewer
├── about.html             # About page
├── sw.js                  # Service worker for offline support
└── requirements.txt       # Python dependencies
```

### Deployment

The site automatically deploys to GitHub Pages when you push to the main branch:

1. GitHub Actions workflow processes the data
2. Jekyll builds the static site
3. Assets are optimized and minified
4. Site is deployed to GitHub Pages

To deploy manually:

```bash
# Build for production
JEKYLL_ENV=production bundle exec jekyll build

# Optimize assets
python scripts/optimize_build.py

# Deploy _site directory to your hosting
```

### Features Implementation

- **Search**: Lunr.js for client-side full-text search with chunked indexing
- **Frontend**: Vue.js 3 for reactive UI components
- **Styling**: Material Design Lite with custom SCSS
- **Visualization**: Color-coded role annotations and frame hierarchy browser
- **Performance**: Lazy loading and chunked data (1000 records per chunk)
- **Offline**: Service worker caches assets for offline browsing
- **Benchmarks**: Interactive dashboard with sortable tables and modal descriptions

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Citation

If you use these datasets in your research, please cite:

### FAMuS Dataset
```bibtex
@inproceedings{vashishtha-etal-2024-famus,
    title = "{FAM}u{S}: Frames Across Multiple Sources",
    author = "Vashishtha, Siddharth and
      Martin, Alexander and
      White, Aaron Steven and
      Van Durme, Benjamin",
    editor = "Duh, Kevin and
      Gomez, Helena and
      Bethard, Steven",
    booktitle = "Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)",
    month = jun,
    year = "2024",
    address = "Mexico City, Mexico",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2024.naacl-long.457",
    pages = "8259--8284"
}
```

### SEAMuS Dataset
```bibtex
@inproceedings{walden-etal-2025-cross,
    title = "Cross-Document Event-Keyed Summarization",
    author = "Walden, William and
      Kuchmiichuk, Pavlo and
      Martin, Alexander and
      Jin, Chihsheng and
      Cao, Angela and
      Sun, Claire and
      Allen, Curisia and
      White, Aaron",
    editor = "Fei, Hao and
      Tu, Kewei and
      Zhang, Yuhui and
      Hu, Xiang and
      Han, Wenjuan and
      Jia, Zixia and
      Zheng, Zilong and
      Cao, Yixin and
      Zhang, Meishan and
      Lu, Wei and
      Siddharth, N. and
      {\O}vrelid, Lilja and
      Xue, Nianwen and
      Zhang, Yue",
    booktitle = "Proceedings of the 1st Joint Workshop on Large Language Models and Structure Modeling (XLLM 2025)",
    month = aug,
    year = "2025",
    address = "Vienna, Austria",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2025.xllm-1.19/",
    pages = "218--241",
    ISBN = "979-8-89176-286-2"
}
```

### MegaWika Dataset
```bibtex
@article{barham2023megawika,
    title = "MegaWika: Millions of reports and their sources across 50 diverse languages",
    author = "Barham, Samuel and
      Weller, Orion and
      Yuan, Michelle and
      Murray, Kenton and
      Yarmohammadi, Mahsa and
      Jiang, Zhengping and
      Vashishtha, Siddharth and
      Martin, Alexander and
      Liu, Anqi and
      White, Aaron Steven and
      Boyd-Graber, Jordan and
      Van Durme, Benjamin",
    journal = "arXiv preprint arXiv:2307.07049",
    year = "2023",
    url = "https://arxiv.org/abs/2307.07049"
}
```

## Resources

- [FAMuS Paper (NAACL 2024)](https://aclanthology.org/2024.naacl-long.457/)
- [SEAMuS Paper (XLLM 2025)](https://aclanthology.org/2025.xllm-1.19/)
- [MegaWika Paper (arXiv)](https://arxiv.org/abs/2307.07049)
- [MegaWika on HuggingFace](https://huggingface.co/datasets/hltcoe/megawika)
- [MegaWika GitHub](https://github.com/hltcoe/megawika)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Jekyll](https://jekyllrb.com/) and [Material Design Lite](https://getmdl.io/)
- Datasets from Johns Hopkins University HLTCOE
- Inspired by the likelihood annotation interface design