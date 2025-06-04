# ============================================
# app.py (修正版 - エラー解決 + OpenAI対応)
# ============================================
import streamlit as st
import pandas as pd
import json
import datetime
from typing import Dict, List, Any, Union # Added Union
import re
import hashlib
import html
import difflib

import sys
import os
# 現在のファイルのディレクトリを取得
current_file_dir = os.path.dirname(os.path.abspath(__file__))
# プロジェクトのルートディレクトリを sys.path に追加
project_root = os.path.abspath(os.path.join(current_file_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ページ設定 (これが最初のStreamlitコマンドである必要があります)
st.set_page_config(
    page_title="LLM Prompt Manager",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ↓↓↓ st.set_page_config() の後に他のインポートや処理を配置 ↓↓↓

from config import MODEL_CONFIGS, get_model_config, get_model_options, get_model_labels, is_free_model
from core import GeminiEvaluator, OpenAIEvaluator, GitManager, WorkflowEngine, WorkflowManager # Added OpenAIEvaluator
from core.evaluator import GeminiEvaluator # Explicit for typing if needed elsewhere
from core.openai_evaluator import OpenAIEvaluator # Explicit for typing

try:
    from core import DataManager
except ImportError:
    # DataManagerが見つからない場合のフォールバック (st.session_stateへのアクセスはメソッド内なのでOK)
    class DataManager:
        @staticmethod
        def export_to_json(include_metadata=True):
            history_data = {
                'evaluation_history': st.session_state.evaluation_history,
                'branches': st.session_state.branches,
                'tags': st.session_state.tags,
                'current_branch': st.session_state.current_branch
            }
            if include_metadata:
                history_data['export_timestamp'] = datetime.datetime.now().isoformat()
            return json.dumps(history_data, default=str, ensure_ascii=False, indent=2)

        @staticmethod
        def import_from_json(json_data):
            try:
                if isinstance(json_data, str):
                    history_data = json.loads(json_data)
                else:
                    history_data = json_data
                st.session_state.evaluation_history = history_data.get('evaluation_history', [])
                st.session_state.branches = history_data.get('branches', {"main": []})
                st.session_state.tags = history_data.get('tags', {})
                st.session_state.current_branch = history_data.get('current_branch', 'main')
                return {'success': True, 'imported_count': len(st.session_state.evaluation_history), 'export_timestamp': history_data.get('export_timestamp', 'Unknown')}
            except Exception as e:
                return {'success': False, 'error': str(e), 'imported_count': 0}

        @staticmethod
        def export_to_csv():
            if not st.session_state.evaluation_history: return ""
            df = pd.DataFrame(st.session_state.evaluation_history)
            if 'timestamp' in df.columns:
                df['timestamp'] = df['timestamp'].apply(lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x))
            return df.to_csv(index=False, encoding='utf-8-sig')

        @staticmethod
        def import_from_csv(df):
            try:
                imported_records = []
                for _, row in df.iterrows():
                    record = {
                        'timestamp': row.get('timestamp', datetime.datetime.now().isoformat()),
                        'execution_mode': row.get('execution_mode', '単一プロンプト'),
                        'final_prompt': row.get('final_prompt', ''), 'criteria': row.get('criteria', ''),
                        'response': row.get('response', ''), 'evaluation': row.get('evaluation', ''),
                        'execution_tokens': int(row.get('execution_tokens', 0)),
                        'evaluation_tokens': int(row.get('evaluation_tokens', 0)),
                        'execution_cost': float(row.get('execution_cost', 0.0)),
                        'evaluation_cost': float(row.get('evaluation_cost', 0.0)),
                        'total_cost': float(row.get('total_cost', 0.0)),
                        'commit_hash': row.get('commit_hash', hashlib.md5(str(row.to_dict()).encode()).hexdigest()[:8]),
                        'commit_message': row.get('commit_message', 'CSVインポート'),
                        'branch': row.get('branch', st.session_state.current_branch),
                        'model_name': row.get('model_name', 'Unknown Model'),
                        'api_provider': row.get('api_provider', 'gemini') # Add provider for CSV
                    }
                    imported_records.append(record)
                st.session_state.evaluation_history.extend(imported_records)
                for record in imported_records:
                    branch_name = record['branch']
                    if branch_name not in st.session_state.branches: st.session_state.branches[branch_name] = []
                    st.session_state.branches[branch_name].append(record)
                return {'success': True, 'imported_count': len(imported_records)}
            except Exception as e:
                return {'success': False, 'error': str(e), 'imported_count': 0}

        @staticmethod
        def get_file_suggestion(file_type="json"):
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            record_count = len(st.session_state.evaluation_history)
            if file_type.lower() == "json": return f"prompt_history_{timestamp}_{record_count}records.json"
            elif file_type.lower() == "csv": return f"prompt_execution_history_{timestamp}_{record_count}records.csv"
            else: return f"prompt_data_{timestamp}.{file_type}"

        @staticmethod
        def get_data_statistics():
            if not st.session_state.evaluation_history:
                return {'total_records': 0, 'models_used': {}, 'date_range': None}
            models_used = {}
            for execution in st.session_state.evaluation_history:
                model = execution.get('model_name', 'Unknown')
                provider = execution.get('api_provider', 'gemini')
                display_name = f"{model} ({provider.capitalize()})"
                models_used[display_name] = models_used.get(display_name, 0) + 1
            return {'total_records': len(st.session_state.evaluation_history), 'models_used': models_used, 'date_range': None }

        @staticmethod
        def validate_data_integrity(): return {'is_valid': True, 'issues': [], 'warnings': []}

        @staticmethod
        def clear_all_data():
            st.session_state.evaluation_history = []
            st.session_state.branches = {"main": []}
            st.session_state.tags = {}
            st.session_state.current_branch = "main"


from ui import (
    load_styles, get_response_box_html, get_evaluation_box_html, get_metric_card_html,
    get_header_html, render_response_box, render_evaluation_box, render_cost_metrics,
    render_execution_card, render_comparison_metrics, render_comparison_responses,
    render_comparison_evaluations, render_export_section, render_import_section,
    render_statistics_summary, render_detailed_statistics, format_timestamp
)
from ui.tabs import (
    render_execution_tab,
    render_history_tab,
    render_comparison_tab,
    render_visualization_tab
)
from ui.styles import format_detailed_cost_display, format_tokens_display # Direct import for main app usage

# スタイル読み込み
load_styles()

# セッション状態の初期化
def initialize_all_session_state():
    GitManager.initialize_session_state()
    
    if 'api_key' not in st.session_state: # Gemini API Key
        st.session_state.api_key = ""
    if 'openai_api_key' not in st.session_state: # OpenAI API Key
        st.session_state.openai_api_key = ""

    if 'selected_model' not in st.session_state:
        model_options = get_model_options() # Returns list of model_ids
        # Default to a Gemini model if available, else first option
        default_model_candidate = next((m for m in model_options if get_model_config(m).get('api_provider') == 'gemini'), None)
        if not default_model_candidate and model_options:
            default_model_candidate = model_options[0]
        elif not model_options: # Should not happen
             default_model_candidate = "gemini-1.5-flash" 

        st.session_state.selected_model = default_model_candidate

    workflow_defaults = {
        'user_workflows': {}, 'current_workflow_execution': None,
        'workflow_execution_progress': {}, 'workflow_temp_variables': ['input_1'],
        'workflow_temp_steps': [{}], 'show_workflow_debug': False,
        'processing_mode': 'single'
    }
    for key, default_value in workflow_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

initialize_all_session_state()


def render_streamlined_sidebar():
    st.header("⚙️ 設定")
    
    st.subheader("🔑 APIキー")
    # Gemini API Key
    gemini_api_key_input = st.text_input(
        "Gemini API Key", value=st.session_state.api_key, type="password", key="api_key_sidebar_gemini",
        help="Google AI Studio (Makersuite) から取得したAPIキー"
    )
    if gemini_api_key_input != st.session_state.api_key:
        st.session_state.api_key = gemini_api_key_input
        # No rerun here, allow user to input both keys before potential reruns

    # OpenAI API Key
    openai_api_key_input = st.text_input(
        "OpenAI API Key", value=st.session_state.openai_api_key, type="password", key="api_key_sidebar_openai",
        help="OpenAI Platform から取得したAPIキー"
    )
    if openai_api_key_input != st.session_state.openai_api_key:
        st.session_state.openai_api_key = openai_api_key_input
    
    # Dynamic API key check based on selected model will be in main()

    st.subheader("🤖 モデル選択")
    model_options = get_model_options() # List of model_ids
    model_display_labels = get_model_labels() # List of display names like "Gemini 1.5 Flash (Gemini)"

    current_selected_model_id = st.session_state.selected_model
    
    # Ensure current_selected_model_id is valid, if not, default
    if current_selected_model_id not in model_options:
        current_selected_model_id = model_options[0] if model_options else None
        st.session_state.selected_model = current_selected_model_id

    selected_model_idx = 0
    if current_selected_model_id and current_selected_model_id in model_options:
        selected_model_idx = model_options.index(current_selected_model_id)

    # Use model_options (IDs) for selectbox, and model_display_labels for format_func
    selected_model_id_from_ui = st.selectbox(
        "モデルを選択", model_options,
        format_func=lambda x: model_display_labels[model_options.index(x)] if x in model_options else x, # Show pretty name
        index=selected_model_idx, label_visibility="collapsed", key="model_select_sidebar"
    )
    if selected_model_id_from_ui != st.session_state.selected_model:
        st.session_state.selected_model = selected_model_id_from_ui
        st.rerun() # Rerun to update cost info and evaluator instance

    if st.session_state.selected_model:
        current_model_config = get_model_config(st.session_state.selected_model)
        provider_display = current_model_config.get('api_provider', 'N/A').capitalize()
        st.caption(f"プロバイダー: {provider_display}")

        if is_free_model(st.session_state.selected_model): # is_free_model checks costs or 'free_tier' flag
            st.success("💰 無料または無料ティア対象の可能性")
        else:
            input_cost_per_1m = current_model_config.get('input_cost_per_token', 0) * 1000000
            output_cost_per_1m = current_model_config.get('output_cost_per_token', 0) * 1000000
            st.info(f"💰 ${input_cost_per_1m:.2f} /1M入力トークン")
            st.info(f"💰 ${output_cost_per_1m:.2f} /1M出力トークン")

    if st.session_state.evaluation_history:
        st.markdown("---")
        st.subheader("📊 統計")
        global_stats = GitManager.get_global_stats()
        st.metric("総実行数 (全ブランチ)", global_stats['total_executions'])
        total_cost_display = format_detailed_cost_display(global_stats['total_cost'])
        st.metric("総コスト (全ブランチ)", total_cost_display)
        
        if st.expander("📈 詳細統計", expanded=False):
            st.markdown("**ブランチ別統計:**")
            for branch_name_stats in GitManager.get_all_branches(): # Renamed var
                branch_stats_val = GitManager.get_branch_stats(branch_name_stats) # Renamed var
                if branch_stats_val['execution_count'] > 0:
                    branch_cost_str = format_detailed_cost_display(branch_stats_val['total_cost']) # Renamed var
                    st.markdown(f"- `{branch_name_stats}`: {branch_stats_val['execution_count']}回, {branch_cost_str}")
            
            workflow_executions = [exec_item for exec_item in st.session_state.evaluation_history if exec_item.get('workflow_id')] # Renamed var
            if workflow_executions:
                st.markdown("**ワークフロー統計:**")
                workflow_cost_val = sum(exec_item.get('total_cost', 0) for exec_item in workflow_executions) # Use total_cost for workflow summary
                workflow_cost_display_str = format_detailed_cost_display(workflow_cost_val) # Renamed var
                st.markdown(f"- ワークフロー実行: {len(workflow_executions)}回")
                st.markdown(f"- ワークフロー総コスト: {workflow_cost_display_str}")

        st.markdown("---")
        st.subheader("💾 データ管理")
        export_col1, export_col2 = st.columns(2)
        with export_col1:
            if st.button("📤 JSONエクスポート", use_container_width=True, key="export_json_sidebar"):
                json_data_export = DataManager.export_to_json()
                filename_json = DataManager.get_file_suggestion("json")
                st.download_button("📥 ダウンロード", json_data_export, filename_json, "application/json", key="json_dl_sidebar")
        with export_col2:
            if st.button("📊 CSVエクスポート", use_container_width=True, key="export_csv_sidebar"):
                csv_data_export = DataManager.export_to_csv()
                filename_csv = DataManager.get_file_suggestion("csv")
                st.download_button("📥 ダウンロード", csv_data_export, filename_csv, "text/csv", key="csv_dl_sidebar")

        uploaded_file_sidebar = st.file_uploader("📂 インポート (JSON/CSV)", type=["json", "csv"], key="import_file_sidebar")
        if uploaded_file_sidebar:
            if st.button("⬆️ 選択したファイルをインポート", use_container_width=True, key="import_button_sidebar"):
                try:
                    if uploaded_file_sidebar.name.endswith('.json'):
                        data_import = json.load(uploaded_file_sidebar)
                        result_import = DataManager.import_from_json(data_import)
                    else: # CSV
                        df_import = pd.read_csv(uploaded_file_sidebar)
                        result_import = DataManager.import_from_csv(df_import)

                    if result_import['success']:
                        st.success(f"✅ {result_import['imported_count']}件の記録をインポートしました。")
                        st.rerun()
                    else:
                        st.error(f"❌ インポート失敗: {result_import['error']}")
                except Exception as e_import:
                    st.error(f"❌ ファイル処理エラー: {str(e_import)}")
    
    if st.session_state.user_workflows:
        st.markdown("---")
        st.subheader("🔄 ワークフロー")
        workflow_count = len(st.session_state.user_workflows)
        st.metric("保存済みワークフロー", workflow_count)
        if workflow_count > 0:
            recent_workflow = list(st.session_state.user_workflows.values())[-1]
            st.caption(f"最新: {recent_workflow['name']}")
            workflow_executions_sidebar = [exec_item for exec_item in st.session_state.evaluation_history if exec_item.get('workflow_id')] # Renamed var
            if workflow_executions_sidebar:
                st.caption(f"実行回数: {len(workflow_executions_sidebar)}回")

def render_git_controls():
    st.subheader("🌿 ブランチ管理")
    git_col1, git_col2 = st.columns(2)
    with git_col1:
        st.write("**現在のブランチ**")
        available_branches = GitManager.get_all_branches()
        current_branch_git = GitManager.get_current_branch()
        current_branch_idx = available_branches.index(current_branch_git) if current_branch_git in available_branches else 0
        selected_branch_git = st.selectbox(
            "ブランチ", available_branches, index=current_branch_idx,
            label_visibility="collapsed", key="branch_select_main"
        )
        if selected_branch_git != current_branch_git:
            if GitManager.switch_branch(selected_branch_git):
                st.rerun()
    with git_col2:
        st.write("**新しいブランチを作成**")
        new_branch_name_git = st.text_input("新しいブランチ名", label_visibility="collapsed", key="new_branch_name_main")
        if st.button("🌱 作成", use_container_width=True, key="create_branch_main"):
            if new_branch_name_git and GitManager.create_branch(new_branch_name_git):
                if GitManager.switch_branch(new_branch_name_git):
                    st.success(f"ブランチ '{new_branch_name_git}' を作成し、切り替えました。")
                    st.rerun()
            elif not new_branch_name_git:
                st.warning("ブランチ名を入力してください。")
            else:
                st.error(f"ブランチ '{new_branch_name_git}' の作成に失敗しました。既に存在する可能性があります。")


def main():
    global_stats_main = GitManager.get_global_stats()
    workflow_count_main = len(st.session_state.user_workflows) # Renamed var
    
    st.markdown("# 🚀 LLM Prompt Manager")
    st.markdown("*単発処理とワークフロー処理でLLMを最大活用*")
    
    header_col1, header_col2, header_col3, header_col4 = st.columns(4)
    with header_col1: st.metric("実行記録", global_stats_main['total_executions'])
    with header_col2: st.metric("ブランチ", global_stats_main['total_branches'])
    with header_col3: st.metric("ワークフロー", workflow_count_main)
    with header_col4:
        cost_display_main = format_detailed_cost_display(global_stats_main['total_cost']) # Renamed var
        st.metric("総コスト", cost_display_main)
    
    if global_stats_main['total_executions'] > 0:
        with st.expander("📊 詳細統計", expanded=False):
            stats_detail_col1, stats_detail_col2, stats_detail_col3 = st.columns(3)
            with stats_detail_col1:
                st.markdown("#### 📋 実行統計")
                single_executions = [exec_item for exec_item in st.session_state.evaluation_history if not exec_item.get('workflow_id')]
                workflow_executions_main = [exec_item for exec_item in st.session_state.evaluation_history if exec_item.get('workflow_id')] # Renamed var
                st.markdown(f"- **単発実行**: {len(single_executions)}回")
                st.markdown(f"- **ワークフロー実行**: {len(workflow_executions_main)}回")
            with stats_detail_col2:
                st.markdown("#### 💰 コスト分析")
                if single_executions:
                    single_cost_val = sum(exec_item.get('total_cost', 0) for exec_item in single_executions) # Use total_cost for consistency
                    single_cost_display_str = format_detailed_cost_display(single_cost_val) # Renamed var
                    st.markdown(f"- **単発コスト**: {single_cost_display_str}")
                if workflow_executions_main:
                    workflow_cost_main_val = sum(exec_item.get('total_cost', 0) for exec_item in workflow_executions_main) # Use total_cost
                    workflow_cost_display_main_str = format_detailed_cost_display(workflow_cost_main_val) # Renamed var
                    st.markdown(f"- **ワークフローコスト**: {workflow_cost_display_main_str}")
            with stats_detail_col3:
                st.markdown("#### 🔢 トークン統計")
                total_tokens_main_val = sum( # Renamed var
                    exec_item.get('execution_tokens', 0) + exec_item.get('evaluation_tokens', 0)
                    for exec_item in st.session_state.evaluation_history
                )
                tokens_display_main_str = format_tokens_display(total_tokens_main_val) # Renamed var
                st.markdown(f"- **総トークン**: {tokens_display_main_str}")
                st.markdown(f"- **正確な値**: {total_tokens_main_val:,}")

    with st.sidebar:
        render_streamlined_sidebar()

    # API Key and Evaluator Setup
    evaluator: Union[GeminiEvaluator, OpenAIEvaluator, None] = None # Type hint for clarity
    selected_model_cfg = get_model_config(st.session_state.selected_model)
    api_provider = selected_model_cfg.get('api_provider', 'gemini')

    api_key_ok = False
    if api_provider == 'openai':
        if st.session_state.openai_api_key:
            evaluator = OpenAIEvaluator(st.session_state.openai_api_key, selected_model_cfg)
            api_key_ok = True
        else:
            st.warning("⚠️ OpenAIモデルが選択されていますが、サイドバーからOpenAI APIキーが設定されていません。")
    else: # gemini (default)
        if st.session_state.api_key:
            evaluator = GeminiEvaluator(st.session_state.api_key, selected_model_cfg)
            api_key_ok = True
        else:
            st.warning("⚠️ Geminiモデルが選択されていますが、サイドバーからGemini APIキーが設定されていません。")
            
    if not api_key_ok:
        st.error("選択されたモデルに対応するAPIキーを設定してください。機能が制限されます。")
        # Potentially return early or disable tabs if evaluator is crucial for all.
        # For now, execution tab will handle its own checks if evaluator is None.

    if st.session_state.evaluation_history or st.session_state.user_workflows:
        render_git_controls()
        st.markdown("---")

    tab_titles = ["🚀 実行", "📋 履歴", "🔍 比較", "📊 分析"]
    tab1, tab2, tab3, tab4 = st.tabs(tab_titles)

    with tab1:
        if evaluator: # Only render if evaluator is successfully created
            render_execution_tab(evaluator) # Pass the evaluator instance
        else:
            st.error(f"実行タブは、選択されたモデル ({selected_model_cfg.get('name')}) のAPIキーが設定されるまで利用できません。")
    with tab2:
        render_history_tab()
    with tab3:
        render_comparison_tab()
    with tab4:
        render_visualization_tab()

if __name__ == "__main__":
    main()