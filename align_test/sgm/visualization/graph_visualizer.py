"""
Interactive Graph Visualizer for Semantic Gravity Mapping.

Creates interactive HTML network visualizations using Pyvis with:
- Force-directed physics layouts
- Node sizing and coloring by centrality metrics
- Edge thickness by association weight
- Interactive controls (zoom, pan, drag)
"""

from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import networkx as nx
from pyvis.network import Network

from align_test.sgm.models.seed_domains import DOMAINS


class InteractiveGraphVisualizer:
    """
    Creates interactive HTML network visualizations with Pyvis.

    Attributes:
        graph: NetworkX directed graph with weights
        results: Analysis results from TopologyAnalyzer
        output_dir: Directory for saving HTML files
    """

    def __init__(
        self,
        graph: nx.DiGraph,
        analysis_results: Dict[str, Any],
        output_dir: str | Path = './data/sgm/visualizations'
    ):
        """
        Initialize visualizer.

        Args:
            graph: Weighted directed graph
            analysis_results: Results from TopologyAnalyzer.analyze_all()
            output_dir: Output directory for HTML files
        """
        self.graph = graph
        self.results = analysis_results
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_full_network(
        self,
        filter_top_n: int = 500,
        color_by: str = 'pagerank',
        size_by: str = 'pagerank',
        layout: str = 'barnes_hut',
        height: str = '800px',
        width: str = '100%'
    ) -> str:
        """
        Create interactive network of top N nodes by PageRank.

        Args:
            filter_top_n: Number of nodes to include (for performance)
            color_by: Node coloring ('pagerank', 'degree', 'betweenness')
            size_by: Node sizing ('pagerank', 'degree', 'betweenness')
            layout: Physics layout ('barnes_hut', 'force_atlas_2based', 'hierarchical')
            height: Canvas height
            width: Canvas width

        Returns:
            Path to generated HTML file
        """
        # Get top N nodes by PageRank
        pagerank = nx.pagerank(self.graph, weight='weight')
        top_nodes = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:filter_top_n]
        top_node_set = set(node for node, _ in top_nodes)

        # Create subgraph
        subgraph = self.graph.subgraph(top_node_set).copy()

        # Initialize Pyvis network
        net = Network(
            height=height,
            width=width,
            directed=True,
            notebook=False,
            bgcolor='#222222',
            font_color='white'
        )

        # Configure physics
        if layout == 'barnes_hut':
            net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=200)
        elif layout == 'force_atlas_2based':
            net.force_atlas_2based()
        elif layout == 'hierarchical':
            net.hierarchical()

        # Get metrics for coloring/sizing
        metrics = self._get_node_metrics(subgraph, color_by, size_by)

        # Add nodes
        for node in subgraph.nodes():
            color_val = metrics['color'].get(node, 0)
            size_val = metrics['size'].get(node, 0)

            # Normalize and scale
            color_hex = self._value_to_color(color_val, metrics['color_range'])
            size_px = self._value_to_size(size_val, metrics['size_range'])

            # Create title (hover info)
            title = f"{node}\n"
            title += f"PageRank: {pagerank.get(node, 0):.4f}\n"
            title += f"In-Degree: {subgraph.in_degree(node)}\n"
            title += f"Out-Degree: {subgraph.out_degree(node)}"

            net.add_node(
                node,
                label=node,
                title=title,
                color=color_hex,
                size=size_px
            )

        # Add edges
        for u, v, data in subgraph.edges(data=True):
            weight = data.get('weight', 0.1)
            # Edge width proportional to weight
            width_px = max(0.5, weight * 3)

            net.add_edge(u, v, value=width_px, title=f"Weight: {weight:.3f}")

        # Configure options
        net.set_options("""
        {
          "nodes": {
            "font": {"size": 14}
          },
          "edges": {
            "color": {"inherit": false},
            "smooth": {"type": "continuous"}
          },
          "physics": {
            "minVelocity": 0.75
          }
        }
        """)

        # Save
        output_path = self.output_dir / f'full_network_top{filter_top_n}.html'
        net.save_graph(str(output_path))

        print(f"✓ Full network visualization saved: {output_path}")
        return str(output_path)

    def create_hub_network(
        self,
        hub_count: int = 20,
        include_neighbors: bool = True,
        height: str = '700px'
    ) -> str:
        """
        Visualize top hubs and their immediate connections.

        Args:
            hub_count: Number of hubs to include
            include_neighbors: Whether to include 1-hop neighbors
            height: Canvas height

        Returns:
            Path to generated HTML file
        """
        # Get top hubs
        hubs_data = self.results.get('hubs', [])[:hub_count]
        hub_nodes = set(h['word'] for h in hubs_data)

        # Optionally include neighbors
        if include_neighbors:
            nodes_to_include = set(hub_nodes)
            for hub in hub_nodes:
                if hub in self.graph:
                    nodes_to_include.update(self.graph.successors(hub))
                    nodes_to_include.update(self.graph.predecessors(hub))
        else:
            nodes_to_include = hub_nodes

        # Create subgraph
        subgraph = self.graph.subgraph(nodes_to_include).copy()

        # Initialize network
        net = Network(height=height, width='100%', directed=True, notebook=False)
        net.barnes_hut()

        # Add nodes
        pagerank = nx.pagerank(subgraph, weight='weight')

        for node in subgraph.nodes():
            is_hub = node in hub_nodes
            color = '#ff4444' if is_hub else '#4444ff'  # Red for hubs, blue for neighbors
            size = 30 if is_hub else 15

            title = f"{node}\nPageRank: {pagerank.get(node, 0):.4f}"
            if is_hub:
                title += "\n⭐ HUB"

            net.add_node(node, label=node, title=title, color=color, size=size)

        # Add edges
        for u, v, data in subgraph.edges(data=True):
            weight = data.get('weight', 0.1)
            width = max(1, weight * 5)
            net.add_edge(u, v, value=width, title=f"Weight: {weight:.3f}")

        # Save
        output_path = self.output_dir / 'hub_network.html'
        net.save_graph(str(output_path))

        print(f"✓ Hub network visualization saved: {output_path}")
        return str(output_path)

    def create_domain_subgraph(
        self,
        domain: str,
        expansion_hops: int = 2,
        height: str = '700px'
    ) -> str:
        """
        Visualize seed words from one domain and their expansion.

        Args:
            domain: Domain name (e.g., 'quantum_physics')
            expansion_hops: How many hops to expand from seeds
            height: Canvas height

        Returns:
            Path to generated HTML file
        """
        if domain not in DOMAINS:
            raise ValueError(f"Unknown domain: {domain}")

        # Get seed words for domain
        seeds = [word.lower() for word in DOMAINS[domain]]
        seeds_in_graph = [s for s in seeds if s in self.graph]

        if not seeds_in_graph:
            print(f"Warning: No seeds from domain '{domain}' found in graph")
            return ""

        # BFS expansion from seeds
        nodes_to_include = set(seeds_in_graph)

        for hop in range(expansion_hops):
            frontier = set(nodes_to_include)
            for node in frontier:
                if node in self.graph:
                    nodes_to_include.update(self.graph.successors(node))

        # Create subgraph
        subgraph = self.graph.subgraph(nodes_to_include).copy()

        # Initialize network
        net = Network(height=height, width='100%', directed=True, notebook=False)
        net.barnes_hut()

        # Add nodes
        for node in subgraph.nodes():
            is_seed = node in seeds_in_graph
            color = '#00ff00' if is_seed else '#888888'  # Green for seeds, gray for expanded
            size = 25 if is_seed else 12

            title = f"{node}"
            if is_seed:
                title += f"\n🌱 Seed ({domain})"

            net.add_node(node, label=node, title=title, color=color, size=size)

        # Add edges
        for u, v, data in subgraph.edges(data=True):
            weight = data.get('weight', 0.1)
            width = max(0.5, weight * 3)
            net.add_edge(u, v, value=width)

        # Save
        output_path = self.output_dir / f'domain_{domain}.html'
        net.save_graph(str(output_path))

        print(f"✓ Domain subgraph visualization saved: {output_path}")
        return str(output_path)

    def _get_node_metrics(
        self,
        graph: nx.DiGraph,
        color_by: str,
        size_by: str
    ) -> Dict[str, Any]:
        """
        Compute metrics for node coloring and sizing.

        Returns:
            Dict with 'color', 'size', 'color_range', 'size_range' keys
        """
        metrics = {}

        # Compute color metric
        if color_by == 'pagerank':
            metrics['color'] = nx.pagerank(graph, weight='weight')
        elif color_by == 'degree':
            metrics['color'] = dict(graph.degree())
        elif color_by == 'betweenness':
            metrics['color'] = nx.betweenness_centrality(graph)
        else:
            metrics['color'] = {node: 1.0 for node in graph.nodes()}

        # Compute size metric
        if size_by == 'pagerank':
            metrics['size'] = nx.pagerank(graph, weight='weight')
        elif size_by == 'degree':
            metrics['size'] = dict(graph.degree())
        elif size_by == 'betweenness':
            metrics['size'] = nx.betweenness_centrality(graph)
        else:
            metrics['size'] = {node: 1.0 for node in graph.nodes()}

        # Compute ranges
        color_values = list(metrics['color'].values())
        size_values = list(metrics['size'].values())

        metrics['color_range'] = (min(color_values) if color_values else 0,
                                   max(color_values) if color_values else 1)
        metrics['size_range'] = (min(size_values) if size_values else 0,
                                  max(size_values) if size_values else 1)

        return metrics

    def _value_to_color(self, value: float, value_range: tuple) -> str:
        """
        Map value to color hex code (blue to red gradient).

        Args:
            value: Value to map
            value_range: (min, max) tuple

        Returns:
            Hex color code
        """
        min_val, max_val = value_range

        if max_val == min_val:
            norm = 0.5
        else:
            norm = (value - min_val) / (max_val - min_val)

        # Gradient: blue (low) -> green (mid) -> red (high)
        if norm < 0.5:
            # Blue to green
            r = 0
            g = int(255 * (norm * 2))
            b = int(255 * (1 - norm * 2))
        else:
            # Green to red
            r = int(255 * ((norm - 0.5) * 2))
            g = int(255 * (1 - (norm - 0.5) * 2))
            b = 0

        return f'#{r:02x}{g:02x}{b:02x}'

    def _value_to_size(self, value: float, value_range: tuple) -> int:
        """
        Map value to node size (10-50px).

        Args:
            value: Value to map
            value_range: (min, max) tuple

        Returns:
            Node size in pixels
        """
        min_val, max_val = value_range

        if max_val == min_val:
            return 20  # Default size

        norm = (value - min_val) / (max_val - min_val)
        return int(10 + norm * 40)  # Range: 10-50px

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"InteractiveGraphVisualizer("
            f"nodes={self.graph.number_of_nodes()}, "
            f"edges={self.graph.number_of_edges()})"
        )
