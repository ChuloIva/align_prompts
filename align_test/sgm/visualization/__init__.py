"""
Visualization Module for Semantic Gravity Mapping.

Provides interactive visualizations for exploring semantic graphs:
- Interactive network graphs (Pyvis)
- 2D/3D manifold projections (UMAP + Plotly)
- Convergence and asymmetry heatmaps
- Island cluster exploration

Example usage:
    >>> from align_test.sgm.visualization import (
    ...     InteractiveGraphVisualizer,
    ...     ManifoldProjector,
    ...     HeatmapGenerator,
    ...     IslandExplorer
    ... )
    >>>
    >>> # Create visualizations
    >>> graph_viz = InteractiveGraphVisualizer(graph, results)
    >>> graph_viz.create_full_network(filter_top_n=500)
    >>>
    >>> manifold = ManifoldProjector(graph, results)
    >>> coords_2d, metadata = manifold.project_2d()
    >>> manifold.create_plotly_2d(coords_2d, metadata)
"""

from align_test.sgm.visualization.graph_visualizer import InteractiveGraphVisualizer
from align_test.sgm.visualization.manifold_projector import ManifoldProjector
from align_test.sgm.visualization.heatmap_generator import HeatmapGenerator
from align_test.sgm.visualization.island_explorer import IslandExplorer

__all__ = [
    'InteractiveGraphVisualizer',
    'ManifoldProjector',
    'HeatmapGenerator',
    'IslandExplorer',
]

__version__ = '0.1.0'
