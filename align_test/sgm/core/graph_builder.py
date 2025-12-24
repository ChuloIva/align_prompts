"""
Graph Builder for Semantic Gravity Mapping - Phase 1.

Implements BFS (Breadth-First Search) expansion to generate
the word association graph from seed concepts.

Algorithm:
1. Start with 100 seed words from diverse domains
2. For each word at depth d (0 to max_hops):
   - Get 5 word associations
   - Add edges to graph
   - Mark word as visited
   - Add new words to frontier for next depth
3. Checkpoint progress every N words for resume capability
"""

import networkx as nx
from typing import List, Tuple, Set, Dict, Optional
from collections import deque

from align_test.sgm.inference.batch_inference import SGMInferenceEngine
from align_test.sgm.storage.checkpoint_manager import CheckpointManager
from align_test.sgm.models.seed_domains import get_all_seeds


class GraphBuilder:
    """
    Builds word association graph via BFS expansion.

    Performs breadth-first expansion from seed concepts to generate
    a directed graph where edges represent associations discovered
    through LLM generation.

    Attributes:
        engine: SGMInferenceEngine for getting word associations
        checkpoint_manager: CheckpointManager for saving progress
        graph: NetworkX directed graph
        visited: Set of visited words (prevents re-expansion)
        checkpoint_interval: Save checkpoint every N words
    """

    def __init__(
        self,
        engine: SGMInferenceEngine,
        checkpoint_manager: CheckpointManager,
        checkpoint_interval: int = 500
    ):
        """
        Initialize graph builder.

        Args:
            engine: SGMInferenceEngine instance
            checkpoint_manager: CheckpointManager instance
            checkpoint_interval: Save checkpoint every N words (default: 500)
        """
        self.engine = engine
        self.checkpoint_manager = checkpoint_manager
        self.graph = nx.DiGraph()
        self.visited: Set[str] = set()
        self.checkpoint_interval = checkpoint_interval
        self._iteration_count = 0

    def build_graph(
        self,
        max_hops: int = 3,
        associations_per_word: int = 5,
        resume: bool = True
    ) -> nx.DiGraph:
        """
        Build word association graph through BFS expansion.

        Expands from seed concepts to depth=max_hops, getting
        N associations per word. Automatically checkpoints and
        supports resume from interruptions.

        Args:
            max_hops: Maximum depth to expand (default: 3)
                     0 = just seeds
                     1 = seeds + 1st hop (500 words)
                     2 = +2nd hop (~2.5k words)
                     3 = +3rd hop (~12.5k words)
            associations_per_word: Associations to request per word (default: 5)
            resume: Whether to attempt resume from checkpoint (default: True)

        Returns:
            NetworkX directed graph with edges representing associations

        Example:
            >>> builder = GraphBuilder(engine, checkpoint_manager)
            >>> graph = builder.build_graph(max_hops=3)
            >>> print(f"Nodes: {graph.number_of_nodes()}")
            >>> print(f"Edges: {graph.number_of_edges()}")
        """
        # Try to resume from checkpoint if requested
        if resume:
            resumed = self._try_resume()
            if resumed:
                print(f"Resumed from checkpoint: {len(self.visited)} words processed")

        # Get seed words
        seeds = get_all_seeds()

        # Initialize frontier with seeds (if not resuming)
        if len(self.visited) == 0:
            frontier = set(seeds)
            current_hop = 0
        else:
            # If resuming, determine current frontier and hop
            frontier, current_hop = self._determine_frontier(max_hops)

        print(f"Starting BFS expansion from {len(seeds)} seeds to depth {max_hops}")
        print(f"Current hop: {current_hop}, Frontier size: {len(frontier)}")

        # BFS expansion
        for hop in range(current_hop, max_hops + 1):
            if not frontier:
                print(f"Frontier empty at hop {hop}, stopping")
                break

            print(f"\n=== Hop {hop}/{max_hops} ===")
            print(f"Expanding {len(frontier)} words...")

            # Process current frontier
            next_frontier = set()

            for word in frontier:
                # Skip if already visited
                if word in self.visited:
                    continue

                # Get associations
                edges = self._expand_word(word, hop, associations_per_word)

                # Add to graph
                for source, target, hop_num in edges:
                    self.graph.add_edge(source, target, hop=hop_num)
                    next_frontier.add(target)

                # Mark as visited
                self.visited.add(word)
                self._iteration_count += 1

                # Checkpoint if needed
                if self._iteration_count % self.checkpoint_interval == 0:
                    self._save_checkpoint(hop)
                    print(f"  Checkpoint saved ({self._iteration_count} words processed)")

            print(f"Hop {hop} complete: {len(next_frontier)} new words discovered")
            print(f"Graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")

            # Update frontier for next hop
            frontier = next_frontier

        # Save final checkpoint
        self._save_checkpoint(max_hops, is_final=True)
        print(f"\nBFS expansion complete!")
        print(f"Final graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")

        return self.graph

    def _expand_word(
        self,
        word: str,
        hop: int,
        n: int = 5
    ) -> List[Tuple[str, str, int]]:
        """
        Expand a single word by getting its associations.

        Args:
            word: Word to expand
            hop: Current hop depth
            n: Number of associations to request

        Returns:
            List of edges as (source, target, hop) tuples
        """
        associations = self.engine.get_associations(word, n=n)

        edges = []
        for assoc in associations:
            if assoc and assoc != word:  # Skip empty and self-loops
                edges.append((word, assoc, hop))

        return edges

    def _save_checkpoint(self, current_hop: int, is_final: bool = False):
        """
        Save checkpoint with current graph state.

        Args:
            current_hop: Current hop depth
            is_final: Whether this is the final checkpoint
        """
        checkpoint_data = {
            'graph': self.graph,
            'visited': self.visited,
            'iteration_count': self._iteration_count,
            'current_hop': current_hop
        }

        if is_final:
            self.checkpoint_manager.save_checkpoint(
                phase=1,
                data=checkpoint_data,
                iteration=None  # Final checkpoint
            )
        else:
            self.checkpoint_manager.save_checkpoint(
                phase=1,
                data=checkpoint_data,
                iteration=self._iteration_count
            )

    def _try_resume(self) -> bool:
        """
        Attempt to resume from latest checkpoint.

        Returns:
            True if resumed successfully, False otherwise
        """
        try:
            checkpoint_data = self.checkpoint_manager.load_checkpoint(phase=1)

            if checkpoint_data is None:
                return False

            # Restore state
            self.graph = checkpoint_data['graph']
            self.visited = checkpoint_data['visited']
            self._iteration_count = checkpoint_data.get('iteration_count', 0)

            return True

        except Exception as e:
            print(f"Warning: Failed to resume from checkpoint: {e}")
            return False

    def _determine_frontier(self, max_hops: int) -> Tuple[Set[str], int]:
        """
        Determine current frontier and hop when resuming.

        Looks at graph edges to find:
        - Which hop we're currently on
        - Which words are in the frontier (discovered but not expanded)

        Args:
            max_hops: Maximum hops for the run

        Returns:
            Tuple of (frontier_set, current_hop)
        """
        # Find maximum hop in graph
        max_hop_in_graph = 0
        for _, _, data in self.graph.edges(data=True):
            hop = data.get('hop', 0)
            if hop > max_hop_in_graph:
                max_hop_in_graph = hop

        # Frontier = all target nodes not yet visited
        all_targets = set(target for _, target in self.graph.edges())
        frontier = all_targets - self.visited

        # If frontier empty, we're done with current hop, move to next
        if not frontier:
            current_hop = min(max_hop_in_graph + 1, max_hops)
        else:
            current_hop = max_hop_in_graph

        return frontier, current_hop

    def preview_sample_paths(self, n: int = 5):
        """
        Display sample paths from seeds through the graph.

        Shows N random paths from seed words to their associations
        to give a sense of the graph structure.

        Args:
            n: Number of sample paths to show

        Example output:
            entanglement -> quantum -> physics -> science
            tsundere -> anime -> Japan -> culture
        """
        seeds = get_all_seeds()

        print(f"\n=== Sample Association Paths ===")

        for i, seed in enumerate(seeds[:n]):
            if seed not in self.graph:
                continue

            # Get a path through the graph from this seed
            path = [seed]
            current = seed

            # Follow outgoing edges for up to 4 hops
            for _ in range(4):
                neighbors = list(self.graph.successors(current))
                if not neighbors:
                    break
                # Pick first neighbor (arbitrary but deterministic)
                current = neighbors[0]
                path.append(current)

            print(f"{i+1}. {' -> '.join(path)}")

    def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics about the current graph.

        Returns:
            Dict with statistics:
            - num_nodes: Number of unique words
            - num_edges: Number of associations
            - num_visited: Number of words expanded
            - avg_out_degree: Average associations per word
            - max_out_degree: Max associations for any word
        """
        out_degrees = [self.graph.out_degree(n) for n in self.graph.nodes()]

        return {
            'num_nodes': self.graph.number_of_nodes(),
            'num_edges': self.graph.number_of_edges(),
            'num_visited': len(self.visited),
            'avg_out_degree': sum(out_degrees) / len(out_degrees) if out_degrees else 0,
            'max_out_degree': max(out_degrees) if out_degrees else 0
        }

    def export_to_graphml(self, filepath: str):
        """
        Export graph to GraphML format for visualization in Gephi.

        Args:
            filepath: Path to save GraphML file
        """
        nx.write_graphml(self.graph, filepath)
        print(f"Graph exported to {filepath}")

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"GraphBuilder("
            f"nodes={self.graph.number_of_nodes()}, "
            f"edges={self.graph.number_of_edges()}, "
            f"visited={len(self.visited)})"
        )
