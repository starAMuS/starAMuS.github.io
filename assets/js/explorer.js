// AMuS Dataset Explorer Vue.js Application
const { createApp } = Vue;

const ExplorerApp = {
  data() {
    return {
      // Current state
      currentExample: null,
      currentIndex: 0,
      currentChunk: null,
      currentChunkId: -1,
      
      // Search state
      searchQuery: '',
      searchResults: [],
      
      // Data state
      famusMetadata: null,
      seamusMetadata: null,
      famusSearchIndex: null,
      seamusSearchIndex: null,
      seamusInstanceMapping: {},  // Maps FAMuS instance IDs to SEAMuS data
      totalExamples: 0,
      
      // Version state
      currentVersion: '1.0',  // '1.0' or '1.1'
      versionToggleEnabled: true,  // Whether toggle is enabled based on differences
      
      // UI state
      loading: false,
      error: null,
      showAnnotations: true,
      
      // Cache for loaded chunks
      chunkCache: new Map(),
      seamusChunks: {},
      
      // Ontology data
      ontologyFrames: null,
      frameHierarchy: null,
      
      // Lunr search indices
      famusLunrIndex: null,
      
      // Search filters
      searchFilters: {
        frames: true,
        text: true,
        roles: true,
        summaries: false
      },
      
      // Frame hierarchy browser
      showFrameHierarchy: false,
      hierarchyFilter: '',
      expandedFrames: {},
      
      // Descendants accordion state
      showAllDescendants: false,
      
      // Role color mapping (like inspiration interface)
      roleColorMapping: null,
      
      // Set of frames that have examples
      framesWithExamples: new Set()
    }
  },
  
  computed: {
    dataPath() {
      // Since explorer.html is at the root level, assets/data/ is also at root
      const fullPath = 'assets/data/';
      console.log('Data path computed:', fullPath);
      return fullPath;
    },
    
    filteredRootFrames() {
      if (!this.frameHierarchy || !this.frameHierarchy.roots) return [];
      
      if (!this.hierarchyFilter) {
        return this.frameHierarchy.roots;
      }
      
      // When filtering, find all matching frames and their paths to root
      const filter = this.hierarchyFilter.toLowerCase();
      const matchingFrames = new Set();
      
      // Find all frames that match the filter
      if (this.frameHierarchy.children) {
        Object.keys(this.frameHierarchy.children).forEach(frame => {
          if (frame.toLowerCase().includes(filter)) {
            matchingFrames.add(frame);
            // Add all ancestors to show the path
            this.addAncestorsToSet(frame, matchingFrames);
          }
        });
      }
      
      // Also check root frames
      this.frameHierarchy.roots.forEach(frame => {
        if (frame.toLowerCase().includes(filter)) {
          matchingFrames.add(frame);
        }
      });
      
      // Return root frames that are either matching or have matching descendants
      return this.frameHierarchy.roots.filter(root => 
        matchingFrames.has(root) || this.hasMatchingDescendants(root, filter)
      );
    }
  },
  
  updated() {
    // Setup tooltips whenever the DOM updates
    this.setupRoleTooltips();
  },
  
  async mounted() {
    console.log('Vue app mounted, starting data load...');
    
    try {
      // Load metadata for both datasets
      await this.loadMetadata();
      
      // Load search indices
      await this.loadSearchIndices();
      
      // Load SEAMuS instance mapping BEFORE building indices
      await this.loadSeamusMapping();
      
      // Load ontology data
      await this.loadOntology();
      
      // Load frame hierarchy
      await this.loadFrameHierarchy();
      
      // Build Lunr indices (must be after SEAMuS mapping is loaded)
      await this.buildLunrIndices();
      
      // Build set of frames with examples
      this.buildFramesWithExamplesSet();
      
      console.log('All data loaded successfully');
      
      // Initialize MDL components after data is loaded
      this.$nextTick(() => {
        if (typeof componentHandler !== 'undefined') {
          componentHandler.upgradeDom();
        }
        // Initialize role popovers
        this.initRolePopovers();
      });
    } catch (error) {
      console.error('Error during initialization:', error);
      this.error = 'Failed to initialize the explorer. Please check the console for details.';
    }
  },
  
  methods: {
    async loadMetadata() {
      try {
        console.log('Loading metadata from:', this.dataPath);
        // Load unified FAMuS metadata
        const famusUrl = `${this.dataPath}famus/metadata.json`;
        console.log('Fetching FAMuS metadata from:', famusUrl);
        const famusResponse = await fetch(famusUrl);
        if (famusResponse.ok) {
          this.famusMetadata = await famusResponse.json();
          console.log('FAMuS metadata loaded:', this.famusMetadata);
          console.log('Instances with differences:', this.famusMetadata.instances_with_differences);
        } else {
          console.error('Failed to load FAMuS metadata:', famusResponse.status, famusResponse.statusText);
        }
        
        // Load SEAMuS metadata
        const seamusUrl = `${this.dataPath}seamus/metadata.json`;
        console.log('Fetching SEAMuS metadata from:', seamusUrl);
        const seamusResponse = await fetch(seamusUrl);
        if (seamusResponse.ok) {
          this.seamusMetadata = await seamusResponse.json();
          console.log('SEAMuS metadata loaded:', this.seamusMetadata);
        } else {
          console.error('Failed to load SEAMuS metadata:', seamusResponse.status, seamusResponse.statusText);
        }
      } catch (error) {
        console.error('Error loading metadata:', error);
        this.error = 'Failed to load dataset metadata. Please check the console for details.';
      }
    },
    
    async loadSearchIndices() {
      try {
        // Load unified FAMuS search index
        const famusResponse = await fetch(`${this.dataPath}famus/search_index.json`);
        if (famusResponse.ok) {
          this.famusSearchIndex = await famusResponse.json();
          console.log('FAMuS search index loaded, items:', this.famusSearchIndex?.length);
        } else {
          console.error('Failed to load FAMuS search index:', famusResponse.status);
        }
        
        // Load SEAMuS search index
        const seamusResponse = await fetch(`${this.dataPath}seamus/search_index.json`);
        if (seamusResponse.ok) {
          this.seamusSearchIndex = await seamusResponse.json();
          console.log('SEAMuS search index loaded, items:', this.seamusSearchIndex?.length);
        } else {
          console.error('Failed to load SEAMuS search index:', seamusResponse.status);
        }
      } catch (error) {
        console.error('Error loading search indices:', error);
      }
    },
    
    async loadSeamusMapping() {
      try {
        const response = await fetch(`${this.dataPath}seamus/instance_mapping.json`);
        if (response.ok) {
          this.seamusInstanceMapping = await response.json();
          console.log('SEAMuS instance mapping loaded');
        }
      } catch (error) {
        console.error('Error loading SEAMuS mapping:', error);
      }
    },
    
    async loadOntology() {
      try {
        const response = await fetch(`${this.dataPath}ontology/frames.json`);
        if (response.ok) {
          this.ontologyFrames = await response.json();
        }
      } catch (error) {
        console.error('Error loading ontology:', error);
      }
    },
    
    async loadFrameHierarchy() {
      try {
        const response = await fetch(`${this.dataPath}ontology/hierarchy.json`);
        if (response.ok) {
          this.frameHierarchy = await response.json();
        }
      } catch (error) {
        console.error('Error loading frame hierarchy:', error);
      }
    },
    
    async buildLunrIndices() {
      // Build FAMuS Lunr index (primary search index)
      if (this.famusSearchIndex && this.famusSearchIndex.length > 0) {
        const famusIndex = this.famusSearchIndex;
        try {
          // Store references outside the lunr function to avoid context issues
          const seamusMapping = this.seamusInstanceMapping;
          
          this.famusLunrIndex = lunr(function() {
            this.ref('id');
            this.field('frame_name', { boost: 3 });
            this.field('frame_gloss', { boost: 2 });
            this.field('frame_definition', { boost: 2 });
            this.field('frame_ancestors');
            this.field('report_text');
            this.field('source_text');
            this.field('roles', { boost: 2 });
            this.field('seamus_summary', { boost: 2 });
            
            famusIndex.forEach((doc) => {
              // Check if this document has a SEAMuS summary
              let seamusSummary = '';
              if (doc.instance_id && seamusMapping && seamusMapping[doc.instance_id]) {
                try {
                  const seamusData = seamusMapping[doc.instance_id];
                  if (seamusData && seamusData.length > 0) {
                    // Combine both summaries for search
                    const reportSummary = seamusData[0].report_summary || '';
                    const combinedSummary = seamusData[0].combined_summary || '';
                    const reportText = Array.isArray(reportSummary) ? reportSummary.join(' ') : reportSummary;
                    const combinedText = Array.isArray(combinedSummary) ? combinedSummary.join(' ') : combinedSummary;
                    seamusSummary = `${reportText} ${combinedText}`.trim();
                  }
                } catch (error) {
                  console.warn('Error processing SEAMuS data for', doc.instance_id, error);
                }
              }
              
              // Flatten arrays for Lunr
              const indexDoc = {
                ...doc,
                frame_ancestors: doc.frame_ancestors ? doc.frame_ancestors.join(' ') : '',
                roles: doc.roles ? doc.roles.join(' ') : '',
                seamus_summary: seamusSummary
              };
              this.add(indexDoc);
            }, this);
          });
          console.log('FAMuS Lunr index built with', this.famusSearchIndex.length, 'documents');
        } catch (error) {
          console.error('Error building Lunr index:', error);
        }
      }
    },
    
    async loadChunk(dataset, chunkId, cache = null) {
      const cacheToUse = cache || this.chunkCache;
      const cacheKey = `${dataset}-${chunkId}`;
      
      // Check cache first
      if (cacheToUse.has(cacheKey)) {
        return cacheToUse.get(cacheKey);
      }
      
      try {
        const response = await fetch(`${this.dataPath}${dataset}/chunk_${String(chunkId).padStart(4, '0')}.json`);
        if (response.ok) {
          const data = await response.json();
          cacheToUse.set(cacheKey, data);
          return data;
        }
      } catch (error) {
        console.error('Error loading chunk:', error);
      }
      
      return null;
    },
    
    async loadExample(id) {
      this.loading = true;
      this.error = null;
      this.showAllDescendants = false;  // Reset accordion state
      
      try {
        const metadata = this.famusMetadata;
        if (!metadata) return;
        
        // Calculate which chunk contains this example
        const chunkSize = metadata.chunk_size;
        const chunkId = Math.floor(id / chunkSize);
        const indexInChunk = id % chunkSize;
        
        // Load chunk if needed
        if (chunkId !== this.currentChunkId || this.currentChunk === null) {
          this.currentChunk = await this.loadChunk('famus', chunkId);
          this.currentChunkId = chunkId;
        }
        
        if (this.currentChunk && this.currentChunk[indexInChunk]) {
          const unifiedExample = this.currentChunk[indexInChunk];
          
          // Extract the current version's data
          const versionKey = this.currentVersion === '1.1' ? 'v1_1' : 'v1_0';
          const versionData = unifiedExample[versionKey];
          
          // Build currentExample from unified data
          this.currentExample = {
            instance_id: unifiedExample.instance_id,
            frame: unifiedExample.frame,
            frame_gloss: unifiedExample.frame_gloss,
            frame_definition: unifiedExample.frame_definition,
            frame_ancestors: unifiedExample.frame_ancestors ? [...new Set(unifiedExample.frame_ancestors)] : [],
            frame_descendants: unifiedExample.frame_descendants ? [...new Set(unifiedExample.frame_descendants)] : [],
            has_differences: unifiedExample.has_differences,
            report: versionData.report,
            source: versionData.source,
            split: unifiedExample.split
          };
          
          this.currentIndex = id;
          this.totalExamples = metadata.total_instances;
          
          // Update toggle state based on differences
          this.versionToggleEnabled = unifiedExample.has_differences;
          
          // Add frame descendants if available (and deduplicate)
          if (this.frameHierarchy && this.currentExample.frame) {
            const descendants = this.getFrameDescendants(this.currentExample.frame);
            if (descendants.length > 0) {
              this.currentExample.frame_descendants = [...new Set(descendants)];
            }
          }
          
          // Check if there's a SEAMuS summary for this instance
          const instanceId = this.currentExample.instance_id;
          if (instanceId && this.seamusInstanceMapping[instanceId]) {
            await this.enrichWithSeamus(instanceId);
          }
          
          // Create role color map for this example
          this.currentExample.roleColorMap = this.createRoleColorMapForExample();
        }
      } catch (error) {
        this.error = 'Error loading example: ' + error.message;
      } finally {
        this.loading = false;
        // Setup tooltips for role annotations after content loads
        this.setupRoleTooltips();
      }
    },
    
    async switchVersion(version) {
      if (version === this.currentVersion || !this.versionToggleEnabled) return;
      
      this.currentVersion = version;
      
      // Clear any existing errors when switching versions
      this.error = null;
      
      // If we have a current example, just update to show the new version
      if (this.currentExample && this.currentChunk) {
        // Find the unified example in current chunk
        const indexInChunk = this.currentIndex % this.famusMetadata.chunk_size;
        const unifiedExample = this.currentChunk[indexInChunk];
        
        if (unifiedExample) {
          // Extract the new version's data
          const versionKey = version === '1.1' ? 'v1_1' : 'v1_0';
          const versionData = unifiedExample[versionKey];
          
          // Preserve SEAMuS data if it exists
          const seamusData = {
            seamus_report_summary: this.currentExample.seamus_report_summary,
            seamus_report_template: this.currentExample.seamus_report_template,
            seamus_combined_summary: this.currentExample.seamus_combined_summary,
            seamus_combined_template: this.currentExample.seamus_combined_template
          };
          
          // Update currentExample with new version data
          this.currentExample = {
            instance_id: unifiedExample.instance_id,
            frame: unifiedExample.frame,
            frame_gloss: unifiedExample.frame_gloss,
            frame_definition: unifiedExample.frame_definition,
            frame_ancestors: unifiedExample.frame_ancestors,
            frame_descendants: unifiedExample.frame_descendants,
            has_differences: unifiedExample.has_differences,
            report: versionData.report,
            source: versionData.source,
            split: unifiedExample.split
          };
          
          // Restore SEAMuS data if it existed
          if (seamusData.seamus_report_summary) {
            this.currentExample.seamus_report_summary = seamusData.seamus_report_summary;
            this.currentExample.seamus_report_template = seamusData.seamus_report_template;
          }
          if (seamusData.seamus_combined_summary) {
            this.currentExample.seamus_combined_summary = seamusData.seamus_combined_summary;
            this.currentExample.seamus_combined_template = seamusData.seamus_combined_template;
          }
          
          // Regenerate role color map for the new version
          this.currentExample.roleColorMap = this.createRoleColorMapForExample();
          
          // Setup tooltips for new content
          this.setupRoleTooltips();
        }
      }
    },
    
    
    async enrichWithSeamus(instanceId) {
      // Get SEAMuS data for this FAMuS instance
      const seamusData = this.seamusInstanceMapping[instanceId];
      if (seamusData && seamusData.length > 0) {
        // For now, take the first SEAMuS entry if multiple exist
        const seamusMapping = seamusData[0];
        
        // Load the full SEAMuS data if we have the index
        if (seamusMapping.idx !== undefined) {
          const chunkId = Math.floor(seamusMapping.idx / 1000);
          const chunkKey = `seamus-${chunkId}`;
          
          // Load chunk if not already loaded
          if (!this.seamusChunks[chunkKey]) {
            try {
              const response = await fetch(`assets/data/seamus/chunk_${chunkId.toString().padStart(4, '0')}.json`);
              if (response.ok) {
                const chunk = await response.json();
                this.seamusChunks[chunkKey] = chunk;
              }
            } catch (error) {
              console.error('Error loading SEAMuS chunk:', error);
              return;
            }
          }
          
          // Get the full SEAMuS data from the chunk
          const chunk = this.seamusChunks[chunkKey];
          if (chunk) {
            const seamusEntry = chunk[seamusMapping.idx % 1000];
            if (seamusEntry) {
              this.currentExample.seamus_report_summary = seamusEntry.report_summary;
              this.currentExample.seamus_report_template = seamusEntry.report_summary_template;
              this.currentExample.seamus_combined_summary = seamusEntry.combined_summary;
              this.currentExample.seamus_combined_template = seamusEntry.combined_summary_template;
              this.currentExample.seamus_id = seamusEntry.id;
              console.log('Enriched with SEAMuS data:', seamusEntry);
            }
          }
        }
      }
    },
    
    async performSearch() {
      if (!this.searchQuery.trim()) {
        return;
      }
      
      // Ensure at least one filter is selected
      if (!this.searchFilters.frames && !this.searchFilters.text && !this.searchFilters.roles && !this.searchFilters.summaries) {
        // If no filters selected, select all by default
        this.searchFilters.frames = true;
        this.searchFilters.text = true;
        this.searchFilters.roles = true;
      }
      
      this.loading = true;
      this.searchResults = [];
      this.error = null;
      
      try {
        if (this.famusLunrIndex) {
          // Use Lunr.js search
          this.searchResults = this.performLunrSearch();
        } else {
          // Fallback to simple search
          this.searchResults = this.performSimpleSearch();
        }
        
        // Clear current example to show search results
        this.currentExample = null;
      } catch (error) {
        console.error('Error during search:', error);
        this.error = 'Search failed: ' + error.message;
      } finally {
        this.loading = false;
      }
    },
    
    performLunrSearch() {
      // Use the unified search index
      const lunrIndex = this.famusLunrIndex;
      const searchIndex = this.famusSearchIndex;
      
      if (!lunrIndex || !searchIndex) return [];
      
      // Build query based on active filters
      let query = this.searchQuery;
      
      try {
        let lunrResults = [];
        
        // Search in each field separately and combine results
        if (this.searchFilters.frames) {
          // Search frame names - try exact match first, then with wildcard
          try {
            const frameNameResults = lunrIndex.search(`frame_name:${query}`);
            lunrResults = lunrResults.concat(frameNameResults);
            
            // Also try with wildcard for partial matches
            if (frameNameResults.length === 0) {
              const wildcardResults = lunrIndex.search(`frame_name:${query.toLowerCase()}*`);
              lunrResults = lunrResults.concat(wildcardResults);
            }
          } catch (e) {
            console.error('Frame name search error:', e);
          }
          
          // Search frame glosses
          try {
            const glossResults = lunrIndex.search(`frame_gloss:${query.toLowerCase()}*`);
            lunrResults = lunrResults.concat(glossResults);
          } catch (e) {
            console.error('Frame gloss search error:', e);
          }
          
          // Search frame definitions
          try {
            const defResults = lunrIndex.search(`frame_definition:${query.toLowerCase()}*`);
            lunrResults = lunrResults.concat(defResults);
          } catch (e) {
            console.error('Frame definition search error:', e);
          }
        }
        
        if (this.searchFilters.text) {
          // Search report text
          try {
            const reportResults = lunrIndex.search(`report_text:${query.toLowerCase()}*`);
            lunrResults = lunrResults.concat(reportResults);
          } catch (e) {
            console.error('Report text search error:', e);
          }
          
          // Search source text
          try {
            const sourceResults = lunrIndex.search(`source_text:${query.toLowerCase()}*`);
            lunrResults = lunrResults.concat(sourceResults);
          } catch (e) {
            console.error('Source text search error:', e);
          }
        }
        
        if (this.searchFilters.roles) {
          // Search roles
          try {
            const roleResults = lunrIndex.search(`roles:${query.toLowerCase()}*`);
            lunrResults = lunrResults.concat(roleResults);
          } catch (e) {
            console.error('Roles search error:', e);
          }
        }
        
        if (this.searchFilters.summaries) {
          // Search SEAMuS summaries
          try {
            const summaryResults = lunrIndex.search(`seamus_summary:${query.toLowerCase()}*`);
            lunrResults = lunrResults.concat(summaryResults);
          } catch (e) {
            console.error('Summary search error:', e);
          }
        }
        
        // If no specific filters, search all fields
        if (!this.searchFilters.frames && !this.searchFilters.text && !this.searchFilters.roles) {
          lunrResults = lunrIndex.search(`${query}*`);
        }
        
        // Remove duplicates based on ref
        const uniqueResults = [];
        const seen = new Set();
        for (const result of lunrResults) {
          if (!seen.has(result.ref)) {
            seen.add(result.ref);
            uniqueResults.push(result);
          }
        }
        
        // Sort by score
        uniqueResults.sort((a, b) => b.score - a.score);
        
        // Map Lunr results back to full documents
        let mappedResults = uniqueResults.slice(0, 100).map(result => {
          const doc = searchIndex.find(d => d.id == result.ref);
          
          // Get SEAMuS summaries
          let seamusCombinedSummary = null;
          let seamusReportSummary = null;
          
          if (doc.instance_id && this.seamusInstanceMapping[doc.instance_id]) {
            const seamusData = this.seamusInstanceMapping[doc.instance_id];
            if (seamusData.length > 0) {
              // Store the summaries for preview
              if (seamusData[0].combined_summary) {
                seamusCombinedSummary = Array.isArray(seamusData[0].combined_summary) 
                  ? seamusData[0].combined_summary.join(' ') 
                  : seamusData[0].combined_summary;
              }
              if (seamusData[0].report_summary) {
                seamusReportSummary = Array.isArray(seamusData[0].report_summary) 
                  ? seamusData[0].report_summary.join(' ') 
                  : seamusData[0].report_summary;
              }
            }
          }
          
          return {
            ...doc,
            score: result.score,
            frame: doc.frame_name || 'Unknown',
            seamus_combined_summary: seamusCombinedSummary,
            seamus_report_summary: seamusReportSummary
          };
        });
        
        return mappedResults.slice(0, 50);
      } catch (error) {
        // If Lunr query parsing fails, fall back to simple search
        console.warn('Lunr search failed, falling back to simple search:', error);
        return this.performSimpleSearch();
      }
    },
    
    performSimpleSearch() {
      const searchIndex = this.famusSearchIndex;
      
      if (!searchIndex) return [];
      
      const query = this.searchQuery.toLowerCase();
      let results = searchIndex.filter(item => {
        let matches = false;
        
        // Apply filters
        if (this.searchFilters.frames) {
          if (item.frame_name && item.frame_name.toLowerCase().includes(query)) matches = true;
          if (item.frame_gloss && item.frame_gloss.toLowerCase().includes(query)) matches = true;
          if (item.frame_definition && item.frame_definition.toLowerCase().includes(query)) matches = true;
        }
        
        if (this.searchFilters.text && !matches) {
          if (item.report_text && item.report_text.toLowerCase().includes(query)) matches = true;
          if (item.source_text && item.source_text.toLowerCase().includes(query)) matches = true;
        }
        
        if (this.searchFilters.roles && !matches) {
          if (item.roles && item.roles.some(r => r.toLowerCase().includes(query))) matches = true;
        }
        
        if (this.searchFilters.summaries && !matches) {
          // Check SEAMuS summaries
          if (item.instance_id && this.seamusInstanceMapping[item.instance_id]) {
            const seamusData = this.seamusInstanceMapping[item.instance_id];
            if (seamusData.length > 0 && seamusData[0].summary && 
                seamusData[0].summary.toLowerCase().includes(query)) {
              matches = true;
            }
          }
        }
        
        return matches;
      });
      
      // Map results and add SEAMuS info
      results = results.map(r => {
        let seamusCombinedSummary = null;
        let seamusReportSummary = null;
        
        if (r.instance_id && this.seamusInstanceMapping[r.instance_id]) {
          const seamusData = this.seamusInstanceMapping[r.instance_id];
          if (seamusData.length > 0) {
            // Store the summaries for preview
            if (seamusData[0].combined_summary) {
              seamusCombinedSummary = Array.isArray(seamusData[0].combined_summary) 
                ? seamusData[0].combined_summary.join(' ') 
                : seamusData[0].combined_summary;
            }
            if (seamusData[0].report_summary) {
              seamusReportSummary = Array.isArray(seamusData[0].report_summary) 
                ? seamusData[0].report_summary.join(' ') 
                : seamusData[0].report_summary;
            }
          }
        }
        
        return {
          ...r,
          frame: r.frame_name || 'Unknown',
          seamus_combined_summary: seamusCombinedSummary,
          seamus_report_summary: seamusReportSummary
        };
      });
      
      return results.slice(0, 50);
    },
    
    navigate(direction) {
      const newIndex = direction === 'next' ? this.currentIndex + 1 : this.currentIndex - 1;
      if (newIndex >= 0 && newIndex < this.totalExamples) {
        this.loadExample(newIndex);
      }
    },
    
    renderAnnotatedText(text, annotations, trigger = null, roleColorMap = null) {
      if (!this.showAnnotations) {
        return this.escapeHtml(text);
      }
      
      // Use provided color map or create one if not provided
      if (!roleColorMap) {
        roleColorMap = this.createRoleColorMapForExample();
      }
      
      // Collect all spans first (before assigning colors)
      const allSpans = [];
      
      // Add trigger span if it exists
      if (trigger && trigger.start_char !== undefined && trigger.end_char !== undefined) {
        allSpans.push({
          start: trigger.start_char,
          end: trigger.end_char,
          role: trigger.frame || 'Trigger',
          roleDefinition: `Frame trigger: ${trigger.frame}`,
          annotation: trigger,
          isTrigger: true
        });
      }
      
      // Add role annotations
      for (const annotation of annotations || []) {
        const role = annotation.role || 'unknown';
        const roleDefinition = annotation.role_definition || '';
        
        // Skip annotations without span information
        if (!annotation.span) {
          console.warn('Annotation without span:', annotation);
          continue;
        }
        
        // Handle both single spans and discontiguous spans
        const spans = Array.isArray(annotation.span[0]) ? annotation.span : [annotation.span];
        
        for (const span of spans) {
          allSpans.push({
            start: span[0],
            end: span[1],
            role,
            roleDefinition,
            annotation
          });
        }
      }
      
      // Sort by start position
      allSpans.sort((a, b) => a.start - b.start);
      
      // Assign colors based on role mapping
      const colors = this.getMaterialDesignColors();
      
      for (const span of allSpans) {
        if (span.isTrigger) {
          // Triggers always get red color (index 5)
          span.roleColor = colors[5].light;
          span.darkerColor = colors[5].dark;
        } else {
          // Use consistent color from role map
          const colorPair = roleColorMap[span.role];
          if (colorPair) {
            span.roleColor = colorPair.light;
            span.darkerColor = colorPair.dark;
          } else {
            // Fallback for unmapped roles
            span.roleColor = 'rgba(158, 158, 158, 0.20)';
            span.darkerColor = '#424242';
          }
        }
      }
      
      let html = '';
      let lastEnd = 0;
      
      for (const span of allSpans) {
        // Add text before annotation
        if (span.start > lastEnd) {
          html += this.escapeHtml(text.substring(lastEnd, span.start));
        }
        
        // Skip if this span overlaps with previous one
        if (span.start < lastEnd) {
          continue;
        }
        
        // Add annotated text with popover and subscript
        const tooltipData = span.roleDefinition ? `data-tooltip="${this.escapeHtml(span.roleDefinition)}"` : '';
        
        html += `<span class="highlight-span role-popover" style="background-color: ${span.roleColor}; position: relative; padding: 4px 8px; border-radius: 4px; margin: 0 2px; display: inline-block;" ${tooltipData}>`;
        html += this.escapeHtml(text.substring(span.start, span.end + 1));
        html += `<span class="span-subscript" style="font-size: 0.65rem; font-weight: 500; background-color: ${span.darkerColor}; color: white; border-radius: 0.75rem; padding: 0.1rem 0.3rem; margin-left: 0.1rem; position: absolute; bottom: -0.5rem; right: 0; box-shadow: 0 1px 3px rgba(0,0,0,0.12); display: inline-block; z-index: 1;">${span.role}</span>`;
        html += '</span>';
        
        lastEnd = span.end + 1;
      }
      
      // Add remaining text
      if (lastEnd < text.length) {
        html += this.escapeHtml(text.substring(lastEnd));
      }
      
      return html;
    },
    
    highlightRolesInDefinition(definitionText, frameRoles, roleColorMap = null) {
      if (!definitionText || !frameRoles) {
        return this.escapeHtml(definitionText || '');
      }
      
      // Use provided color map or create one if not provided
      if (!roleColorMap) {
        roleColorMap = this.currentExample?.roleColorMap || this.createRoleColorMapForExample();
      }
      
      // Create an array to track all role occurrences with their positions
      const roleOccurrences = [];
      
      // Find all occurrences of each role in the text
      for (const [roleName, roleDefinition] of Object.entries(frameRoles)) {
        // Create regex to match whole words only - CASE SENSITIVE (no 'i' flag)
        // Only match sentence-cased role names
        const regex = new RegExp(`\\b(${this.escapeRegex(roleName)})\\b`, 'g');
        let match;
        while ((match = regex.exec(definitionText)) !== null) {
          // Only add if the match starts with uppercase (sentence-cased)
          if (match[0][0] === match[0][0].toUpperCase()) {
            roleOccurrences.push({
              start: match.index,
              end: match.index + match[0].length - 1,
              roleName: roleName,
              roleDefinition: roleDefinition,
              originalText: match[0]
            });
          }
        }
      }
      
      // Sort by start position
      roleOccurrences.sort((a, b) => a.start - b.start);
      
      // Remove overlapping occurrences (keep first)
      const filteredOccurrences = [];
      let lastEnd = -1;
      for (const occurrence of roleOccurrences) {
        if (occurrence.start > lastEnd) {
          filteredOccurrences.push(occurrence);
          lastEnd = occurrence.end;
        }
      }
      
      // Assign colors based on role mapping
      filteredOccurrences.forEach((occurrence) => {
        const colorPair = roleColorMap[occurrence.roleName];
        if (colorPair) {
          occurrence.color = colorPair.light;
          occurrence.darkerColor = colorPair.dark;
        } else {
          // Fallback for unmapped roles
          occurrence.color = 'rgba(158, 158, 158, 0.20)';
          occurrence.darkerColor = '#424242';
        }
      });
      
      // Build the HTML string
      let html = '';
      let lastPos = 0;
      
      for (const occurrence of filteredOccurrences) {
        // Add text before this occurrence
        if (occurrence.start > lastPos) {
          html += this.escapeHtml(definitionText.substring(lastPos, occurrence.start));
        }
        
        // Add highlighted role
        const tooltipData = occurrence.roleDefinition ? `data-tooltip="${this.escapeHtml(occurrence.roleDefinition)}"` : '';
        html += `<span class="highlight-span role-popover" style="background-color: ${occurrence.color}; position: relative; padding: 4px 8px; border-radius: 4px; margin: 0 2px; display: inline-block; cursor: help;" ${tooltipData}>${this.escapeHtml(occurrence.originalText)}<span class="span-subscript" style="font-size: 0.65rem; font-weight: 500; background-color: ${occurrence.darkerColor}; color: white; border-radius: 0.75rem; padding: 0.1rem 0.3rem; margin-left: 0.1rem; position: absolute; bottom: -0.5rem; right: 0; box-shadow: 0 1px 3px rgba(0,0,0,0.12); display: inline-block; z-index: 1;">${this.escapeHtml(occurrence.roleName)}</span></span>`;
        
        lastPos = occurrence.end + 1;
      }
      
      // Add remaining text
      if (lastPos < definitionText.length) {
        html += this.escapeHtml(definitionText.substring(lastPos));
      }
      
      return html;
    },
    
    // Material Design color palette for role highlighting - reordered for maximum contrast
    getMaterialDesignColors() {
      return [
        { light: 'rgba(33, 150, 243, 0.20)', dark: '#1565C0' },     // Blue 500/800
        { light: 'rgba(255, 152, 0, 0.20)', dark: '#E65100' },      // Orange 500/800
        { light: 'rgba(76, 175, 80, 0.20)', dark: '#2E7D32' },      // Green 500/800
        { light: 'rgba(156, 39, 176, 0.20)', dark: '#6A1B9A' },     // Purple 500/800
        { light: 'rgba(121, 85, 72, 0.20)', dark: '#4E342E' },      // Brown 500/800
        { light: 'rgba(244, 67, 54, 0.20)', dark: '#C62828' },      // Red 500/800 - RESERVED FOR TRIGGERS
        { light: 'rgba(0, 188, 212, 0.20)', dark: '#00838F' },      // Cyan 500/800
        { light: 'rgba(233, 30, 99, 0.20)', dark: '#AD1457' },      // Pink 500/800
        { light: 'rgba(0, 150, 136, 0.20)', dark: '#00695C' },      // Teal 500/800
        { light: 'rgba(255, 193, 7, 0.20)', dark: '#F57F17' },      // Amber 500/800
        { light: 'rgba(63, 81, 181, 0.20)', dark: '#283593' },      // Indigo 500/800
        { light: 'rgba(205, 220, 57, 0.20)', dark: '#827717' },     // Lime 500/800
        { light: 'rgba(103, 58, 183, 0.20)', dark: '#4527A0' },     // Deep Purple 500/800
        { light: 'rgba(139, 195, 74, 0.20)', dark: '#558B2F' },     // Light Green 500/800
        { light: 'rgba(96, 125, 139, 0.20)', dark: '#37474F' },     // Blue Grey 500/800
        { light: 'rgba(255, 87, 34, 0.20)', dark: '#D84315' },      // Deep Orange 500/800
        { light: 'rgba(3, 169, 244, 0.20)', dark: '#0277BD' },      // Light Blue 500/800
        { light: 'rgba(158, 158, 158, 0.20)', dark: '#424242' },    // Grey 500/800
        { light: 'rgba(255, 110, 64, 0.20)', dark: '#E64A19' },     // Deep Orange A200/800
        { light: 'rgba(124, 179, 66, 0.20)', dark: '#558B2F' }      // Light Green 600/800
      ];
    },
    
    // Create a consistent role-to-color mapping for an entire example
    createRoleColorMapForExample() {
      const roleColorMap = {};
      const uniqueRoles = new Set();
      
      // Collect all unique roles from the current example
      if (this.currentExample) {
        // From report annotations
        if (this.currentExample.report && this.currentExample.report.annotations) {
          this.currentExample.report.annotations.forEach(ann => {
            if (ann.role) uniqueRoles.add(ann.role);
          });
        }
        
        // From source annotations
        if (this.currentExample.source && this.currentExample.source.annotations) {
          this.currentExample.source.annotations.forEach(ann => {
            if (ann.role) uniqueRoles.add(ann.role);
          });
        }
        
        // From frame roles
        const frameRoles = this.getFrameRoles();
        Object.keys(frameRoles).forEach(role => uniqueRoles.add(role));
        
        // From SEAMuS templates if present
        if (this.currentExample.seamus_report_template) {
          Object.keys(this.currentExample.seamus_report_template).forEach(role => uniqueRoles.add(role));
        }
        if (this.currentExample.seamus_combined_template) {
          Object.keys(this.currentExample.seamus_combined_template).forEach(role => uniqueRoles.add(role));
        }
      }
      
      // Sort roles for consistent ordering
      const sortedRoles = [...uniqueRoles].sort();
      
      // Assign colors consistently, skipping the trigger color (index 5)
      const colors = this.getMaterialDesignColors();
      let colorIndex = 0;
      
      sortedRoles.forEach(role => {
        // Skip index 5 (red) which is reserved for triggers
        if (colorIndex === 5) colorIndex++;
        
        const colorPair = colors[colorIndex % colors.length];
        roleColorMap[role] = colorPair;
        colorIndex++;
        
        // Skip index 5 when cycling
        if ((colorIndex % colors.length) === 5) colorIndex++;
      });
      
      return roleColorMap;
    },
    
    
    buildFramesWithExamplesSet() {
      // Build a set of all frames that have examples in the dataset
      this.framesWithExamples.clear();
      
      if (this.famusSearchIndex) {
        this.famusSearchIndex.forEach(item => {
          if (item.frame_name) {
            this.framesWithExamples.add(item.frame_name);
          }
        });
      }
      
      console.log('Frames with examples loaded:', this.framesWithExamples.size);
    },
    
    frameHasExamples(frameName) {
      return this.framesWithExamples.has(frameName);
    },
    
    
    getResultPreview(result) {
      // Prioritize SEAMuS combined summary when available
      if (result.seamus_combined_summary) {
        return result.seamus_combined_summary.substring(0, 150) + '...';
      } else if (result.seamus_report_summary) {
        return result.seamus_report_summary.substring(0, 150) + '...';
      } else if (result.summary) {
        return result.summary.substring(0, 150) + '...';
      } else if (result.report_text) {
        return result.report_text.substring(0, 150) + '...';
      } else if (result.frame_definition) {
        return result.frame_definition.substring(0, 150) + '...';
      }
      return 'No preview available';
    },
    
    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    },
    
    renderSeamusSummary(type, roleColorMap = null) {
      let summary, template;
      
      if (type === 'report') {
        summary = this.currentExample.seamus_report_summary;
        template = this.currentExample.seamus_report_template;
      } else if (type === 'combined') {
        summary = this.currentExample.seamus_combined_summary;
        template = this.currentExample.seamus_combined_template;
      }
      
      if (!summary || !template) {
        return '';
      }
      
      // Join tokens if summary is an array
      const summaryText = Array.isArray(summary)
        ? summary.join(' ')
        : summary;
      
      if (!template || Object.keys(template).length === 0) {
        return this.escapeHtml(summaryText);
      }
      
      // Use provided color map or create one if not provided
      if (!roleColorMap) {
        roleColorMap = this.currentExample?.roleColorMap || this.createRoleColorMapForExample();
      }
      
      // Create a map of all annotations
      const annotations = [];
      for (const [role, data] of Object.entries(template)) {
        if (data.arguments && data.arguments.length > 0) {
          for (const arg of data.arguments) {
            // Skip empty arguments
            if (arg.start_token !== undefined && arg.end_token !== undefined && arg.start_token >= 0) {
              annotations.push({
                role,
                start_token: arg.start_token,
                end_token: arg.end_token,
                tokens: arg.tokens || []
              });
            }
          }
        }
      }
      
      // Sort annotations by start position
      annotations.sort((a, b) => a.start_token - b.start_token);
      
      // Assign colors based on role mapping
      annotations.forEach((ann) => {
        const colorPair = roleColorMap[ann.role];
        if (colorPair) {
          ann.backgroundColor = colorPair.light;
          ann.darkerColor = colorPair.dark;
        } else {
          // Fallback for unmapped roles
          ann.backgroundColor = 'rgba(158, 158, 158, 0.20)';
          ann.darkerColor = '#424242';
        }
      });
      
      // Split summary into tokens
      const tokens = Array.isArray(summary)
        ? summary
        : summary.split(' ');
      
      let html = '';
      let lastEnd = -1;
      
      for (const ann of annotations) {
        // Add tokens before this annotation
        for (let i = lastEnd + 1; i < ann.start_token && i < tokens.length; i++) {
          html += this.escapeHtml(tokens[i]) + ' ';
        }
        
        // Add annotated tokens with unique colors
        const roleDefinition = this.getFrameRoles()[ann.role] || '';
        const tooltipData = roleDefinition ? `data-tooltip="${this.escapeHtml(roleDefinition)}"` : '';
        
        html += `<span class="highlight-span role-popover" style="background-color: ${ann.backgroundColor}; position: relative; padding: 4px 8px; border-radius: 4px; margin: 0 2px; display: inline-block;" ${tooltipData}>`;
        
        // Add the tokens for this annotation
        for (let i = ann.start_token; i <= ann.end_token && i < tokens.length; i++) {
          html += this.escapeHtml(tokens[i]);
          if (i < ann.end_token) html += ' ';
        }
        
        html += `<span class="span-subscript" style="font-size: 0.65rem; font-weight: 500; background-color: ${ann.darkerColor}; color: white; border-radius: 0.75rem; padding: 0.1rem 0.3rem; margin-left: 0.1rem; position: absolute; bottom: -0.5rem; right: 0; box-shadow: 0 1px 3px rgba(0,0,0,0.12); display: inline-block; z-index: 1;">${ann.role}</span>`;
        html += '</span> ';
        
        lastEnd = ann.end_token;
      }
      
      // Add remaining tokens
      for (let i = lastEnd + 1; i < tokens.length; i++) {
        html += this.escapeHtml(tokens[i]) + ' ';
      }
      
      return html.trim();
    },
    
    escapeRegex(string) {
      return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    },
    
    getFrameRoles() {
      // Get frame roles from current example or ontology
      if (!this.currentExample || !this.currentExample.frame) {
        return {};
      }
      
      // First check if roles are enriched in the current example
      const annotations = [
        ...(this.currentExample.source?.annotations || []),
        ...(this.currentExample.report?.annotations || [])
      ];
      
      const roles = {};
      for (const ann of annotations) {
        if (ann.role && ann.role_definition) {
          roles[ann.role] = ann.role_definition;
        }
      }
      
      // If we have ontology data, use it to get all roles for this frame
      if (this.ontologyFrames && this.ontologyFrames[this.currentExample.frame]) {
        const frameData = this.ontologyFrames[this.currentExample.frame];
        Object.assign(roles, frameData.all_roles || {});
      }
      
      return roles;
    },
    
    getFrameDescendants(frameName) {
      return this.getFrameChildren(frameName);
    },
    
    getFrameChildren(frameName) {
      if (!this.frameHierarchy || !this.frameHierarchy.children) {
        return [];
      }
      return this.frameHierarchy.children[frameName] || [];
    },
    
    addAncestorsToSet(frameName, set) {
      if (!this.frameHierarchy || !this.frameHierarchy.parents) return;
      
      const parents = this.frameHierarchy.parents[frameName];
      if (parents && parents.length > 0) {
        parents.forEach(parent => {
          set.add(parent);
          this.addAncestorsToSet(parent, set);
        });
      }
    },
    
    hasMatchingDescendants(frameName, filter) {
      const children = this.getFrameChildren(frameName);
      
      for (const child of children) {
        if (child.toLowerCase().includes(filter)) {
          return true;
        }
        if (this.hasMatchingDescendants(child, filter)) {
          return true;
        }
      }
      
      return false;
    },
    
    shouldShowFrame(frameName) {
      if (!this.hierarchyFilter) return true;
      
      const filter = this.hierarchyFilter.toLowerCase();
      // Show if the frame matches or has matching descendants
      return frameName.toLowerCase().includes(filter) || 
             this.hasMatchingDescendants(frameName, filter);
    },
    
    toggleFrameExpansion(frameName) {
      this.expandedFrames[frameName] = !this.expandedFrames[frameName];
    },
    
    searchForFrame(frameName) {
      this.searchQuery = frameName;
      this.searchFilters.frames = true;
      this.showFrameHierarchy = false;
      this.performSearch();
    },
    
    onSearchInput() {
      // This could be enhanced with debouncing and autocomplete
      // For now, it's a placeholder for future enhancements
    },
    
    initRolePopovers() {
      // Initialize popovers for role annotations
      document.addEventListener('click', (e) => {
        // Close all open popovers when clicking outside
        const existingPopover = document.querySelector('.role-tooltip');
        if (existingPopover && !e.target.closest('.role-popover')) {
          existingPopover.remove();
        }
      });
    },
    
    setupRoleTooltips() {
      // This will be called after the DOM updates with new content
      this.$nextTick(() => {
        const roleElements = document.querySelectorAll('.role-popover[data-tooltip]');
        
        // Remove existing event listeners to prevent duplicates
        roleElements.forEach(element => {
          element.removeEventListener('mouseenter', this.showRoleTooltip);
          element.removeEventListener('mouseleave', this.hideRoleTooltip);
          element.removeEventListener('click', this.toggleRolePopover);
        });
        
        // Add new event listeners
        roleElements.forEach(element => {
          element.addEventListener('mouseenter', this.showRoleTooltip.bind(this));
          element.addEventListener('mouseleave', this.hideRoleTooltip.bind(this));
          element.addEventListener('click', this.toggleRolePopover.bind(this));
        });
      });
    },
    
    showRoleTooltip(event) {
      const element = event.target.closest('.role-popover');
      if (!element) return;
      
      const tooltipText = element.getAttribute('data-tooltip');
      if (!tooltipText) return;
      
      // Remove existing tooltip
      const existingTooltip = document.querySelector('.role-tooltip');
      if (existingTooltip) existingTooltip.remove();
      
      // Create new tooltip
      const tooltip = document.createElement('div');
      tooltip.className = 'role-tooltip';
      tooltip.textContent = tooltipText;
      document.body.appendChild(tooltip);
      
      // Position tooltip
      const rect = element.getBoundingClientRect();
      tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
      tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
      tooltip.classList.add('visible');
    },
    
    hideRoleTooltip() {
      const tooltip = document.querySelector('.role-tooltip');
      if (tooltip) {
        tooltip.remove();
      }
    },
    
    toggleRolePopover(event) {
      event.stopPropagation();
      const element = event.target.closest('.role-popover');
      if (!element) return;
      
      const tooltipText = element.getAttribute('data-tooltip');
      if (!tooltipText) return;
      
      // Remove existing popover
      const existingPopover = document.querySelector('.role-tooltip');
      if (existingPopover) {
        existingPopover.remove();
        return;
      }
      
      // Create persistent popover
      const popover = document.createElement('div');
      popover.className = 'role-tooltip persistent';
      popover.innerHTML = `
        <div class="tooltip-content">${tooltipText}</div>
        <button class="tooltip-close" onclick="this.parentElement.remove()">×</button>
      `;
      document.body.appendChild(popover);
      
      // Position popover
      const rect = element.getBoundingClientRect();
      popover.style.left = rect.left + (rect.width / 2) - (popover.offsetWidth / 2) + 'px';
      popover.style.top = rect.top - popover.offsetHeight - 8 + 'px';
      popover.classList.add('visible');
    }
  }
};

// Create and mount the Vue app
console.log('Initializing Explorer App...');
try {
  const app = createApp(ExplorerApp);
  app.mount('#explorer-app');
  console.log('Explorer App mounted successfully');
} catch (error) {
  console.error('Error mounting Explorer App:', error);
}