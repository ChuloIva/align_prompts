"""
Semantic Gravity Mapping (SGM) Module.

This module implements a system to map LLM semantic structure by generating
word association graphs and analyzing their topological properties.

Main Components:
- GraphBuilder: Phase 1 - BFS expansion from seed concepts
- LogprobScorer: Phase 2 - Edge weight assignment via logprobs
- TopologyAnalyzer: Phase 3 - Graph analysis (hubs, convergence, islands, asymmetry)

Example usage:
    >>> from align_test.core.vllm_client import VLLMClient
    >>> from align_test.sgm import SGMInferenceEngine, GraphBuilder, CheckpointManager
    >>>
    >>> # Initialize components
    >>> client = VLLMClient(model='google/gemma-3-4b-it')
    >>> engine = SGMInferenceEngine(client)
    >>> checkpoint_manager = CheckpointManager('./checkpoints')
    >>>
    >>> # Build graph
    >>> builder = GraphBuilder(engine, checkpoint_manager)
    >>> graph = builder.build_graph(max_hops=3)
"""

# Core components
from align_test.sgm.core.graph_builder import GraphBuilder
from align_test.sgm.core.logprob_scorer import LogprobScorer
from align_test.sgm.core.topology_analyzer import TopologyAnalyzer

# Inference
from align_test.sgm.inference.batch_inference import SGMInferenceEngine

# Storage
from align_test.sgm.storage.checkpoint_manager import CheckpointManager

# Models
from align_test.sgm.models.seed_domains import (
    get_all_seeds,
    get_seeds_by_domain,
    get_domain_names,
    get_seeds_with_metadata,
    DOMAINS
)

__all__ = [
    # Core
    'GraphBuilder',
    'LogprobScorer',
    'TopologyAnalyzer',

    # Inference
    'SGMInferenceEngine',

    # Storage
    'CheckpointManager',

    # Models
    'get_all_seeds',
    'get_seeds_by_domain',
    'get_domain_names',
    'get_seeds_with_metadata',
    'DOMAINS',
]

__version__ = '0.1.0'
