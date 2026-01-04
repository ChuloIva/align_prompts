#!/usr/bin/env python3
"""
Visualization script for moral philosophy evaluation results.

This script loads saved moral philosophy evaluation results and generates
comprehensive visualizations showing model preferences across different
philosophical frameworks.

Usage:
    python visualize_moral_philosophy.py <results_file.json>
    python visualize_moral_philosophy.py --latest
"""

import json
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from typing import Dict, List

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)


def load_results(results_path: Path) -> Dict:
    """Load results from JSON file."""
    with open(results_path, 'r') as f:
        return json.load(f)


def create_heatmap(df: pd.DataFrame, taxonomy: Dict, output_dir: Path, timestamp: str):
    """Create philosophical preferences heatmap."""
    # Create preference matrix
    preference_matrix = {}
    models = df['model'].unique()

    for model in models:
        model_short = model.split('/')[-1].replace(':free', '')[:25]
        preference_matrix[model_short] = {}

        model_df = df[df['model'] == model]

        for framework_key, framework in taxonomy.items():
            framework_df = model_df[model_df['framework_key'] == framework_key]

            if len(framework_df) == 0:
                preference_matrix[model_short][framework['name']] = 0
                continue

            option_a = framework['option_a']['name']
            option_b = framework['option_b']['name']

            option_a_count = len(framework_df[framework_df['philosophical_preference'] == option_a])
            option_b_count = len(framework_df[framework_df['philosophical_preference'] == option_b])

            # Score: +1 for option_a, -1 for option_b, normalized
            total = len(framework_df)
            score = (option_a_count - option_b_count) / total if total > 0 else 0
            preference_matrix[model_short][framework['name']] = score

    # Convert to DataFrame for heatmap
    heatmap_df = pd.DataFrame(preference_matrix).T

    # Plot heatmap
    plt.figure(figsize=(14, 10))
    sns.heatmap(heatmap_df, annot=True, fmt=".2f", cmap="RdYlGn", center=0,
                cbar_kws={'label': 'Preference Score'}, vmin=-1, vmax=1)
    plt.title('Model Philosophical Preferences\n(+1 = Option A, -1 = Option B)',
              fontsize=16, pad=20)
    plt.xlabel('Philosophical Framework', fontsize=12)
    plt.ylabel('Model', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    output_file = output_dir / f'philosophical_preferences_heatmap_{timestamp}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Saved heatmap: {output_file}")
    return heatmap_df


def create_framework_distributions(df: pd.DataFrame, taxonomy: Dict,
                                   output_dir: Path, timestamp: str):
    """Create per-framework distribution charts."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()

    for idx, (framework_key, framework) in enumerate(taxonomy.items()):
        ax = axes[idx]

        framework_df = df[df['framework_key'] == framework_key]

        if len(framework_df) == 0:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center')
            ax.set_title(framework['name'])
            continue

        # Count preferences by model
        model_preferences = framework_df.groupby(
            ['model', 'philosophical_preference']
        ).size().unstack(fill_value=0)

        # Shorten model names
        model_preferences.index = [
            m.split('/')[-1].replace(':free', '')[:20]
            for m in model_preferences.index
        ]

        # Plot stacked bar chart
        colors = {
            framework['option_a']['name']: '#2ecc71',
            framework['option_b']['name']: '#e74c3c',
            'unclear': '#95a5a6',
            'mixed': '#95a5a6',
            'error': '#34495e'
        }

        plot_colors = [colors.get(col, '#95a5a6') for col in model_preferences.columns]

        model_preferences.plot(kind='barh', stacked=True, ax=ax, color=plot_colors)

        ax.set_title(framework['name'], fontsize=14, fontweight='bold')
        ax.set_xlabel('Count', fontsize=11)
        ax.set_ylabel('')
        ax.legend(title='Preference', bbox_to_anchor=(1.05, 1),
                 loc='upper left', fontsize=9)
        ax.grid(axis='x', alpha=0.3)

    plt.tight_layout()
    output_file = output_dir / f'framework_distributions_{timestamp}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Saved distribution charts: {output_file}")


def create_radar_chart(df: pd.DataFrame, taxonomy: Dict,
                       output_dir: Path, timestamp: str, max_models: int = 4):
    """Create radar chart comparing model philosophical profiles."""
    models = df['model'].unique()[:max_models]

    categories = [f['name'] for f in taxonomy.values()]
    num_vars = len(categories)

    # Compute angles for radar chart
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]  # Close the plot

    fig, ax = plt.subplots(figsize=(12, 12), subplot_kw=dict(projection='polar'))

    for model in models:
        model_short = model.split('/')[-1].replace(':free', '')
        values = []

        for framework_key in taxonomy.keys():
            framework_df = df[
                (df['model'] == model) &
                (df['framework_key'] == framework_key) &
                (df['success'] == True)
            ]

            if len(framework_df) > 0:
                avg_confidence = framework_df['confidence'].mean()
                values.append(avg_confidence)
            else:
                values.append(0)

        values += values[:1]  # Close the plot

        ax.plot(angles, values, 'o-', linewidth=2, label=model_short)
        ax.fill(angles, values, alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, size=10)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], size=8)
    ax.grid(True)
    ax.set_title('Model Philosophical Confidence Scores', size=16, pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))

    plt.tight_layout()
    output_file = output_dir / f'model_radar_chart_{timestamp}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Saved radar chart: {output_file}")


def create_confidence_distribution(df: pd.DataFrame, output_dir: Path, timestamp: str):
    """Create confidence score distribution plot."""
    df_success = df[df['success'] == True]

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Overall confidence distribution
    ax1 = axes[0]
    ax1.hist(df_success['confidence'], bins=20, edgecolor='black', alpha=0.7)
    ax1.set_xlabel('Confidence Score', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    ax1.set_title('Overall Confidence Distribution', fontsize=14, fontweight='bold')
    ax1.axvline(df_success['confidence'].mean(), color='red', linestyle='--',
                linewidth=2, label=f'Mean: {df_success["confidence"].mean():.3f}')
    ax1.legend()
    ax1.grid(alpha=0.3)

    # Confidence by framework
    ax2 = axes[1]
    framework_names = [df_success[df_success['framework_key'] == k]['framework_name'].iloc[0]
                      if len(df_success[df_success['framework_key'] == k]) > 0 else k
                      for k in df_success['framework_key'].unique()]

    confidence_by_framework = [
        df_success[df_success['framework_key'] == k]['confidence'].values
        for k in df_success['framework_key'].unique()
    ]

    bp = ax2.boxplot(confidence_by_framework, labels=framework_names, patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor('#3498db')
        patch.set_alpha(0.7)

    ax2.set_xlabel('Philosophical Framework', fontsize=12)
    ax2.set_ylabel('Confidence Score', fontsize=12)
    ax2.set_title('Confidence by Framework', fontsize=14, fontweight='bold')
    ax2.tick_params(axis='x', rotation=45)
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    output_file = output_dir / f'confidence_distributions_{timestamp}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Saved confidence distributions: {output_file}")


def create_summary_table(df: pd.DataFrame, taxonomy: Dict, output_dir: Path, timestamp: str):
    """Create summary statistics table."""
    summary_data = []

    for framework_key, framework in taxonomy.items():
        framework_df = df[df['framework_key'] == framework_key]

        if len(framework_df) == 0:
            continue

        option_a = framework['option_a']['name']
        option_b = framework['option_b']['name']

        option_a_count = len(framework_df[framework_df['philosophical_preference'] == option_a])
        option_b_count = len(framework_df[framework_df['philosophical_preference'] == option_b])
        unclear_count = len(framework_df[framework_df['philosophical_preference'].isin(['unclear', 'mixed'])])
        total = len(framework_df)

        summary_data.append({
            'Framework': framework['name'],
            f'{option_a} (%)': f'{option_a_count/total*100:.1f}%',
            f'{option_b} (%)': f'{option_b_count/total*100:.1f}%',
            'Unclear (%)': f'{unclear_count/total*100:.1f}%',
            'Avg Confidence': f'{framework_df["confidence"].mean():.3f}',
            'Total': total
        })

    summary_df = pd.DataFrame(summary_data)

    # Save as CSV
    csv_file = output_dir / f'summary_table_{timestamp}.csv'
    summary_df.to_csv(csv_file, index=False)

    print(f"✓ Saved summary table: {csv_file}")
    print("\nSummary Statistics:")
    print(summary_df.to_string(index=False))

    return summary_df


def generate_report(results_data: Dict, df: pd.DataFrame, output_dir: Path, timestamp: str):
    """Generate text summary report."""
    metadata = results_data['metadata']
    taxonomy = metadata['taxonomy']

    report = []
    report.append("=" * 80)
    report.append("MORAL PHILOSOPHY EVALUATION REPORT")
    report.append("=" * 80)
    report.append("")
    report.append(f"Evaluation Timestamp: {metadata['timestamp']}")
    report.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Models Tested: {len(metadata['models_tested'])}")
    report.append(f"Scenarios Tested: {len(metadata['scenarios_tested'])}")
    report.append(f"Total Results: {metadata['total_results']}")
    report.append(f"Successful Results: {len(df[df['success'] == True])}")
    report.append(f"Failed Results: {len(df[df['success'] == False])}")
    report.append("")

    report.append("=" * 80)
    report.append("MODELS TESTED")
    report.append("=" * 80)
    for model in metadata['models_tested']:
        report.append(f"  - {model}")
    report.append("")

    report.append("=" * 80)
    report.append("KEY FINDINGS BY FRAMEWORK")
    report.append("=" * 80)

    df_success = df[df['success'] == True]

    for framework_key, framework in taxonomy.items():
        framework_df = df_success[df_success['framework_key'] == framework_key]

        if len(framework_df) == 0:
            continue

        report.append("")
        report.append(framework['name'])
        report.append("-" * 80)
        report.append(f"Description: {framework['description']}")
        report.append("")

        option_a = framework['option_a']['name']
        option_b = framework['option_b']['name']

        option_a_count = len(framework_df[framework_df['philosophical_preference'] == option_a])
        option_b_count = len(framework_df[framework_df['philosophical_preference'] == option_b])
        unclear_count = len(framework_df[framework_df['philosophical_preference'].isin(['unclear', 'mixed'])])
        total = len(framework_df)

        report.append(f"Overall Distribution:")
        report.append(f"  {option_a}: {option_a_count}/{total} ({option_a_count/total*100:.1f}%)")
        report.append(f"  {option_b}: {option_b_count}/{total} ({option_b_count/total*100:.1f}%)")
        report.append(f"  Unclear/Mixed: {unclear_count}/{total} ({unclear_count/total*100:.1f}%)")
        report.append(f"  Average Confidence: {framework_df['confidence'].mean():.3f}")
        report.append("")

        # Model breakdown
        report.append("Model Preferences:")
        for model in metadata['models_tested']:
            model_framework_df = framework_df[framework_df['model'] == model]
            if len(model_framework_df) > 0:
                model_short = model.split('/')[-1].replace(':free', '')
                pref_a = len(model_framework_df[model_framework_df['philosophical_preference'] == option_a])
                pref_b = len(model_framework_df[model_framework_df['philosophical_preference'] == option_b])
                total_model = len(model_framework_df)

                if pref_a > pref_b:
                    report.append(f"  {model_short:30s}: {option_a} ({pref_a}/{total_model})")
                elif pref_b > pref_a:
                    report.append(f"  {model_short:30s}: {option_b} ({pref_b}/{total_model})")
                else:
                    report.append(f"  {model_short:30s}: Mixed/Unclear")

    report.append("")
    report.append("=" * 80)
    report.append("OVERALL MODEL RANKINGS")
    report.append("=" * 80)
    report.append("")
    report.append("Average Confidence by Model:")

    model_confidence = df_success.groupby('model')['confidence'].mean().sort_values(ascending=False)
    for i, (model, conf) in enumerate(model_confidence.items(), 1):
        model_short = model.split('/')[-1].replace(':free', '')
        report.append(f"  {i}. {model_short:30s}: {conf:.3f}")

    report.append("")
    report.append("=" * 80)
    report.append(f"Visualizations saved to: {output_dir}")
    report.append("=" * 80)

    report_text = "\n".join(report)

    # Save report
    report_file = output_dir / f'evaluation_report_{timestamp}.txt'
    with open(report_file, 'w') as f:
        f.write(report_text)

    print(f"\n✓ Saved report: {report_file}")
    print("\n" + report_text)


def main():
    parser = argparse.ArgumentParser(
        description='Visualize moral philosophy evaluation results'
    )
    parser.add_argument(
        'results_file',
        nargs='?',
        type=str,
        help='Path to results JSON file'
    )
    parser.add_argument(
        '--latest',
        action='store_true',
        help='Use the latest results file in results/moral_philosophy/'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory for visualizations (default: same as results file)'
    )

    args = parser.parse_args()

    # Determine results file
    if args.latest:
        results_dir = Path('../results/moral_philosophy')
        if not results_dir.exists():
            print(f"Error: Results directory not found: {results_dir}")
            return

        # Find latest results file
        results_files = list(results_dir.glob('moral_philosophy_results_*.json'))
        if not results_files:
            print(f"Error: No results files found in {results_dir}")
            return

        results_file = max(results_files, key=lambda p: p.stat().st_mtime)
        print(f"Using latest results file: {results_file}")
    elif args.results_file:
        results_file = Path(args.results_file)
        if not results_file.exists():
            print(f"Error: Results file not found: {results_file}")
            return
    else:
        parser.print_help()
        return

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = results_file.parent

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load results
    print(f"\nLoading results from: {results_file}")
    results_data = load_results(results_file)

    # Convert to DataFrame
    df = pd.DataFrame(results_data['results'])
    df_success = df[df['success'] == True]

    print(f"Total results: {len(df)}")
    print(f"Successful: {len(df_success)}")
    print(f"Failed: {len(df) - len(df_success)}")

    # Get taxonomy
    taxonomy = results_data['metadata']['taxonomy']

    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create visualizations
    print("\nGenerating visualizations...")
    print("-" * 80)

    create_heatmap(df_success, taxonomy, output_dir, timestamp)
    create_framework_distributions(df_success, taxonomy, output_dir, timestamp)
    create_radar_chart(df_success, taxonomy, output_dir, timestamp)
    create_confidence_distribution(df_success, output_dir, timestamp)
    create_summary_table(df_success, taxonomy, output_dir, timestamp)
    generate_report(results_data, df, output_dir, timestamp)

    print("\n" + "=" * 80)
    print("✓ Visualization complete!")
    print(f"Output directory: {output_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
