# ui/__init__.py

"""
UIモジュール
このファイルは、uiパッケージ内のコンポーネントとスタイルを
アプリケーションの他の部分から簡単にインポートできるようにするための窓口です。
"""
import sys
import os

# パスを追加して、uiパッケージ内のモジュールを正しく解決できるようにする
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# スタイル関連の関数をインポート
from .styles import (
    load_styles,
    get_response_box_html,
    get_evaluation_box_html,
    get_metric_card_html,
    get_header_html,
    get_commit_card_style,
    get_branch_tag_html,
    format_detailed_cost_display,
    format_tokens_display
)

# UIコンポーネント関数をインポート
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
    render_workflow_card,
    render_workflow_progress,
    render_workflow_result_tabs,
    render_variable_substitution_help,
    render_error_details,
    render_workflow_template_selector,
    render_workflow_step_card,
    render_workflow_execution_summary,
    render_workflow_live_step
)

# タブ描画関数をインポート
from .tabs import (
    render_execution_tab,
    render_history_tab,
    render_comparison_tab,
    render_visualization_tab
)


# `from ui import *` でインポートされる対象を定義する
__all__ = [
    # styles.pyから
    'load_styles',
    'get_response_box_html',
    'get_evaluation_box_html',
    'get_metric_card_html',
    'get_header_html',
    'get_commit_card_style',
    'get_branch_tag_html',
    'format_detailed_cost_display',
    'format_tokens_display',
    
    # components.pyから
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
    'render_workflow_card',
    'render_workflow_progress',
    'render_workflow_result_tabs',
    'render_variable_substitution_help',
    'render_error_details',
    'render_workflow_template_selector',
    'render_workflow_step_card',
    'render_workflow_execution_summary',
    'render_workflow_live_step',

    # tabs/__init__.pyから
    'render_execution_tab',
    'render_history_tab',
    'render_comparison_tab',
    'render_visualization_tab'
]