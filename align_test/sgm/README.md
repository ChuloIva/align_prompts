# Semantic Gravity Mapping (SGM)

A system to map LLM semantic structure by generating word association graphs and analyzing their topological properties.

## Overview

SGM reveals how concepts cluster and converge in an LLM's latent semantic space by:
1. Generating word association graphs through iterative prompting
2. Weighting associations using logprob extraction
3. Analyzing graph topology to find semantic attractors, convergence patterns, and biases

## Quick Start (Google Colab)

1. Open `notebooks/semantic_gravity_mapping.ipynb` in Google Colab
2. Run all cells (Runtime → Run all)
3. Wait 45-85 minutes for complete analysis
4. Download results from Google Drive

## Architecture

```
align_test/sgm/
├── core/
│   ├── graph_builder.py     # Phase 1: BFS expansion
│   ├── logprob_scorer.py    # Phase 2: Edge weighting
│   └── topology_analyzer.py # Phase 3: Graph analysis
├── inference/
│   └── batch_inference.py   # vLLM wrapper with batching
├── storage/
│   └── checkpoint_manager.py # Save/resume capability
└── models/
    └── seed_domains.py      # 100 seed concepts
```

## Usage

### Python API

```python
from align_test.core.vllm_client import VLLMClient
from align_test.sgm import (
    SGMInferenceEngine,
    GraphBuilder,
    LogprobScorer,
    TopologyAnalyzer,
    CheckpointManager
)

# Initialize
client = VLLMClient(model='google/gemma-3-4b-it')
engine = SGMInferenceEngine(client, temperature=0.7)
checkpoint_manager = CheckpointManager('./checkpoints')

# Phase 1: Build graph
builder = GraphBuilder(engine, checkpoint_manager)
raw_graph = builder.build_graph(max_hops=3)

# Phase 2: Score edges
engine.temperature = 0.0  # Deterministic scoring
scorer = LogprobScorer(engine, checkpoint_manager)
weighted_graph = scorer.score_all_edges(raw_graph)

# Phase 3: Analyze topology
analyzer = TopologyAnalyzer(weighted_graph)
results = analyzer.analyze_all()
analyzer.print_summary(results)
```

### Jupyter Notebook

See `notebooks/semantic_gravity_mapping.ipynb` for a complete interactive workflow.

## Phases

### Phase 1: Seed & Crawl

**Goal:** Generate association graph via BFS expansion

- Start with 100 niche concepts across 10 domains
- For each word, get 5 associations using prompt:
  ```
  "List 5 single-word associations for '[WORD]'.
   Provide only words, separated by commas."
  ```
- Expand to depth 3 (generates ~15k edges)
- Checkpoint every 500 words for resume capability

**Output:** Directed graph with ~10k nodes, ~15k edges

**Time:** 30-60 minutes on T4 GPU

### Phase 2: Logprob Scoring

**Goal:** Assign weights to edges using logprob extraction

- For each edge (A, B), prompt:
  ```
  "Word: A. Is 'B' a strong association? Yes or No"
  ```
- Extract logprob for "Yes" token
- Weight = e^(logprob) ∈ [0, 1]
- Checkpoint every 2000 edges

**Output:** Weighted directed graph

**Time:** 10-20 minutes on T4 GPU

### Phase 3: Topology Analysis

**Goal:** Extract semantic patterns from weighted graph

**Metrics:**

1. **Hubs (PageRank):** Central concepts in semantic network
   - Reveals "semantic attractors"
   - Example: physics, science, nature

2. **Convergence Analysis:** Path length from niche concepts to hubs
   - Measures "semantic gravity"
   - Low average = strong convergence (RLHF bias?)
   - High average = weak convergence (concepts stay niche)

3. **Island Detection:** Isolated concept clusters
   - Reveals model blind spots
   - Example: Molecular gastronomy terms disconnected from main graph

4. **Asymmetry Check:** Directional association bias
   - A→B strong, B→A weak reveals narrative bias
   - Example: "algorithm"→"bias" (0.8) vs "bias"→"algorithm" (0.1)

**Output:** JSON with all metrics

**Time:** ~5 minutes

## Key Findings

### 1. Semantic Attractors

Top hubs by PageRank reveal which concepts dominate the model's semantic space.

Example output:
```
1. science    (PageRank: 0.042)
2. nature     (PageRank: 0.038)
3. system     (PageRank: 0.031)
4. theory     (PageRank: 0.028)
5. energy     (PageRank: 0.025)
```

### 2. Semantic Gravity

Convergence analysis shows how quickly niche concepts converge to common ones.

Example output:
```
Domain                      Avg Hops to Hubs
quantum_physics             2.1 ± 0.8
medieval_history            2.5 ± 1.1
anime                       2.8 ± 1.2
molecular_gastronomy        3.4 ± 1.8
```

Low convergence = strong gravity (all paths lead to safe/common concepts)
High convergence = weak gravity (domain stays niche)

### 3. Islands (Model Blind Spots)

Disconnected clusters reveal domains where the model lacks connections.

Example:
```
Island 1 (size 8): spherification, emulsion, gelification, ...
Island 2 (size 5): rune, Fenrir, Mjolnir, ...
```

### 4. Asymmetric Associations (Narrative Bias)

Directional bias reveals how model training emphasized certain narratives.

Example:
```
algorithm → bias:     forward=0.82, backward=0.11, asymmetry=0.71
technology → risk:    forward=0.75, backward=0.15, asymmetry=0.60
```

This suggests model learned "algorithmic bias" and "technology risk" as strong associations, but not the reverse.

## Configuration

### Key Parameters

```python
CONFIG = {
    'model': 'google/gemma-3-4b-it',
    'max_hops': 3,                    # BFS depth
    'associations_per_word': 5,       # Associations per word
    'temperature_associations': 0.7,  # Temperature for Phase 1
    'temperature_scoring': 0.0,       # Temperature for Phase 2
    'batch_size': 32,                 # Concurrent requests
}
```

### Seed Domains

100 niche concepts across 10 domains:
- Quantum Physics
- Medieval History
- Anime
- Molecular Gastronomy
- Philosophy
- Immunology
- Music Theory
- Gothic Architecture
- Norse Mythology
- Organic Chemistry

## Performance

**Google Colab T4 GPU:**
- Phase 1 (Graph Building): 30-60 min (~15k inferences)
- Phase 2 (Logprob Scoring): 10-20 min (~10k scorings)
- Phase 3 (Topology Analysis): 5 min (graph algorithms)
- **Total:** 45-85 minutes

**Optimizations:**
- Async batching: -30% time
- Smart sampling: -40% time
- **Optimized:** 30-50 minutes

## Output Files

```
data/sgm/
├── checkpoints/
│   ├── phase1_iteration_500.pkl
│   ├── phase1_final.pkl
│   ├── phase2_final.pkl
│   └── ...
└── graphs/
    ├── semantic_graph_final.gpickle  # NetworkX graph
    ├── semantic_graph_final.csv      # Edge list (for Gephi)
    └── topology_metrics.json         # Analysis results
```

## Checkpointing & Resume

All phases support automatic checkpointing:

```python
# Phase 1: Save every 500 words (~15 min intervals)
# Phase 2: Save every 2000 edges (~10 min intervals)
# Phase 3: Save after completion

# Resume is automatic on next run
builder = GraphBuilder(engine, checkpoint_manager)
graph = builder.build_graph(max_hops=3, resume=True)
```

## Visualization

### Gephi

1. Download `semantic_graph_final.csv`
2. Import to Gephi as edge list
3. Apply ForceAtlas2 layout
4. Color by community detection
5. Size by PageRank

### Python (NetworkX + Matplotlib)

```python
import networkx as nx
import matplotlib.pyplot as plt

graph = checkpoint_manager.load_graph('semantic_graph_final')

# Draw subgraph
subgraph = graph.subgraph(list(graph.nodes())[:100])
pos = nx.spring_layout(subgraph, weight='weight')
nx.draw(subgraph, pos, with_labels=True, node_size=50)
plt.show()
```

## Extending the System

### Custom Seed Domains

```python
from align_test.sgm.models.seed_domains import DOMAINS

# Add custom domain
DOMAINS['custom_domain'] = [
    'word1', 'word2', 'word3', ...
]
```

### Custom Prompting

```python
class CustomInferenceEngine(SGMInferenceEngine):
    def get_associations(self, word: str, n: int = 5) -> List[str]:
        # Custom prompt
        prompt = f"What are {n} things related to {word}?"
        # ... rest of implementation
```

### Custom Metrics

```python
class CustomTopologyAnalyzer(TopologyAnalyzer):
    def custom_metric(self) -> Dict:
        # Add your own graph metrics
        pass
```

## Troubleshooting

### vLLM Server Not Starting

```bash
# Check logs
tail /tmp/vllm_server.log

# Restart server
killall python
python -m vllm.entrypoints.openai.api_server --model google/gemma-3-4b-it
```

### OOM (Out of Memory)

Reduce batch size or max_hops:
```python
CONFIG['batch_size'] = 16  # Reduce from 32
CONFIG['max_hops'] = 2     # Reduce from 3
```

### Logprob Extraction Fails

Some models don't return clean logprobs. Fallback:
```python
# In batch_inference.py, set fallback mode
scorer.fallback_mode = True  # Use Yes/No counting instead
```

## Citation

If you use this in research, please cite:

```bibtex
@software{semantic_gravity_mapping,
  title = {Semantic Gravity Mapping: Probing LLM Semantic Structure},
  author = {Your Name},
  year = {2025},
  url = {https://github.com/YOUR_USERNAME/align_prompts}
}
```

## License

[Your License Here]

## Acknowledgments

Based on the "Semantic Gravity Mapping" concept described in `Final_plan.md` and `brainstorming.md`.
