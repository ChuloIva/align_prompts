"""
Manifold Projector for Semantic Gravity Mapping.

Projects semantic graph to 2D/3D using UMAP for visualization.
Creates interactive Plotly scatter plots with hover information.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import networkx as nx
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import umap

from align_test.sgm.models.seed_domains import DOMAINS, get_seeds_with_metadata


class ManifoldProjector:
    """
    Projects semantic graph to 2D/3D using UMAP.

    Uses shortest-path distances in the weighted graph as
    the distance metric for UMAP, revealing the true semantic
    manifold structure.

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
        Initialize manifold projector.

        Args:
            graph: Weighted directed graph
            analysis_results: Results from TopologyAnalyzer.analyze_all()
            output_dir: Output directory for HTML files
        """
        self.graph = graph
        self.results = analysis_results
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Cache for computed distances
        self._distance_matrix = None
        self._node_list = None

    def compute_graph_distances(
        self,
        max_nodes: Optional[int] = None,
        use_weight_inverse: bool = True
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Compute all-pairs shortest path distances.

        Args:
            max_nodes: Limit to top N nodes by PageRank (for performance)
            use_weight_inverse: Use 1/weight as edge cost (True recommended)

        Returns:
            - Distance matrix (NxN)
            - Node list (ordered)
        """
        if self._distance_matrix is not None:
            return self._distance_matrix, self._node_list

        # Filter to top nodes if requested
        if max_nodes is not None:
            pagerank = nx.pagerank(self.graph, weight='weight')
            top_nodes = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
            node_list = [node for node, _ in top_nodes]
            subgraph = self.graph.subgraph(node_list).copy()
        else:
            subgraph = self.graph
            node_list = list(subgraph.nodes())

        n = len(node_list)
        node_to_idx = {node: idx for idx, node in enumerate(node_list)}

        # Compute shortest paths with weight as cost
        print(f"Computing all-pairs shortest paths for {n} nodes...")

        distance_matrix = np.full((n, n), np.inf)
        np.fill_diagonal(distance_matrix, 0)

        # Use Floyd-Warshall for dense graphs or Dijkstra for sparse
        if n < 1000:  # Use Floyd-Warshall for small graphs
            # Get weight function
            if use_weight_inverse:
                def weight_fn(u, v, d): return 1.0 / (d.get('weight', 0.01) + 0.01)
            else:
                def weight_fn(u, v, d): return d.get('weight', 0.1)

            # Compute all pairs shortest paths
            for source_idx, source in enumerate(node_list):
                if source not in subgraph:
                    continue

                try:
                    lengths = nx.single_source_dijkstra_path_length(
                        subgraph,
                        source,
                        weight=weight_fn
                    )

                    for target, length in lengths.items():
                        if target in node_to_idx:
                            target_idx = node_to_idx[target]
                            distance_matrix[source_idx, target_idx] = length

                except nx.NetworkXError:
                    continue

                if (source_idx + 1) % 100 == 0:
                    print(f"  Processed {source_idx + 1}/{n} nodes...")

        # Replace inf with max distance + 1 (for disconnected nodes)
        max_finite = np.max(distance_matrix[distance_matrix != np.inf])
        distance_matrix[distance_matrix == np.inf] = max_finite * 2

        # Cache
        self._distance_matrix = distance_matrix
        self._node_list = node_list

        print(f"✓ Distance matrix computed: {distance_matrix.shape}")
        return distance_matrix, node_list

    def project_2d(
        self,
        n_neighbors: int = 15,
        min_dist: float = 0.1,
        metric: str = 'precomputed',
        random_state: int = 42
    ) -> Tuple[np.ndarray, Dict]:
        """
        Project graph to 2D using UMAP.

        Args:
            n_neighbors: UMAP n_neighbors parameter
            min_dist: UMAP min_dist parameter
            metric: Distance metric ('precomputed' for graph distances)
            random_state: Random seed

        Returns:
            - 2D coordinates (Nx2 array)
            - Metadata dict (labels, colors, sizes, etc.)
        """
        print("\n=== Running UMAP 2D Projection ===")

        # Get distance matrix
        distance_matrix, node_list = self.compute_graph_distances()

        # Run UMAP
        print(f"Running UMAP with n_neighbors={n_neighbors}, min_dist={min_dist}...")
        reducer = umap.UMAP(
            n_components=2,
            n_neighbors=min_neighbors(n_neighbors, len(node_list)),
            min_dist=min_dist,
            metric=metric,
            random_state=random_state
        )

        coords_2d = reducer.fit_transform(distance_matrix)

        print(f"✓ UMAP 2D projection complete: {coords_2d.shape}")

        # Compute metadata
        metadata = self._compute_metadata(node_list)

        return coords_2d, metadata

    def project_3d(
        self,
        n_neighbors: int = 15,
        min_dist: float = 0.1,
        metric: str = 'precomputed',
        random_state: int = 42
    ) -> Tuple[np.ndarray, Dict]:
        """
        Project graph to 3D using UMAP.

        Args:
            n_neighbors: UMAP n_neighbors parameter
            min_dist: UMAP min_dist parameter
            metric: Distance metric ('precomputed' for graph distances)
            random_state: Random seed

        Returns:
            - 3D coordinates (Nx3 array)
            - Metadata dict
        """
        print("\n=== Running UMAP 3D Projection ===")

        # Get distance matrix
        distance_matrix, node_list = self.compute_graph_distances()

        # Run UMAP
        print(f"Running UMAP with n_neighbors={n_neighbors}, min_dist={min_dist}...")
        reducer = umap.UMAP(
            n_components=3,
            n_neighbors=min(n_neighbors, len(node_list) - 1),
            min_dist=min_dist,
            metric=metric,
            random_state=random_state
        )

        coords_3d = reducer.fit_transform(distance_matrix)

        print(f"✓ UMAP 3D projection complete: {coords_3d.shape}")

        # Compute metadata
        metadata = self._compute_metadata(node_list)

        return coords_3d, metadata

    def create_plotly_2d(
        self,
        coords: Optional[np.ndarray] = None,
        metadata: Optional[Dict] = None,
        color_by: str = 'pagerank',
        title: str = 'Semantic Manifold (2D UMAP)'
    ) -> go.Figure:
        """
        Create interactive Plotly 2D scatter.

        Args:
            coords: 2D coordinates (if None, will compute)
            metadata: Metadata dict (if None, will compute)
            color_by: Color nodes by ('pagerank', 'domain', 'degree')
            title: Plot title

        Returns:
            Plotly Figure object
        """
        # Compute if not provided
        if coords is None or metadata is None:
            coords, metadata = self.project_2d()

        # Get color values
        color_values = self._get_color_values(metadata, color_by)

        # Create figure
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=coords[:, 0],
            y=coords[:, 1],
            mode='markers',
            marker=dict(
                size=metadata['sizes'],
                color=color_values,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title=color_by.capitalize()),
                line=dict(width=0.5, color='white')
            ),
            text=metadata['labels'],
            hovertemplate='<b>%{text}</b><br>' +
                         f'{color_by}: %{{marker.color:.4f}}<br>' +
                         'x: %{x:.2f}<br>' +
                         'y: %{y:.2f}<br>' +
                         '<extra></extra>',
            name=''
        ))

        fig.update_layout(
            title=title,
            xaxis_title='UMAP 1',
            yaxis_title='UMAP 2',
            template='plotly_dark',
            hovermode='closest',
            width=1000,
            height=800
        )

        # Save
        output_path = self.output_dir / 'manifold_2d.html'
        fig.write_html(str(output_path))
        print(f"✓ 2D UMAP visualization saved: {output_path}")

        return fig

    def create_plotly_3d(
        self,
        coords: Optional[np.ndarray] = None,
        metadata: Optional[Dict] = None,
        color_by: str = 'pagerank',
        title: str = 'Semantic Manifold (3D UMAP)'
    ) -> go.Figure:
        """
        Create interactive Plotly 3D scatter.

        Args:
            coords: 3D coordinates (if None, will compute)
            metadata: Metadata dict (if None, will compute)
            color_by: Color nodes by ('pagerank', 'domain', 'degree')
            title: Plot title

        Returns:
            Plotly Figure object
        """
        # Compute if not provided
        if coords is None or metadata is None:
            coords, metadata = self.project_3d()

        # Get color values
        color_values = self._get_color_values(metadata, color_by)

        # Create figure
        fig = go.Figure()

        fig.add_trace(go.Scatter3d(
            x=coords[:, 0],
            y=coords[:, 1],
            z=coords[:, 2],
            mode='markers',
            marker=dict(
                size=metadata['sizes'] / 2,  # Smaller for 3D
                color=color_values,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title=color_by.capitalize()),
                line=dict(width=0.5, color='white')
            ),
            text=metadata['labels'],
            hovertemplate='<b>%{text}</b><br>' +
                         f'{color_by}: %{{marker.color:.4f}}<br>' +
                         'x: %{x:.2f}<br>' +
                         'y: %{y:.2f}<br>' +
                         'z: %{z:.2f}<br>' +
                         '<extra></extra>',
            name=''
        ))

        fig.update_layout(
            title=title,
            scene=dict(
                xaxis_title='UMAP 1',
                yaxis_title='UMAP 2',
                zaxis_title='UMAP 3'
            ),
            template='plotly_dark',
            width=1000,
            height=800
        )

        # Save
        output_path = self.output_dir / 'manifold_3d.html'
        fig.write_html(str(output_path))
        print(f"✓ 3D UMAP visualization saved: {output_path}")

        return fig

    def _compute_metadata(self, node_list: List[str]) -> Dict:
        """
        Compute metadata for nodes (labels, colors, sizes).

        Args:
            node_list: List of node names

        Returns:
            Metadata dict
        """
        # Get PageRank
        pagerank_full = nx.pagerank(self.graph, weight='weight')
        pagerank = [pagerank_full.get(node, 0) for node in node_list]

        # Get degrees
        in_degree = [self.graph.in_degree(node) if node in self.graph else 0 for node in node_list]
        out_degree = [self.graph.out_degree(node) if node in self.graph else 0 for node in node_list]

        # Get domains (if node is a seed)
        seeds_meta = get_seeds_with_metadata()
        seed_to_domain = {s['word'].lower(): s['domain'] for s in seeds_meta}
        domains = [seed_to_domain.get(node, 'expanded') for node in node_list]

        # Compute sizes (based on PageRank)
        pagerank_arr = np.array(pagerank)
        sizes = 5 + (pagerank_arr / pagerank_arr.max() * 15) if pagerank_arr.max() > 0 else np.ones(len(node_list)) * 10

        return {
            'labels': node_list,
            'pagerank': pagerank,
            'in_degree': in_degree,
            'out_degree': out_degree,
            'domains': domains,
            'sizes': sizes
        }

    def _get_color_values(self, metadata: Dict, color_by: str) -> List:
        """
        Get color values based on coloring scheme.

        Args:
            metadata: Metadata dict
            color_by: Coloring scheme

        Returns:
            List of color values
        """
        if color_by == 'pagerank':
            return metadata['pagerank']
        elif color_by == 'degree':
            return [i + o for i, o in zip(metadata['in_degree'], metadata['out_degree'])]
        elif color_by == 'domain':
            # Map domains to integers
            unique_domains = list(set(metadata['domains']))
            domain_to_int = {d: i for i, d in enumerate(unique_domains)}
            return [domain_to_int[d] for d in metadata['domains']]
        else:
            return metadata['pagerank']  # Default

    def __repr__(self) -> str:
        """String representation."""
        return f"ManifoldProjector(nodes={self.graph.number_of_nodes()})"
