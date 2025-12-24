"""
Heatmap Generator for Semantic Gravity Mapping.

Creates heatmaps and distribution plots for:
- Domain convergence analysis
- Asymmetry matrices (directional bias)
- Hub centrality comparisons
- Edge weight distributions
"""

from pathlib import Path
from typing import Dict, List, Any
import numpy as np
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from scipy import stats


class HeatmapGenerator:
    """
    Generates heatmaps and distribution plots for analysis visualization.

    Attributes:
        results: Analysis results from TopologyAnalyzer
        output_dir: Directory for saving HTML files
    """

    def __init__(
        self,
        analysis_results: Dict[str, Any],
        output_dir: str | Path = './data/sgm/visualizations'
    ):
        """
        Initialize heatmap generator.

        Args:
            analysis_results: Results from TopologyAnalyzer.analyze_all()
            output_dir: Output directory for HTML files
        """
        self.results = analysis_results
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def convergence_heatmap(self) -> go.Figure:
        """
        Create domain convergence heatmap.

        Shows:
        - Rows: Domains
        - Columns: Metrics (avg_hops, min_hops, max_hops, std_hops)
        - Color: Convergence speed (red=fast, blue=slow)

        Returns:
            Plotly Figure object
        """
        conv_data = self.results.get('convergence', {}).get('by_domain', {})

        if not conv_data:
            print("Warning: No convergence data available")
            return go.Figure()

        # Prepare data
        domains = []
        metrics = ['avg_hops', 'min_hops', 'max_hops', 'std_hops']
        data_matrix = []

        for domain, domain_data in sorted(conv_data.items()):
            domains.append(domain.replace('_', ' ').title())
            row = []
            for metric in metrics:
                value = domain_data.get(metric, 0)
                # Replace inf with NaN
                if value == float('inf'):
                    value = np.nan
                row.append(value)
            data_matrix.append(row)

        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=data_matrix,
            x=[m.replace('_', ' ').title() for m in metrics],
            y=domains,
            colorscale='RdBu_r',  # Red=fast, Blue=slow
            text=[[f'{val:.2f}' if not np.isnan(val) else 'N/A'
                   for val in row] for row in data_matrix],
            texttemplate='%{text}',
            textfont={"size": 10},
            colorbar=dict(title='Hops')
        ))

        fig.update_layout(
            title='Domain Convergence Analysis<br><sub>Lower values = faster convergence to semantic hubs</sub>',
            xaxis_title='Convergence Metrics',
            yaxis_title='Domains',
            template='plotly_dark',
            width=800,
            height=600
        )

        # Save
        output_path = self.output_dir / 'convergence_heatmap.html'
        fig.write_html(str(output_path))
        print(f"✓ Convergence heatmap saved: {output_path}")

        return fig

    def asymmetry_matrix(self, top_n: int = 50) -> go.Figure:
        """
        Create asymmetry heatmap for top asymmetric pairs.

        Shows directional bias in associations.

        Args:
            top_n: Number of top asymmetric pairs to show

        Returns:
            Plotly Figure object
        """
        asymmetry_data = self.results.get('asymmetry', [])[:top_n]

        if not asymmetry_data:
            print("Warning: No asymmetry data available")
            return go.Figure()

        # Extract unique words
        words = set()
        for pair in asymmetry_data:
            words.add(pair['source'])
            words.add(pair['target'])

        words = sorted(list(words))
        n = len(words)
        word_to_idx = {w: i for i, w in enumerate(words)}

        # Create matrix (forward - backward weights)
        matrix = np.zeros((n, n))

        for pair in asymmetry_data:
            src_idx = word_to_idx[pair['source']]
            tgt_idx = word_to_idx[pair['target']]

            forward = pair['forward_weight']
            backward = pair['backward_weight']

            # Store asymmetry score
            matrix[src_idx, tgt_idx] = forward - backward

        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            x=words,
            y=words,
            colorscale='RdBu',  # Red=strong forward, Blue=strong backward
            zmid=0,  # Center at 0
            text=[[f'{val:.3f}' for val in row] for row in matrix],
            texttemplate='%{text}',
            textfont={"size": 8},
            colorbar=dict(title='Forward - Backward')
        ))

        fig.update_layout(
            title='Association Asymmetry Matrix<br><sub>Red = Strong A→B, Blue = Strong B→A</sub>',
            xaxis_title='Target Word',
            yaxis_title='Source Word',
            template='plotly_dark',
            width=900,
            height=900,
            xaxis=dict(tickangle=-45)
        )

        # Save
        output_path = self.output_dir / 'asymmetry_matrix.html'
        fig.write_html(str(output_path))
        print(f"✓ Asymmetry matrix saved: {output_path}")

        return fig

    def hub_centrality_comparison(self) -> go.Figure:
        """
        Compare centrality metrics for top hubs.

        Shows which hubs dominate by different metrics.

        Returns:
            Plotly Figure object
        """
        centrality_data = self.results.get('centrality', {})
        hubs_data = self.results.get('hubs', [])[:20]

        if not centrality_data or not hubs_data:
            print("Warning: No centrality data available")
            return go.Figure()

        # Get hub words
        hub_words = [h['word'] for h in hubs_data]

        # Prepare data
        metrics = ['pagerank', 'betweenness', 'in_degree', 'out_degree']
        data_matrix = []

        for hub in hub_words:
            row = []
            for metric in metrics:
                value = centrality_data.get(metric, {}).get(hub, 0)
                row.append(value)
            data_matrix.append(row)

        # Normalize each column to [0, 1]
        data_matrix = np.array(data_matrix)
        for col in range(data_matrix.shape[1]):
            col_max = data_matrix[:, col].max()
            if col_max > 0:
                data_matrix[:, col] /= col_max

        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=data_matrix,
            x=[m.replace('_', ' ').title() for m in metrics],
            y=hub_words,
            colorscale='Viridis',
            text=[[f'{val:.3f}' for val in row] for row in data_matrix],
            texttemplate='%{text}',
            textfont={"size": 10},
            colorbar=dict(title='Normalized Score')
        ))

        fig.update_layout(
            title='Hub Centrality Comparison<br><sub>Normalized scores across different metrics</sub>',
            xaxis_title='Centrality Metrics',
            yaxis_title='Top Hubs',
            template='plotly_dark',
            width=700,
            height=800
        )

        # Save
        output_path = self.output_dir / 'hub_centrality.html'
        fig.write_html(str(output_path))
        print(f"✓ Hub centrality comparison saved: {output_path}")

        return fig

    def weight_distribution_kde(self, graph: nx.DiGraph) -> go.Figure:
        """
        Edge weight distribution with KDE overlay.

        Args:
            graph: Weighted directed graph

        Returns:
            Plotly Figure object
        """
        # Get all weights
        weights = [data.get('weight', 0) for _, _, data in graph.edges(data=True) if data.get('weight', 0) > 0]

        if not weights:
            print("Warning: No edge weights available")
            return go.Figure()

        weights = np.array(weights)

        # Compute KDE
        kde = stats.gaussian_kde(weights)
        x_kde = np.linspace(weights.min(), weights.max(), 200)
        y_kde = kde(x_kde)

        # Compute quartiles
        q1, q2, q3 = np.percentile(weights, [25, 50, 75])
        mean = weights.mean()

        # Create subplot
        fig = make_subplots(
            rows=1, cols=1,
            subplot_titles=['Edge Weight Distribution']
        )

        # Histogram
        fig.add_trace(go.Histogram(
            x=weights,
            nbinsx=50,
            name='Weight Distribution',
            marker_color='steelblue',
            opacity=0.7
        ))

        # KDE
        fig.add_trace(go.Scatter(
            x=x_kde,
            y=y_kde * len(weights) * (weights.max() - weights.min()) / 50,  # Scale to match histogram
            mode='lines',
            name='KDE',
            line=dict(color='red', width=2)
        ))

        # Add quartile lines
        for val, name, color in [(q1, 'Q1', 'green'), (q2, 'Median', 'yellow'), (q3, 'Q3', 'orange'), (mean, 'Mean', 'cyan')]:
            fig.add_vline(x=val, line_dash="dash", line_color=color, annotation_text=f'{name}: {val:.3f}', annotation_position="top right")

        fig.update_layout(
            title=f'Edge Weight Distribution (N={len(weights):,})<br><sub>Mean: {mean:.3f}, Median: {q2:.3f}, Std: {weights.std():.3f}</sub>',
            xaxis_title='Edge Weight',
            yaxis_title='Frequency',
            template='plotly_dark',
            showlegend=True,
            width=900,
            height=600
        )

        # Save
        output_path = self.output_dir / 'weight_distribution.html'
        fig.write_html(str(output_path))
        print(f"✓ Weight distribution saved: {output_path}")

        return fig

    def __repr__(self) -> str:
        """String representation."""
        return "HeatmapGenerator()"
