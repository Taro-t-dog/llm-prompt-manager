# ui/__init__.py

"""
UIモジュール
"""

from .styles import (
    load_styles,
    get_response_box_html,
    get_evaluation_box_html,
    get_metric_card_html,
    get_header_html,
    get_commit_card_style,
    get_branch_tag_html
)

from .components import (
    render_response_box,
    render_evaluation_box,
    render_cost_metrics,
    render_execution_card,
    render_prompt_details,
    render_comparison_metrics,
    render_comparison_responses,
    render_comparison_evaluations,
    render_branch_selector,
    render_execution_selector,
    render_export_section,
    render_import_section,
    render_statistics_summary,
    render_detailed_statistics,
    format_timestamp,
    # ワークフロー関連コンポーネントの追加
    render_workflow_card,
    render_workflow_progress,
    render_workflow_result_tabs,
    render_variable_substitution_help,
    render_error_details,
    render_workflow_template_selector,
    get_additional_styles, # CSSもエクスポートする場合
    render_workflow_step_card,
    render_workflow_execution_summary,
    render_workflow_live_step
)

__all__ = [
    # styles
    'load_styles',
    'get_response_box_html',
    'get_evaluation_box_html',
    'get_metric_card_html',
    'get_header_html',
    'get_commit_card_style',
    'get_branch_tag_html',
    # components
    'render_response_box',
    'render_evaluation_box',
    'render_cost_metrics',
    'render_execution_card',
    'render_prompt_details',
    'render_comparison_metrics',
    'render_comparison_responses',
    'render_comparison_evaluations',
    'render_branch_selector',
    'render_execution_selector',
    'render_export_section',
    'render_import_section',
    'render_statistics_summary',
    'render_detailed_statistics',
    'format_timestamp',
    # Workflow components added
    'render_workflow_card',
    'render_workflow_progress',
    'render_workflow_result_tabs',
    'render_variable_substitution_help',
    'render_error_details',
    'render_workflow_template_selector',
    'get_additional_styles',
    'render_workflow_step_card',
    'render_workflow_execution_summary',
    'render_workflow_live_step'
]