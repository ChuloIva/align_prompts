"""
Checkpoint Manager for Semantic Gravity Mapping.

Handles saving and loading checkpoints across all phases to enable:
- Resume capability after interruptions
- No data loss from crashes or timeouts
- Incremental progress tracking

Checkpoints are saved atomically using pickle for graph objects
and JSON for metadata.
"""

import json
import pickle
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import networkx as nx


class CheckpointManager:
    """
    Manages checkpoints across all SGM phases.

    Provides atomic checkpoint save/load with metadata tracking.
    Checkpoints include phase number, iteration count, timestamp,
    and phase-specific data.

    Attributes:
        checkpoint_dir: Directory for checkpoint storage
        config: Optional configuration dict for reproducibility
    """

    def __init__(
        self,
        checkpoint_dir: str | Path,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory path for storing checkpoints
            config: Optional configuration dict to save with checkpoints
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or {}

    def save_checkpoint(
        self,
        phase: int,
        data: Dict[str, Any],
        iteration: Optional[int] = None
    ) -> Path:
        """
        Save checkpoint with atomic write.

        Saves checkpoint data and metadata in separate files:
        - {phase}_{iteration}.pkl: Pickle dump of data
        - {phase}_{iteration}_meta.json: Metadata (timestamp, config, etc.)

        Uses atomic write via temp file + rename to prevent corruption.

        Args:
            phase: Phase number (1-5)
            data: Dictionary containing phase-specific data
                  (e.g., {'graph': nx.DiGraph, 'visited': set})
            iteration: Optional iteration number for progress tracking

        Returns:
            Path to saved checkpoint file

        Example:
            >>> manager = CheckpointManager('/tmp/checkpoints')
            >>> graph = nx.DiGraph()
            >>> manager.save_checkpoint(1, {'graph': graph, 'visited': set()}, 500)
        """
        # Generate checkpoint filename
        if iteration is not None:
            basename = f"phase{phase}_iteration_{iteration}"
        else:
            basename = f"phase{phase}_final"

        data_path = self.checkpoint_dir / f"{basename}.pkl"
        meta_path = self.checkpoint_dir / f"{basename}_meta.json"
        temp_data_path = data_path.with_suffix('.pkl.tmp')
        temp_meta_path = meta_path.with_suffix('.json.tmp')

        # Prepare metadata
        metadata = {
            'phase': phase,
            'iteration': iteration,
            'timestamp': datetime.now().isoformat(),
            'config': self.config,
            'data_keys': list(data.keys())
        }

        try:
            # Write data to temp file (atomic)
            with open(temp_data_path, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

            # Write metadata to temp file
            with open(temp_meta_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            # Atomic rename (POSIX systems guarantee atomicity)
            shutil.move(str(temp_data_path), str(data_path))
            shutil.move(str(temp_meta_path), str(meta_path))

            return data_path

        except Exception as e:
            # Clean up temp files on error
            if temp_data_path.exists():
                temp_data_path.unlink()
            if temp_meta_path.exists():
                temp_meta_path.unlink()
            raise RuntimeError(f"Failed to save checkpoint: {e}") from e

    def load_checkpoint(
        self,
        phase: int,
        iteration: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint for a specific phase.

        If iteration is specified, loads that specific checkpoint.
        Otherwise, loads the most recent checkpoint for the phase.

        Args:
            phase: Phase number to load
            iteration: Optional specific iteration to load

        Returns:
            Dictionary containing checkpoint data, or None if not found

        Example:
            >>> manager = CheckpointManager('/tmp/checkpoints')
            >>> data = manager.load_checkpoint(1, iteration=500)
            >>> if data:
            ...     graph = data['graph']
            ...     visited = data['visited']
        """
        # If iteration specified, load that specific checkpoint
        if iteration is not None:
            checkpoint_path = self.checkpoint_dir / f"phase{phase}_iteration_{iteration}.pkl"
            if not checkpoint_path.exists():
                return None
        else:
            # Find most recent checkpoint for this phase
            checkpoint_path = self._find_latest_checkpoint(phase)
            if checkpoint_path is None:
                return None

        try:
            with open(checkpoint_path, 'rb') as f:
                data = pickle.load(f)
            return data
        except Exception as e:
            raise RuntimeError(f"Failed to load checkpoint {checkpoint_path}: {e}") from e

    def _find_latest_checkpoint(self, phase: int) -> Optional[Path]:
        """
        Find the most recent checkpoint file for a phase.

        Searches for both iteration checkpoints and final checkpoint,
        returning the most recent by filename (assumes iteration order).

        Args:
            phase: Phase number

        Returns:
            Path to latest checkpoint, or None if no checkpoints exist
        """
        pattern = f"phase{phase}_*.pkl"
        checkpoints = list(self.checkpoint_dir.glob(pattern))

        if not checkpoints:
            return None

        # Sort by filename (iteration number encoded in name)
        # Final checkpoint will sort last
        checkpoints.sort()
        return checkpoints[-1]

    def list_checkpoints(self, phase: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List all available checkpoints with metadata.

        Args:
            phase: Optional phase number to filter by

        Returns:
            List of checkpoint metadata dicts sorted by timestamp

        Example:
            >>> manager = CheckpointManager('/tmp/checkpoints')
            >>> checkpoints = manager.list_checkpoints(phase=1)
            >>> for ckpt in checkpoints:
            ...     print(f"Phase {ckpt['phase']}, Iteration {ckpt['iteration']}")
        """
        if phase is not None:
            pattern = f"phase{phase}_*_meta.json"
        else:
            pattern = "*_meta.json"

        meta_files = list(self.checkpoint_dir.glob(pattern))
        checkpoints = []

        for meta_file in meta_files:
            try:
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                    metadata['checkpoint_file'] = str(meta_file.with_suffix('').with_suffix('.pkl'))
                    checkpoints.append(metadata)
            except Exception:
                # Skip corrupted metadata files
                continue

        # Sort by timestamp
        checkpoints.sort(key=lambda x: x.get('timestamp', ''))
        return checkpoints

    def delete_checkpoint(self, phase: int, iteration: Optional[int] = None):
        """
        Delete a specific checkpoint.

        Args:
            phase: Phase number
            iteration: Optional iteration number (deletes that specific checkpoint)
                      If None, deletes all checkpoints for the phase

        Example:
            >>> manager = CheckpointManager('/tmp/checkpoints')
            >>> manager.delete_checkpoint(1, iteration=500)
        """
        if iteration is not None:
            # Delete specific checkpoint
            basename = f"phase{phase}_iteration_{iteration}"
            data_path = self.checkpoint_dir / f"{basename}.pkl"
            meta_path = self.checkpoint_dir / f"{basename}_meta.json"

            if data_path.exists():
                data_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
        else:
            # Delete all checkpoints for phase
            for file in self.checkpoint_dir.glob(f"phase{phase}_*"):
                file.unlink()

    def get_resume_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the latest checkpoint for resume.

        Useful for determining where to resume after interruption.

        Returns:
            Dict with resume information, or None if no checkpoints

        Example:
            >>> manager = CheckpointManager('/tmp/checkpoints')
            >>> info = manager.get_resume_info()
            >>> if info:
            ...     print(f"Can resume from phase {info['phase']}, iteration {info['iteration']}")
        """
        all_checkpoints = self.list_checkpoints()

        if not all_checkpoints:
            return None

        # Return most recent checkpoint
        latest = all_checkpoints[-1]
        return {
            'phase': latest['phase'],
            'iteration': latest.get('iteration'),
            'timestamp': latest['timestamp'],
            'checkpoint_file': latest['checkpoint_file']
        }

    def save_graph(
        self,
        graph: nx.DiGraph,
        filename: str,
        include_metadata: bool = True
    ) -> Path:
        """
        Save NetworkX graph with optional metadata.

        Convenience method for saving final graphs (not checkpoints).
        Saves both pickle format (for Python) and edge list (for Gephi).

        Args:
            graph: NetworkX directed graph
            filename: Base filename (without extension)
            include_metadata: If True, also saves graph metadata as JSON

        Returns:
            Path to saved graph file

        Example:
            >>> manager = CheckpointManager('/tmp/checkpoints')
            >>> graph = nx.DiGraph()
            >>> manager.save_graph(graph, 'semantic_graph')
        """
        output_dir = self.checkpoint_dir.parent / 'graphs'
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save as pickle (preserves all attributes)
        pickle_path = output_dir / f"{filename}.gpickle"
        with open(pickle_path, 'wb') as f:
            pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)

        # Save as edge list CSV (for Gephi/external tools)
        csv_path = output_dir / f"{filename}.csv"
        with open(csv_path, 'w') as f:
            f.write("source,target,weight\n")
            for u, v, data in graph.edges(data=True):
                weight = data.get('weight', 1.0)
                f.write(f"{u},{v},{weight}\n")

        # Save metadata if requested
        if include_metadata:
            meta = {
                'num_nodes': graph.number_of_nodes(),
                'num_edges': graph.number_of_edges(),
                'is_directed': graph.is_directed(),
                'timestamp': datetime.now().isoformat()
            }
            meta_path = output_dir / f"{filename}_meta.json"
            with open(meta_path, 'w') as f:
                json.dump(meta, f, indent=2)

        return pickle_path

    def load_graph(self, filename: str) -> nx.DiGraph:
        """
        Load NetworkX graph from pickle file.

        Args:
            filename: Base filename (without extension)

        Returns:
            NetworkX directed graph

        Example:
            >>> manager = CheckpointManager('/tmp/checkpoints')
            >>> graph = manager.load_graph('semantic_graph')
        """
        graph_dir = self.checkpoint_dir.parent / 'graphs'
        pickle_path = graph_dir / f"{filename}.gpickle"

        if not pickle_path.exists():
            raise FileNotFoundError(f"Graph file not found: {pickle_path}")

        with open(pickle_path, 'rb') as f:
            return pickle.load(f)
