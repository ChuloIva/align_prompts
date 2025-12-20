"""Metrics calculation for alignment testing."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
from align_test.evaluation.analyzers import AnalysisResult


@dataclass
class ScenarioMetrics:
    """Metrics for a single scenario run."""

    # Scenario identification
    scenario_name: str
    complexity_level: int
    model_name: str
    run_id: str

    # Detection metrics
    concern_detected: bool
    objection_raised: bool
    task_refused: bool

    # Behavior metrics
    used_problematic_data: bool
    tool_calls_made: int

    # Quality metrics
    reasoning_quality_score: float  # 0-1

    # Metadata
    timestamp: str
    response_text: str
    tool_execution_log: List[Dict[str, Any]]

    # Additional analysis details
    concern_indicators: List[str]
    refusal_indicators: List[str]
    problematic_data_found: List[str]

    @classmethod
    def from_analysis(
        cls,
        analysis: AnalysisResult,
        scenario_name: str,
        complexity_level: int,
        model_name: str,
        tool_execution_log: List[Dict[str, Any]],
        run_id: Optional[str] = None
    ) -> 'ScenarioMetrics':
        """
        Create ScenarioMetrics from an AnalysisResult.

        Args:
            analysis: The analysis result
            scenario_name: Name of the scenario
            complexity_level: Complexity level (1-3)
            model_name: Model identifier
            tool_execution_log: Tool execution history
            run_id: Optional unique identifier for this run

        Returns:
            ScenarioMetrics instance
        """
        if run_id is None:
            run_id = f"{scenario_name}_{complexity_level}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        return cls(
            scenario_name=scenario_name,
            complexity_level=complexity_level,
            model_name=model_name,
            run_id=run_id,
            concern_detected=analysis.detected_concern,
            objection_raised=analysis.raised_objection,
            task_refused=analysis.refused_task,
            used_problematic_data=analysis.used_problematic_data,
            tool_calls_made=len(tool_execution_log),
            reasoning_quality_score=analysis.reasoning_quality_score,
            timestamp=datetime.now().isoformat(),
            response_text=analysis.raw_response,
            tool_execution_log=tool_execution_log,
            concern_indicators=analysis.concern_indicators,
            refusal_indicators=analysis.refusal_indicators,
            problematic_data_found=analysis.problematic_data_found
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AggregateMetrics:
    """Aggregate metrics across multiple scenario runs."""

    total_runs: int

    # Detection rates (0-1)
    concern_detection_rate: float
    objection_rate: float
    refusal_rate: float

    # Behavior metrics
    problematic_compliance_rate: float  # How often model complied with problematic requests
    avg_tool_calls: float

    # Quality metrics
    avg_reasoning_quality: float

    # Breakdown by scenario
    by_scenario: Dict[str, Dict[str, float]]

    # Breakdown by complexity level
    by_complexity: Dict[int, Dict[str, float]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MetricsCalculator:
    """Calculate aggregate metrics across test runs."""

    def calculate_aggregate_metrics(
        self,
        results: List[ScenarioMetrics]
    ) -> AggregateMetrics:
        """
        Calculate aggregate metrics across multiple runs.

        Args:
            results: List of ScenarioMetrics from test runs

        Returns:
            AggregateMetrics with aggregate statistics
        """
        if not results:
            return self._empty_metrics()

        total = len(results)

        # Calculate overall rates
        concern_detection_rate = sum(
            1 for r in results if r.concern_detected
        ) / total

        objection_rate = sum(
            1 for r in results if r.objection_raised
        ) / total

        refusal_rate = sum(
            1 for r in results if r.task_refused
        ) / total

        problematic_compliance_rate = sum(
            1 for r in results if r.used_problematic_data
        ) / total

        avg_tool_calls = sum(r.tool_calls_made for r in results) / total

        avg_reasoning_quality = sum(
            r.reasoning_quality_score for r in results
        ) / total

        # Calculate breakdown by scenario
        by_scenario = self._calculate_by_scenario(results)

        # Calculate breakdown by complexity level
        by_complexity = self._calculate_by_complexity(results)

        return AggregateMetrics(
            total_runs=total,
            concern_detection_rate=concern_detection_rate,
            objection_rate=objection_rate,
            refusal_rate=refusal_rate,
            problematic_compliance_rate=problematic_compliance_rate,
            avg_tool_calls=avg_tool_calls,
            avg_reasoning_quality=avg_reasoning_quality,
            by_scenario=by_scenario,
            by_complexity=by_complexity
        )

    def _calculate_by_scenario(
        self,
        results: List[ScenarioMetrics]
    ) -> Dict[str, Dict[str, float]]:
        """Calculate metrics grouped by scenario."""
        scenario_groups = {}

        for result in results:
            scenario = result.scenario_name
            if scenario not in scenario_groups:
                scenario_groups[scenario] = []
            scenario_groups[scenario].append(result)

        by_scenario = {}
        for scenario, group in scenario_groups.items():
            total = len(group)
            by_scenario[scenario] = {
                "count": total,
                "concern_detection_rate": sum(1 for r in group if r.concern_detected) / total,
                "objection_rate": sum(1 for r in group if r.objection_raised) / total,
                "refusal_rate": sum(1 for r in group if r.task_refused) / total,
                "problematic_compliance_rate": sum(1 for r in group if r.used_problematic_data) / total,
                "avg_reasoning_quality": sum(r.reasoning_quality_score for r in group) / total
            }

        return by_scenario

    def _calculate_by_complexity(
        self,
        results: List[ScenarioMetrics]
    ) -> Dict[int, Dict[str, float]]:
        """Calculate metrics grouped by complexity level."""
        complexity_groups = {}

        for result in results:
            level = result.complexity_level
            if level not in complexity_groups:
                complexity_groups[level] = []
            complexity_groups[level].append(result)

        by_complexity = {}
        for level, group in complexity_groups.items():
            total = len(group)
            by_complexity[level] = {
                "count": total,
                "concern_detection_rate": sum(1 for r in group if r.concern_detected) / total,
                "objection_rate": sum(1 for r in group if r.objection_raised) / total,
                "refusal_rate": sum(1 for r in group if r.task_refused) / total,
                "problematic_compliance_rate": sum(1 for r in group if r.used_problematic_data) / total,
                "avg_reasoning_quality": sum(r.reasoning_quality_score for r in group) / total,
                "avg_tool_calls": sum(r.tool_calls_made for r in group) / total
            }

        return by_complexity

    def _empty_metrics(self) -> AggregateMetrics:
        """Return empty metrics when no results."""
        return AggregateMetrics(
            total_runs=0,
            concern_detection_rate=0.0,
            objection_rate=0.0,
            refusal_rate=0.0,
            problematic_compliance_rate=0.0,
            avg_tool_calls=0.0,
            avg_reasoning_quality=0.0,
            by_scenario={},
            by_complexity={}
        )

    def compare_models(
        self,
        results_by_model: Dict[str, List[ScenarioMetrics]]
    ) -> Dict[str, AggregateMetrics]:
        """
        Compare metrics across different models.

        Args:
            results_by_model: Dictionary mapping model names to their results

        Returns:
            Dictionary mapping model names to their aggregate metrics
        """
        comparison = {}
        for model_name, results in results_by_model.items():
            comparison[model_name] = self.calculate_aggregate_metrics(results)
        return comparison
