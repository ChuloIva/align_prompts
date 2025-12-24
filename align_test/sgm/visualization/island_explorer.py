"""
Island Explorer for Semantic Gravity Mapping.

Visualizes isolated concept clusters (islands) that are
disconnected from the main semantic network.
"""

from pathlib import Path
from typing import Dict, List, Any
import networkx as nx
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pyvis.network import Network


class IslandExplorer:
    """
    Explores and visualizes isolated concept clusters.

    Islands represent domains or topics that are disconnected
    from the main semantic network - potential model blind spots.

    Attributes:
        graph: NetworkX directed graph
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
        Initialize island explorer.

        Args:
            graph: Weighted directed graph
            analysis_results: Results from TopologyAnalyzer.analyze_all()
            output_dir: Output directory for HTML files
        """
        self.graph = graph
        self.results = analysis_results
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_island_grid(self, max_islands: int = 6) -> go.Figure:
        """
        Create subplot grid showing top N islands.

        Each subplot shows a force-directed layout of the island.

        Args:
            max_islands: Maximum number of islands to show

        Returns:
            Plotly Figure object
        """
        islands_data = self.results.get('islands', [])[:max_islands]

        if not islands_data:
            print("Warning: No islands found")
            return go.Figure()

        # Calculate grid layout
        ncols = min(3, len(islands_data))
        nrows = (len(islands_data) + ncols - 1) // ncols

        # Create subplots
        fig = make_subplots(
            rows=nrows,
            cols=ncols,
            subplot_titles=[f"Island {i+1} (size: {island['size']})"
                           for i, island in enumerate(islands_data)],
            specs=[[{'type': 'scatter'} for _ in range(ncols)] for _ in range(nrows)],
            horizontal_spacing=0.1,
            vertical_spacing=0.15
        )

        # Plot each island
        for idx, island_data in enumerate(islands_data):
            row = idx // ncols + 1
            col = idx % ncols + 1

            # Get subgraph for island
            island_nodes = island_data['words']
            subgraph = self.graph.subgraph(island_nodes).copy()

            # Compute layout
            try:
                pos = nx.spring_layout(subgraph, k=2, iterations=50)
            except:
                # Fallback for disconnected graphs
                pos = {node: (i % 5, i // 5) for i, node in enumerate(island_nodes)}

            # Add edges
            edge_x = []
            edge_y = []
            for u, v in subgraph.edges():
                x0, y0 = pos[u]
                x1, y1 = pos[v]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])

            fig.add_trace(
                go.Scatter(
                    x=edge_x,
                    y=edge_y,
                    mode='lines',
                    line=dict(width=0.5, color='#888'),
                    hoverinfo='none',
                    showlegend=False
                ),
                row=row,
                col=col
            )

            # Add nodes
            node_x = [pos[node][0] for node in island_nodes]
            node_y = [pos[node][1] for node in island_nodes]

            fig.add_trace(
                go.Scatter(
                    x=node_x,
                    y=node_y,
                    mode='markers+text',
                    text=island_nodes,
                    textposition='top center',
                    textfont=dict(size=8),
                    marker=dict(size=10, color='lightblue'),
                    hovertext=island_nodes,
                    hoverinfo='text',
                    showlegend=False
                ),
                row=row,
                col=col
            )

            # Update axes
            fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, row=row, col=col)
            fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False, row=row, col=col)

        fig.update_layout(
            title='Isolated Concept Clusters (Islands)<br><sub>Disconnected semantic regions</sub>',
            showlegend=False,
            template='plotly_dark',
            height=300 * nrows,
            width=400 * ncols
        )

        # Save
        output_path = self.output_dir / 'islands_grid.html'
        fig.write_html(str(output_path))
        print(f"✓ Islands grid visualization saved: {output_path}")

        return fig

    def create_island_network(self, island_idx: int = 0, height: str = '600px') -> str:
        """
        Create interactive Pyvis network for single island.

        Args:
            island_idx: Index of island to visualize (0-based)
            height: Canvas height

        Returns:
            Path to generated HTML file
        """
        islands_data = self.results.get('islands', [])

        if island_idx >= len(islands_data):
            print(f"Warning: Island index {island_idx} out of range")
            return ""

        island_data = islands_data[island_idx]
        island_nodes = island_data['words']

        # Get subgraph
        subgraph = self.graph.subgraph(island_nodes).copy()

        # Initialize network
        net = Network(height=height, width='100%', directed=True, notebook=False)
        net.barnes_hut()

        # Add nodes
        for node in island_nodes:
            degree = subgraph.degree(node)
            size = 10 + degree * 2

            net.add_node(
                node,
                label=node,
                title=f"{node}\nDegree: {degree}",
                size=size,
                color='lightgreen'
            )

        # Add edges
        for u, v, data in subgraph.edges(data=True):
            weight = data.get('weight', 0.1)
            width = max(1, weight * 5)
            net.add_edge(u, v, value=width, title=f"Weight: {weight:.3f}")

        # Save
        output_path = self.output_dir / f'island_{island_idx}.html'
        net.save_graph(str(output_path))

        print(f"✓ Island {island_idx} network saved: {output_path}")
        return str(output_path)

    def island_statistics_table(self) -> pd.DataFrame:
        """
        Create summary table of all islands.

        Returns:
            Pandas DataFrame with island statistics
        """
        islands_data = self.results.get('islands', [])

        if not islands_data:
            print("Warning: No islands found")
            return pd.DataFrame()

        # Prepare data
        rows = []

        for idx, island_data in enumerate(islands_data):
            island_nodes = island_data['words']
            subgraph = self.graph.subgraph(island_nodes).copy()

            # Compute statistics
            weights = [data.get('weight', 0) for _, _, data in subgraph.edges(data=True)]
            avg_weight = sum(weights) / len(weights) if weights else 0

            # Sample words (first 5)
            sample_words = ', '.join(island_nodes[:5])
            if len(island_nodes) > 5:
                sample_words += ', ...'

            rows.append({
                'Island ID': idx + 1,
                'Size': island_data['size'],
                'Edges': subgraph.number_of_edges(),
                'Avg Weight': f"{avg_weight:.3f}",
                'Sample Words': sample_words
            })

        df = pd.DataFrame(rows)

        # Save as CSV
        output_path = self.output_dir / 'island_statistics.csv'
        df.to_csv(output_path, index=False)
        print(f"✓ Island statistics table saved: {output_path}")

        return df

    def __repr__(self) -> str:
        """String representation."""
        num_islands = len(self.results.get('islands', []))
        return f"IslandExplorer(islands={num_islands})"
