"""
Logprob Scorer for Semantic Gravity Mapping - Phase 2.

Assigns weights to graph edges using logprob extraction.
For each edge (A, B), asks the model:
  "Word: A. Is 'B' a strong association? Yes or No"

Extracts logprob for "Yes" token to measure association strength.
Weight = e^(logprob), where:
- High logprob (close to 0) = Strong association (weight ~ 1.0)
- Low logprob (very negative) = Weak association (weight ~ 0.0)
"""

import math
import networkx as nx
from typing import List, Tuple, Set, Dict, Optional

from align_test.sgm.inference.batch_inference import SGMInferenceEngine
from align_test.sgm.storage.checkpoint_manager import CheckpointManager


class LogprobScorer:
    """
    Scores edge strength via logprob extraction.

    Takes an unweighted directed graph from Phase 1 and adds
    'weight' attributes to edges based on logprob scoring.

    Attributes:
        engine: SGMInferenceEngine for scoring associations
        checkpoint_manager: CheckpointManager for saving progress
        checkpoint_interval: Save checkpoint every N edges
    """

    def __init__(
        self,
        engine: SGMInferenceEngine,
        checkpoint_manager: CheckpointManager,
        checkpoint_interval: int = 2000
    ):
        """
        Initialize logprob scorer.

        Args:
            engine: SGMInferenceEngine instance (with temperature=0.0 for deterministic scoring)
            checkpoint_manager: CheckpointManager instance
            checkpoint_interval: Save checkpoint every N edges (default: 2000)
        """
        self.engine = engine
        self.checkpoint_manager = checkpoint_manager
        self.checkpoint_interval = checkpoint_interval
        self._scored_count = 0

    def score_all_edges(
        self,
        graph: nx.DiGraph,
        resume: bool = True,
        show_progress: bool = True
    ) -> nx.DiGraph:
        """
        Score all edges in graph with logprob weights.

        Adds 'weight', 'logprob', and 'scored' attributes to each edge.
        Supports resume from checkpoint if interrupted.

        Args:
            graph: NetworkX directed graph from Phase 1
            resume: Whether to attempt resume from checkpoint (default: True)
            show_progress: Whether to show progress bar (default: True)

        Returns:
            Weighted directed graph (modifies graph in-place and returns it)

        Example:
            >>> scorer = LogprobScorer(engine, checkpoint_manager)
            >>> weighted_graph = scorer.score_all_edges(raw_graph)
            >>> # Check edge weights
            >>> for u, v, data in weighted_graph.edges(data=True):
            ...     print(f"{u} -> {v}: weight={data['weight']:.3f}")
        """
        # Try to resume from checkpoint
        if resume:
            resumed_graph = self._try_resume()
            if resumed_graph is not None:
                graph = resumed_graph
                print(f"Resumed from checkpoint: {self._scored_count} edges already scored")

        # Get unique edges to score
        unique_edges = self._deduplicate_edges(graph)
        total_edges = len(unique_edges)

        print(f"Scoring {total_edges} unique edges...")

        # Filter out already scored edges
        edges_to_score = [
            (u, v) for u, v in unique_edges
            if not graph.get_edge_data(u, v, {}).get('scored', False)
        ]

        if not edges_to_score:
            print("All edges already scored!")
            return graph

        print(f"{len(edges_to_score)} edges need scoring")

        # Score edges in batches
        edges_list = list(edges_to_score)

        if show_progress:
            try:
                from tqdm import tqdm
                edges_iter = tqdm(edges_list, desc="Scoring edges")
            except ImportError:
                edges_iter = edges_list
                print("Note: Install tqdm for progress bars (pip install tqdm)")
        else:
            edges_iter = edges_list

        for source, target in edges_iter:
            # Score edge
            logprob = self.engine.score_association(source, target, return_logprob=True)
            weight = math.exp(logprob)

            # Add attributes to all edges between these nodes
            # (there might be multiple edges from Phase 1 with different hops)
            for u, v, key in graph.edges(source, target, keys=True) if graph.is_multigraph() else [(source, target, None)]:
                graph[u][v]['weight'] = weight
                graph[u][v]['logprob'] = logprob
                graph[u][v]['scored'] = True

            self._scored_count += 1

            # Checkpoint if needed
            if self._scored_count % self.checkpoint_interval == 0:
                self._save_checkpoint(graph)
                if show_progress and hasattr(edges_iter, 'set_postfix'):
                    edges_iter.set_postfix({'checkpointed': self._scored_count})

        # Save final checkpoint
        self._save_checkpoint(graph, is_final=True)
        print(f"\nScoring complete! {self._scored_count} edges scored")

        return graph

    def _deduplicate_edges(self, graph: nx.DiGraph) -> Set[Tuple[str, str]]:
        """
        Extract unique (source, target) pairs from graph.

        Multiple edges between same nodes (from different hops)
        are deduplicated to a single pair.

        Args:
            graph: NetworkX directed graph

        Returns:
            Set of unique (source, target) tuples
        """
        return set(graph.edges())

    def _save_checkpoint(self, graph: nx.DiGraph, is_final: bool = False):
        """
        Save checkpoint with current scoring progress.

        Args:
            graph: Current graph with partial scoring
            is_final: Whether this is the final checkpoint
        """
        checkpoint_data = {
            'graph': graph,
            'scored_count': self._scored_count
        }

        if is_final:
            self.checkpoint_manager.save_checkpoint(
                phase=2,
                data=checkpoint_data,
                iteration=None
            )
        else:
            self.checkpoint_manager.save_checkpoint(
                phase=2,
                data=checkpoint_data,
                iteration=self._scored_count
            )

    def _try_resume(self) -> Optional[nx.DiGraph]:
        """
        Attempt to resume from latest checkpoint.

        Returns:
            Graph with partial scoring if found, None otherwise
        """
        try:
            checkpoint_data = self.checkpoint_manager.load_checkpoint(phase=2)

            if checkpoint_data is None:
                return None

            # Restore state
            graph = checkpoint_data['graph']
            self._scored_count = checkpoint_data.get('scored_count', 0)

            return graph

        except Exception as e:
            print(f"Warning: Failed to resume from checkpoint: {e}")
            return None

    def get_weight_statistics(self, graph: nx.DiGraph) -> Dict[str, float]:
        """
        Get statistics about edge weights.

        Args:
            graph: Weighted graph

        Returns:
            Dict with statistics:
            - mean_weight: Average edge weight
            - median_weight: Median edge weight
            - min_weight: Minimum weight
            - max_weight: Maximum weight
            - std_weight: Standard deviation
        """
        weights = [data.get('weight', 0.0) for _, _, data in graph.edges(data=True)]

        if not weights:
            return {
                'mean_weight': 0.0,
                'median_weight': 0.0,
                'min_weight': 0.0,
                'max_weight': 0.0,
                'std_weight': 0.0
            }

        # Calculate statistics
        weights_sorted = sorted(weights)
        n = len(weights)
        mean = sum(weights) / n
        median = weights_sorted[n // 2] if n % 2 == 1 else (weights_sorted[n // 2 - 1] + weights_sorted[n // 2]) / 2
        std = math.sqrt(sum((w - mean) ** 2 for w in weights) / n)

        return {
            'mean_weight': mean,
            'median_weight': median,
            'min_weight': min(weights),
            'max_weight': max(weights),
            'std_weight': std,
            'num_scored': len([w for w in weights if w > 0])
        }

    def get_top_edges(
        self,
        graph: nx.DiGraph,
        n: int = 10,
        sort_by: str = 'weight'
    ) -> List[Tuple[str, str, float]]:
        """
        Get top N edges by weight or logprob.

        Args:
            graph: Weighted graph
            n: Number of edges to return
            sort_by: 'weight' or 'logprob'

        Returns:
            List of (source, target, value) tuples sorted by value

        Example:
            >>> scorer = LogprobScorer(engine, checkpoint_manager)
            >>> top_edges = scorer.get_top_edges(graph, n=10)
            >>> for u, v, w in top_edges:
            ...     print(f"{u} -> {v}: {w:.3f}")
        """
        edges_with_values = []

        for u, v, data in graph.edges(data=True):
            value = data.get(sort_by, 0.0)
            edges_with_values.append((u, v, value))

        # Sort by value (descending)
        edges_with_values.sort(key=lambda x: x[2], reverse=True)

        return edges_with_values[:n]

    def get_bottom_edges(
        self,
        graph: nx.DiGraph,
        n: int = 10,
        sort_by: str = 'weight'
    ) -> List[Tuple[str, str, float]]:
        """
        Get bottom N edges by weight or logprob.

        Useful for finding weak/spurious associations.

        Args:
            graph: Weighted graph
            n: Number of edges to return
            sort_by: 'weight' or 'logprob'

        Returns:
            List of (source, target, value) tuples sorted by value (ascending)
        """
        edges_with_values = []

        for u, v, data in graph.edges(data=True):
            value = data.get(sort_by, 0.0)
            if value > 0:  # Only consider scored edges
                edges_with_values.append((u, v, value))

        # Sort by value (ascending)
        edges_with_values.sort(key=lambda x: x[2])

        return edges_with_values[:n]

    def visualize_weight_distribution(self, graph: nx.DiGraph):
        """
        Visualize distribution of edge weights using ASCII histogram.

        Args:
            graph: Weighted graph
        """
        weights = [data.get('weight', 0.0) for _, _, data in graph.edges(data=True) if data.get('weight', 0.0) > 0]

        if not weights:
            print("No weights to visualize")
            return

        print("\n=== Weight Distribution ===")

        # Create histogram buckets
        num_buckets = 20
        min_w = min(weights)
        max_w = max(weights)
        bucket_size = (max_w - min_w) / num_buckets

        buckets = [0] * num_buckets
        for w in weights:
            bucket_idx = min(int((w - min_w) / bucket_size), num_buckets - 1)
            buckets[bucket_idx] += 1

        # Print ASCII histogram
        max_count = max(buckets)
        scale = 50 / max_count if max_count > 0 else 1

        for i, count in enumerate(buckets):
            bucket_start = min_w + i * bucket_size
            bucket_end = bucket_start + bucket_size
            bar = '█' * int(count * scale)
            print(f"{bucket_start:.3f}-{bucket_end:.3f}: {bar} ({count})")

        print(f"\nTotal edges: {len(weights)}")
        stats = self.get_weight_statistics(graph)
        print(f"Mean: {stats['mean_weight']:.3f}, Median: {stats['median_weight']:.3f}")
        print(f"Min: {stats['min_weight']:.3f}, Max: {stats['max_weight']:.3f}")

    def __repr__(self) -> str:
        """String representation."""
        return f"LogprobScorer(scored={self._scored_count})"
