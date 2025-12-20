"""Results reporting and visualization."""

from typing import List, Optional
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from align_test.evaluation.metrics import ScenarioMetrics, AggregateMetrics


class ResultsReporter:
    """Generate reports and visualizations from test results."""

    def __init__(self):
        """Initialize the reporter."""
        # Set seaborn style for better-looking plots
        sns.set_style("whitegrid")
        sns.set_palette("husl")

    def generate_summary_report(
        self,
        results: List[ScenarioMetrics],
        aggregate: AggregateMetrics
    ) -> str:
        """
        Generate a human-readable summary report.

        Args:
            results: List of scenario metrics
            aggregate: Aggregate metrics

        Returns:
            Formatted summary string
        """
        report_lines = [
            "=" * 80,
            "ALIGNMENT TESTING SUMMARY REPORT",
            "=" * 80,
            "",
            f"Total Test Runs: {aggregate.total_runs}",
            "",
            "OVERALL METRICS:",
            "-" * 40,
            f"  Concern Detection Rate:       {aggregate.concern_detection_rate:.1%}",
            f"  Objection Raised Rate:        {aggregate.objection_rate:.1%}",
            f"  Task Refusal Rate:            {aggregate.refusal_rate:.1%}",
            f"  Problematic Compliance Rate:  {aggregate.problematic_compliance_rate:.1%}",
            f"  Average Reasoning Quality:    {aggregate.avg_reasoning_quality:.2f} / 1.0",
            f"  Average Tool Calls:           {aggregate.avg_tool_calls:.1f}",
            "",
        ]

        # By scenario breakdown
        if aggregate.by_scenario:
            report_lines.extend([
                "BREAKDOWN BY SCENARIO:",
                "-" * 40,
            ])
            for scenario, metrics in aggregate.by_scenario.items():
                report_lines.extend([
                    f"\n{scenario.upper()} ({metrics['count']} runs):",
                    f"  Concern Detection: {metrics['concern_detection_rate']:.1%}",
                    f"  Objection Rate:    {metrics['objection_rate']:.1%}",
                    f"  Refusal Rate:      {metrics['refusal_rate']:.1%}",
                    f"  Problematic Data:  {metrics['problematic_compliance_rate']:.1%}",
                ])

        # By complexity level breakdown
        if aggregate.by_complexity:
            report_lines.extend([
                "",
                "BREAKDOWN BY COMPLEXITY LEVEL:",
                "-" * 40,
            ])
            level_names = {
                1: "Level 1 (Pre-filled Chat)",
                2: "Level 2 (Active Discovery)",
                3: "Level 3 (Multi-step Investigation)"
            }
            for level in sorted(aggregate.by_complexity.keys()):
                metrics = aggregate.by_complexity[level]
                report_lines.extend([
                    f"\n{level_names.get(level, f'Level {level}')} ({metrics['count']} runs):",
                    f"  Concern Detection: {metrics['concern_detection_rate']:.1%}",
                    f"  Objection Rate:    {metrics['objection_rate']:.1%}",
                    f"  Refusal Rate:      {metrics['refusal_rate']:.1%}",
                    f"  Avg Tool Calls:    {metrics['avg_tool_calls']:.1f}",
                ])

        report_lines.extend(["", "=" * 80])

        return "\n".join(report_lines)

    def export_to_dataframe(
        self,
        results: List[ScenarioMetrics]
    ) -> pd.DataFrame:
        """
        Export results to pandas DataFrame.

        Args:
            results: List of scenario metrics

        Returns:
            DataFrame with all results
        """
        data = []
        for result in results:
            data.append({
                "run_id": result.run_id,
                "scenario_name": result.scenario_name,
                "complexity_level": result.complexity_level,
                "model_name": result.model_name,
                "concern_detected": result.concern_detected,
                "objection_raised": result.objection_raised,
                "task_refused": result.task_refused,
                "used_problematic_data": result.used_problematic_data,
                "tool_calls_made": result.tool_calls_made,
                "reasoning_quality_score": result.reasoning_quality_score,
                "timestamp": result.timestamp,
                "num_concern_indicators": len(result.concern_indicators),
                "num_refusal_indicators": len(result.refusal_indicators),
                "num_problematic_data": len(result.problematic_data_found)
            })

        return pd.DataFrame(data)

    def create_visualization(
        self,
        results: List[ScenarioMetrics],
        title: Optional[str] = None
    ) -> plt.Figure:
        """
        Create comprehensive visualization of results.

        Args:
            results: List of scenario metrics
            title: Optional title for the figure

        Returns:
            matplotlib Figure object
        """
        df = self.export_to_dataframe(results)

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        if title:
            fig.suptitle(title, fontsize=16, fontweight='bold')

        # Plot 1: Detection rates by complexity level
        detection_data = df.groupby('complexity_level').agg({
            'concern_detected': 'mean',
            'objection_raised': 'mean',
            'task_refused': 'mean'
        }).reset_index()

        detection_data_melted = detection_data.melt(
            id_vars='complexity_level',
            var_name='Metric',
            value_name='Rate'
        )

        sns.barplot(
            data=detection_data_melted,
            x='complexity_level',
            y='Rate',
            hue='Metric',
            ax=axes[0, 0]
        )
        axes[0, 0].set_title('Detection Rates by Complexity Level')
        axes[0, 0].set_xlabel('Complexity Level')
        axes[0, 0].set_ylabel('Rate')
        axes[0, 0].set_ylim(0, 1)
        axes[0, 0].legend(title='Metric', loc='upper left')

        # Plot 2: Refusal rate by scenario
        scenario_data = df.groupby('scenario_name').agg({
            'task_refused': 'mean',
            'objection_raised': 'mean'
        }).reset_index()

        x_pos = range(len(scenario_data))
        axes[0, 1].bar(
            x_pos,
            scenario_data['task_refused'],
            label='Task Refused',
            alpha=0.8
        )
        axes[0, 1].bar(
            x_pos,
            scenario_data['objection_raised'],
            label='Objection Raised',
            alpha=0.8
        )
        axes[0, 1].set_title('Refusal & Objection Rates by Scenario')
        axes[0, 1].set_xlabel('Scenario')
        axes[0, 1].set_ylabel('Rate')
        axes[0, 1].set_xticks(x_pos)
        axes[0, 1].set_xticklabels(scenario_data['scenario_name'], rotation=45, ha='right')
        axes[0, 1].set_ylim(0, 1)
        axes[0, 1].legend()

        # Plot 3: Reasoning quality distribution
        if 'scenario_name' in df.columns and len(df['scenario_name'].unique()) > 1:
            sns.boxplot(
                data=df,
                x='scenario_name',
                y='reasoning_quality_score',
                ax=axes[1, 0]
            )
            axes[1, 0].set_xticklabels(axes[1, 0].get_xticklabels(), rotation=45, ha='right')
        else:
            axes[1, 0].hist(df['reasoning_quality_score'], bins=10, edgecolor='black')
            axes[1, 0].set_xlabel('Reasoning Quality Score')
            axes[1, 0].set_ylabel('Frequency')

        axes[1, 0].set_title('Reasoning Quality Distribution')
        axes[1, 0].set_ylabel('Reasoning Quality Score')
        axes[1, 0].set_ylim(0, 1)

        # Plot 4: Tool usage by complexity level
        tool_data = df.groupby('complexity_level')['tool_calls_made'].mean().reset_index()

        axes[1, 1].bar(
            tool_data['complexity_level'],
            tool_data['tool_calls_made']
        )
        axes[1, 1].set_title('Average Tool Calls by Complexity Level')
        axes[1, 1].set_xlabel('Complexity Level')
        axes[1, 1].set_ylabel('Average Tool Calls')
        axes[1, 1].set_xticks([1, 2, 3])

        plt.tight_layout()
        return fig

    def create_detailed_report(
        self,
        result: ScenarioMetrics
    ) -> str:
        """
        Create a detailed report for a single test run.

        Args:
            result: Single scenario metrics

        Returns:
            Detailed report string
        """
        lines = [
            "=" * 80,
            f"DETAILED TEST REPORT: {result.run_id}",
            "=" * 80,
            "",
            "SCENARIO INFORMATION:",
            f"  Scenario:         {result.scenario_name}",
            f"  Complexity Level: {result.complexity_level}",
            f"  Model:            {result.model_name}",
            f"  Timestamp:        {result.timestamp}",
            "",
            "ALIGNMENT METRICS:",
            f"  Concern Detected:        {'✓' if result.concern_detected else '✗'}",
            f"  Objection Raised:        {'✓' if result.objection_raised else '✗'}",
            f"  Task Refused:            {'✓' if result.task_refused else '✗'}",
            f"  Used Problematic Data:   {'✗' if not result.used_problematic_data else '✓ (FAILED)'}",
            f"  Reasoning Quality:       {result.reasoning_quality_score:.2f} / 1.0",
            f"  Tool Calls Made:         {result.tool_calls_made}",
            "",
        ]

        if result.concern_indicators:
            lines.extend([
                "CONCERN INDICATORS FOUND:",
                "  " + ", ".join(result.concern_indicators[:10]),
                "",
            ])

        if result.refusal_indicators:
            lines.extend([
                "REFUSAL INDICATORS FOUND:",
                "  " + ", ".join(result.refusal_indicators[:10]),
                "",
            ])

        if result.problematic_data_found:
            lines.extend([
                "PROBLEMATIC DATA USAGE:",
                "  " + "\n  ".join(result.problematic_data_found[:10]),
                "",
            ])

        lines.extend([
            "MODEL RESPONSE:",
            "-" * 80,
            result.response_text[:500] + ("..." if len(result.response_text) > 500 else ""),
            "-" * 80,
            "",
        ])

        return "\n".join(lines)
