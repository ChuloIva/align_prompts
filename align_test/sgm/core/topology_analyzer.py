"""
Topology Analyzer for Semantic Gravity Mapping - Phase 3.

Analyzes the weighted graph to extract semantic patterns:
1. Hub Detection: Find central concepts (PageRank, degree centrality)
2. Convergence Analysis: Measure "semantic gravity" (path lengths to hubs)
3. Island Detection: Find isolated concept clusters
4. Asymmetry Detection: Find directional association biases

These metrics reveal:
- Which concepts are "attractors" in the model's semantic space
- How quickly niche concepts converge to common ones
- Which domains are isolated (model blind spots)
- Where the model has narrative biases (A->B strong, B->A weak)
"""

import json
import networkx as nx
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict

from align_test.sgm.models.seed_domains import get_all_seeds, DOMAINS


class TopologyAnalyzer:
    """
    Analyzes semantic graph topology to extract patterns.

    Computes various graph metrics to understand the structure
    of the model's semantic space.

    Attributes:
        graph: Weighted directed graph from Phase 2
    """

    def __init__(self, graph: nx.DiGraph):
        """
        Initialize topology analyzer.

        Args:
            graph: Weighted directed graph with 'weight' attributes on edges
        """
        self.graph = graph

    def analyze_all(self) -> Dict[str, Any]:
        """
        Run all analyses and return comprehensive report.

        Returns:
            Dict with all analysis results:
            {
                'hubs': [...],              # Top concepts by PageRank
                'convergence': {...},       # Domain-level convergence metrics
                'islands': [...],           # Isolated concept clusters
                'centrality': {...},        # Various centrality metrics
                'asymmetry': [...],         # Asymmetric association pairs
                'statistics': {...}         # Basic graph statistics
            }

        Example:
            >>> analyzer = TopologyAnalyzer(weighted_graph)
            >>> results = analyzer.analyze_all()
            >>> print(f"Top hub: {results['hubs'][0]}")
        """
        print("Running topology analysis...")

        results = {}

        # Basic statistics
        print("  Computing statistics...")
        results['statistics'] = self._get_statistics()

        # Hub detection
        print("  Finding hubs...")
        results['hubs'] = self.find_hubs(top_n=20)

        # Convergence analysis
        print("  Analyzing convergence...")
        results['convergence'] = self.convergence_analysis()

        # Island detection
        print("  Detecting islands...")
        results['islands'] = self.detect_islands(min_size=3)

        # Centrality metrics
        print("  Computing centrality...")
        results['centrality'] = self._compute_all_centrality()

        # Asymmetry check
        print("  Checking asymmetry...")
        results['asymmetry'] = self.asymmetry_check(top_n=20)

        print("Analysis complete!")
        return results

    def find_hubs(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """
        Find top concepts by PageRank.

        PageRank measures importance in the semantic network,
        where importance = how many other concepts point to it,
        weighted by the importance of those concepts.

        Args:
            top_n: Number of top hubs to return

        Returns:
            List of dicts with 'word', 'pagerank', and 'degree' keys,
            sorted by PageRank (descending)

        Example:
            >>> analyzer = TopologyAnalyzer(graph)
            >>> hubs = analyzer.find_hubs(top_n=10)
            >>> for hub in hubs:
            ...     print(f"{hub['word']}: PageRank={hub['pagerank']:.4f}")
        """
        # Compute PageRank with edge weights
        pagerank = nx.pagerank(self.graph, weight='weight')

        # Get in-degree (number of incoming edges)
        in_degree = dict(self.graph.in_degree())

        # Combine into list of dicts
        hubs = [
            {
                'word': word,
                'pagerank': score,
                'in_degree': in_degree.get(word, 0)
            }
            for word, score in pagerank.items()
        ]

        # Sort by PageRank
        hubs.sort(key=lambda x: x['pagerank'], reverse=True)

        return hubs[:top_n]

    def convergence_analysis(self) -> Dict[str, Any]:
        """
        Measure "semantic gravity" - how fast concepts converge to hubs.

        For each domain's seed words:
        1. Find top 5 hubs
        2. Compute shortest weighted path from each seed to each hub
        3. Calculate average path length

        Low average = strong gravity (fast convergence to common concepts)
        High average = weak gravity (concepts stay niche)

        Returns:
            Dict with domain-level and overall convergence metrics

        Example:
            >>> analyzer = TopologyAnalyzer(graph)
            >>> conv = analyzer.convergence_analysis()
            >>> print(f"Physics convergence: {conv['by_domain']['quantum_physics']['avg_hops']:.2f}")
        """
        # Get top 5 hubs
        hubs = self.find_hubs(top_n=5)
        hub_words = [h['word'] for h in hubs]

        # Get seeds by domain
        seeds_by_domain = {
            domain: [word.lower() for word in words]
            for domain, words in DOMAINS.items()
        }

        convergence_by_domain = {}

        for domain, seeds in seeds_by_domain.items():
            path_lengths = []

            for seed in seeds:
                if seed not in self.graph:
                    continue

                # Find shortest weighted path to each hub
                for hub in hub_words:
                    if hub not in self.graph:
                        continue

                    try:
                        # Use weight as edge cost (inverse of strength)
                        # Lower weight = weaker association = higher cost
                        path = nx.shortest_path(
                            self.graph,
                            source=seed,
                            target=hub,
                            weight=lambda u, v, d: 1.0 / (d.get('weight', 0.01) + 0.01)
                        )
                        path_lengths.append(len(path) - 1)  # Num hops

                    except nx.NetworkXNoPath:
                        # No path to this hub
                        continue

            # Calculate statistics
            if path_lengths:
                avg = sum(path_lengths) / len(path_lengths)
                min_hops = min(path_lengths)
                max_hops = max(path_lengths)
                std = (sum((x - avg) ** 2 for x in path_lengths) / len(path_lengths)) ** 0.5

                convergence_by_domain[domain] = {
                    'avg_hops': avg,
                    'min_hops': min_hops,
                    'max_hops': max_hops,
                    'std_hops': std,
                    'num_paths': len(path_lengths)
                }
            else:
                # No paths found (domain is isolated)
                convergence_by_domain[domain] = {
                    'avg_hops': float('inf'),
                    'min_hops': float('inf'),
                    'max_hops': float('inf'),
                    'std_hops': 0.0,
                    'num_paths': 0
                }

        # Overall convergence (average across domains)
        valid_avgs = [
            d['avg_hops'] for d in convergence_by_domain.values()
            if d['avg_hops'] != float('inf')
        ]

        overall_avg = sum(valid_avgs) / len(valid_avgs) if valid_avgs else float('inf')

        return {
            'by_domain': convergence_by_domain,
            'overall_avg_hops': overall_avg,
            'hub_words': hub_words
        }

    def detect_islands(self, min_size: int = 3) -> List[Dict[str, Any]]:
        """
        Find isolated concept clusters (weakly connected components).

        Islands represent domains or topics that are disconnected
        from the main semantic network - potential model blind spots.

        Args:
            min_size: Minimum cluster size to report (default: 3)

        Returns:
            List of dicts with 'words' (list) and 'size' (int) keys,
            sorted by size (descending)

        Example:
            >>> analyzer = TopologyAnalyzer(graph)
            >>> islands = analyzer.detect_islands(min_size=3)
            >>> for island in islands:
            ...     print(f"Island of {island['size']}: {island['words'][:5]}")
        """
        # Find weakly connected components
        components = list(nx.weakly_connected_components(self.graph))

        # Filter by minimum size
        islands = [
            {
                'words': sorted(list(comp)),
                'size': len(comp)
            }
            for comp in components
            if len(comp) >= min_size
        ]

        # Sort by size (descending)
        islands.sort(key=lambda x: x['size'], reverse=True)

        return islands

    def asymmetry_check(
        self,
        threshold: float = 0.3,
        top_n: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find pairs with strong directional bias.

        Asymmetry reveals narrative biases where the model associates
        A with B strongly, but not B with A.

        Example: "Algorithm" -> "Bias" (strong)
                 "Bias" -> "Algorithm" (weak)
        This suggests model training emphasized "algorithmic bias" narratives.

        Args:
            threshold: Minimum weight difference to consider asymmetric
            top_n: Number of top asymmetric pairs to return

        Returns:
            List of dicts with asymmetry information:
            {
                'source': str,
                'target': str,
                'forward_weight': float,  # A -> B
                'backward_weight': float,  # B -> A
                'asymmetry': float        # abs(forward - backward)
            }

        Example:
            >>> analyzer = TopologyAnalyzer(graph)
            >>> asymm = analyzer.asymmetry_check(threshold=0.3, top_n=10)
            >>> for pair in asymm:
            ...     print(f"{pair['source']} -> {pair['target']}: "
            ...           f"forward={pair['forward_weight']:.3f}, "
            ...           f"backward={pair['backward_weight']:.3f}")
        """
        asymmetric_pairs = []

        # Check all edges
        for u, v, data in self.graph.edges(data=True):
            forward_weight = data.get('weight', 0.0)

            # Check if reverse edge exists
            if self.graph.has_edge(v, u):
                backward_weight = self.graph[v][u].get('weight', 0.0)
            else:
                backward_weight = 0.0

            # Calculate asymmetry
            asymmetry = abs(forward_weight - backward_weight)

            if asymmetry >= threshold:
                asymmetric_pairs.append({
                    'source': u,
                    'target': v,
                    'forward_weight': forward_weight,
                    'backward_weight': backward_weight,
                    'asymmetry': asymmetry
                })

        # Sort by asymmetry (descending)
        asymmetric_pairs.sort(key=lambda x: x['asymmetry'], reverse=True)

        return asymmetric_pairs[:top_n]

    def _compute_all_centrality(self) -> Dict[str, Dict[str, float]]:
        """
        Compute various centrality metrics.

        Returns:
            Dict with top nodes for each centrality measure:
            {
                'pagerank': {...},
                'betweenness': {...},
                'in_degree': {...},
                'out_degree': {...}
            }
        """
        # PageRank (already computed in find_hubs)
        pagerank = nx.pagerank(self.graph, weight='weight')

        # Betweenness centrality (nodes that bridge different clusters)
        betweenness = nx.betweenness_centrality(self.graph, weight='weight')

        # Degree centrality
        in_degree = dict(self.graph.in_degree())
        out_degree = dict(self.graph.out_degree())

        # Get top 10 for each metric
        def top_k(metric_dict, k=10):
            sorted_items = sorted(metric_dict.items(), key=lambda x: x[1], reverse=True)
            return {word: score for word, score in sorted_items[:k]}

        return {
            'pagerank': top_k(pagerank),
            'betweenness': top_k(betweenness),
            'in_degree': top_k(in_degree),
            'out_degree': top_k(out_degree)
        }

    def _get_statistics(self) -> Dict[str, Any]:
        """
        Get basic graph statistics.

        Returns:
            Dict with statistics:
            - num_nodes, num_edges
            - avg_degree, max_degree
            - density
            - num_components
        """
        num_nodes = self.graph.number_of_nodes()
        num_edges = self.graph.number_of_edges()

        degrees = [d for _, d in self.graph.degree()]
        avg_degree = sum(degrees) / len(degrees) if degrees else 0
        max_degree = max(degrees) if degrees else 0

        density = nx.density(self.graph)
        num_components = nx.number_weakly_connected_components(self.graph)

        return {
            'num_nodes': num_nodes,
            'num_edges': num_edges,
            'avg_degree': avg_degree,
            'max_degree': max_degree,
            'density': density,
            'num_weakly_connected_components': num_components
        }

    def print_summary(self, results: Dict[str, Any]):
        """
        Print human-readable summary of analysis results.

        Args:
            results: Results dict from analyze_all()
        """
        print("\n" + "=" * 60)
        print("SEMANTIC GRAVITY MAPPING - ANALYSIS SUMMARY")
        print("=" * 60)

        # Statistics
        stats = results['statistics']
        print(f"\n📊 Graph Statistics:")
        print(f"   Nodes: {stats['num_nodes']:,}")
        print(f"   Edges: {stats['num_edges']:,}")
        print(f"   Avg Degree: {stats['avg_degree']:.2f}")
        print(f"   Density: {stats['density']:.4f}")
        print(f"   Components: {stats['num_weakly_connected_components']}")

        # Top hubs
        print(f"\n🎯 Top 10 Semantic Hubs (by PageRank):")
        for i, hub in enumerate(results['hubs'][:10], 1):
            print(f"   {i:2d}. {hub['word']:20s} (PR: {hub['pagerank']:.4f}, InDeg: {hub['in_degree']})")

        # Convergence
        print(f"\n🌀 Convergence Analysis (Semantic Gravity):")
        conv = results['convergence']
        print(f"   Overall Avg Hops to Hubs: {conv['overall_avg_hops']:.2f}")
        print(f"   Top Hubs: {', '.join(conv['hub_words'])}")
        print(f"\n   By Domain:")

        # Sort domains by convergence (fastest first)
        domain_conv = sorted(
            conv['by_domain'].items(),
            key=lambda x: x[1]['avg_hops']
        )

        for domain, metrics in domain_conv[:5]:
            if metrics['avg_hops'] != float('inf'):
                print(f"      {domain:25s}: {metrics['avg_hops']:.2f} hops (±{metrics['std_hops']:.2f})")

        # Islands
        islands = results['islands']
        if islands:
            print(f"\n🏝️  Isolated Clusters (Islands):")
            print(f"   Found {len(islands)} islands")
            for i, island in enumerate(islands[:3], 1):
                words_preview = ', '.join(island['words'][:5])
                if island['size'] > 5:
                    words_preview += ', ...'
                print(f"   {i}. Size {island['size']}: {words_preview}")
        else:
            print(f"\n🏝️  No isolated clusters found (all concepts connected)")

        # Asymmetry
        print(f"\n⚖️  Top 5 Asymmetric Associations:")
        for i, pair in enumerate(results['asymmetry'][:5], 1):
            print(f"   {i}. {pair['source']} -> {pair['target']}")
            print(f"      Forward: {pair['forward_weight']:.3f}, Backward: {pair['backward_weight']:.3f}")
            print(f"      Asymmetry: {pair['asymmetry']:.3f}")

        print("\n" + "=" * 60)

    def export_results(self, results: Dict[str, Any], filepath: str):
        """
        Export analysis results to JSON file.

        Args:
            results: Results dict from analyze_all()
            filepath: Path to save JSON file
        """
        # Convert sets to lists for JSON serialization
        serializable_results = self._make_serializable(results)

        with open(filepath, 'w') as f:
            json.dump(serializable_results, f, indent=2)

        print(f"Results exported to {filepath}")

    def _make_serializable(self, obj: Any) -> Any:
        """
        Recursively convert sets and other non-serializable objects to JSON-compatible types.
        """
        if isinstance(obj, set):
            return sorted(list(obj))
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, float):
            if obj == float('inf'):
                return "inf"
            elif obj == float('-inf'):
                return "-inf"
            else:
                return obj
        else:
            return obj

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"TopologyAnalyzer("
            f"nodes={self.graph.number_of_nodes()}, "
            f"edges={self.graph.number_of_edges()})"
        )
