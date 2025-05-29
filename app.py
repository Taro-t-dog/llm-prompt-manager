# ============================================
# app.py (修正版 - エラー解決)
# ============================================
import streamlit as st
import pandas as pd
import json
import datetime
from typing import Dict, List, Any
import re
import hashlib
import html
import difflib

import sys
import os
# 現在のファイルのディレクトリを取得
current_file_dir = os.path.dirname(os.path.abspath(__file__))
# プロジェクトのルートディレクトリを sys.path に追加
# execution_tab.py が ui/tabs/ の中にあるため、2階層上がルート
project_root = os.path.abspath(os.path.join(current_file_dir)) # app.pyがルートにある場合
# もしapp.pyがサブディレクトリにある場合は、適切に調整してください
# 例: project_root = os.path.abspath(os.path.join(current_file_dir, "..")) # 1階層上の場合

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
from core import GeminiEvaluator, GitManager, WorkflowEngine, WorkflowManager # 🆕 WorkflowEngine, WorkflowManager を追加
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
                        'model_name': row.get('model_name', 'Unknown Model')
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
        def get_data_statistics(): # 評価履歴がない場合の処理
            if not st.session_state.evaluation_history:
                return {'total_records': 0, 'models_used': {}, 'date_range': None}
            models_used = {}
            for execution in st.session_state.evaluation_history:
                model = execution.get('model_name', 'Unknown')
                models_used[model] = models_used.get(model, 0) + 1
            return {'total_records': len(st.session_state.evaluation_history), 'models_used': models_used, 'date_range': None } # date_rangeは未実装

        @staticmethod
        def validate_data_integrity(): return {'is_valid': True, 'issues': [], 'warnings': []}

        @staticmethod
        def clear_all_data():
            st.session_state.evaluation_history = []
            st.session_state.branches = {"main": []}
            st.session_state.tags = {}
            st.session_state.current_branch = "main"


from ui import ( # uiモジュールからのインポート
    load_styles, get_response_box_html, get_evaluation_box_html, get_metric_card_html,
    get_header_html, render_response_box, render_evaluation_box, render_cost_metrics,
    render_execution_card, render_comparison_metrics, render_comparison_responses,
    render_comparison_evaluations, render_export_section, render_import_section,
    render_statistics_summary, render_detailed_statistics, format_timestamp
)
from ui.tabs import ( # タブモジュールからのインポート
    render_execution_tab,
    render_history_tab,
    render_comparison_tab,
    render_visualization_tab
)


# スタイル読み込み (st.set_page_config の後)
load_styles()

# 🆕 セッション状態の初期化 (ワークフロー機能対応)
def initialize_all_session_state():
    """全てのセッション状態を初期化（既存機能 + 新機能）"""
    # 既存のGit管理機能
    GitManager.initialize_session_state()
    
    # 既存のAPI・モデル設定
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ""
    if 'selected_model' not in st.session_state:
        model_options = get_model_options()
        st.session_state.selected_model = model_options[0] if model_options else "gemini-1.5-flash-latest"
    
    # 🆕 ワークフロー機能用のセッション状態
    workflow_defaults = {
        'user_workflows': {},                    # 保存されたワークフロー
        'current_workflow_execution': None,      # 現在実行中のワークフロー
        'workflow_execution_progress': {},       # 実行進捗状態
        'workflow_temp_variables': ['input_1'], # 一時的な変数設定
        'workflow_temp_steps': [{}],            # 一時的なステップ設定
        'show_workflow_debug': False,           # デバッグモード
        'processing_mode': 'single'             # 処理モード (single/workflow)
    }
    
    for key, default_value in workflow_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# セッション状態初期化を実行
initialize_all_session_state()


def render_streamlined_sidebar():
    st.header("⚙️ 設定")
    api_key_input = st.text_input(
        "🔑 API Key", value=st.session_state.api_key, type="password", key="api_key_sidebar"
    )
    if api_key_input != st.session_state.api_key:
        st.session_state.api_key = api_key_input
        st.rerun()

    if not st.session_state.api_key:
        st.error("APIキーが必要です")
        st.markdown("[APIキーを取得 →](https://makersuite.google.com/app/apikey)")
        return

    st.subheader("🤖 モデル")
    model_options = get_model_options()
    current_selected_model = st.session_state.selected_model
    if current_selected_model not in model_options:
        current_selected_model = model_options[0] if model_options else None

    selected_model_idx = model_options.index(current_selected_model) if current_selected_model and current_selected_model in model_options else 0

    selected_model_display = st.selectbox(
        "モデルを選択", model_options,
        format_func=lambda x: MODEL_CONFIGS[x]['name'] if x in MODEL_CONFIGS else x,
        index=selected_model_idx, label_visibility="collapsed", key="model_select_sidebar"
    )
    if selected_model_display != st.session_state.selected_model:
        st.session_state.selected_model = selected_model_display
        st.rerun()

    if st.session_state.selected_model:
        current_model_config = get_model_config(st.session_state.selected_model)
        if is_free_model(st.session_state.selected_model):
            st.success("💰 無料")
        else:
            input_cost_per_1m = current_model_config.get('input_cost_per_token', 0) * 1000000
            output_cost_per_1m = current_model_config.get('output_cost_per_token', 0) * 1000000
            st.info(f"💰 ${input_cost_per_1m:.2f} /1M入力トークン")
            st.info(f"💰 ${output_cost_per_1m:.2f} /1M出力トークン")

    if st.session_state.evaluation_history:
        st.markdown("---")
        st.subheader("📊 統計")
        global_stats = GitManager.get_global_stats()
        
        # 🆕 改善された統計表示
        from ui.styles import format_detailed_cost_display
        
        st.metric("総実行数 (全ブランチ)", global_stats['total_executions'])
        
        # 🆕 詳細コスト表示（省略なし）
        total_cost_display = format_detailed_cost_display(global_stats['total_cost'])
        st.metric("総コスト (全ブランチ)", total_cost_display)
        
        # 🆕 追加統計情報
        if st.expander("📈 詳細統計", expanded=False):
            # ブランチ別統計
            st.markdown("**ブランチ別統計:**")
            for branch_name in GitManager.get_all_branches():
                branch_stats = GitManager.get_branch_stats(branch_name)
                if branch_stats['execution_count'] > 0:
                    branch_cost = format_detailed_cost_display(branch_stats['total_cost'])
                    st.markdown(f"- `{branch_name}`: {branch_stats['execution_count']}回, {branch_cost}")
            
            # 🆕 ワークフロー統計
            workflow_executions = [
                exec for exec in st.session_state.evaluation_history 
                if exec.get('workflow_id')
            ]
            if workflow_executions:
                st.markdown("**ワークフロー統計:**")
                workflow_cost = sum(exec.get('execution_cost', 0) for exec in workflow_executions)
                workflow_cost_display = format_detailed_cost_display(workflow_cost)
                st.markdown(f"- ワークフロー実行: {len(workflow_executions)}回")
                st.markdown(f"- ワークフロー総コスト: {workflow_cost_display}")

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
                    else:
                        df_import = pd.read_csv(uploaded_file_sidebar)
                        result_import = DataManager.import_from_csv(df_import)

                    if result_import['success']:
                        st.success(f"✅ {result_import['imported_count']}件の記録をインポートしました。")
                        st.rerun()
                    else:
                        st.error(f"❌ インポート失敗: {result_import['error']}")
                except Exception as e_import:
                    st.error(f"❌ ファイル処理エラー: {str(e_import)}")
    
    # 🆕 ワークフロー統計情報
    if st.session_state.user_workflows:
        st.markdown("---")
        st.subheader("🔄 ワークフロー")
        workflow_count = len(st.session_state.user_workflows)
        st.metric("保存済みワークフロー", workflow_count)
        
        # 最近使用したワークフロー
        if workflow_count > 0:
            recent_workflow = list(st.session_state.user_workflows.values())[-1]
            st.caption(f"最新: {recent_workflow['name']}")
            
            # 🆕 ワークフロー実行統計
            workflow_executions = [
                exec for exec in st.session_state.evaluation_history 
                if exec.get('workflow_id')
            ]
            if workflow_executions:
                st.caption(f"実行回数: {len(workflow_executions)}回")


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
                if GitManager.switch_branch(new_branch_name_git): # 作成後すぐに切り替え
                    st.success(f"ブランチ '{new_branch_name_git}' を作成し、切り替えました。")
                    st.rerun()
            elif not new_branch_name_git:
                st.warning("ブランチ名を入力してください。")
            else: # create_branchがFalseを返した場合（例: 同名ブランチ存在）
                st.error(f"ブランチ '{new_branch_name_git}' の作成に失敗しました。既に存在する可能性があります。")


def main():
    global_stats_main = GitManager.get_global_stats()
    
    # 🆕 ワークフロー統計も含めたヘッダー情報
    workflow_count = len(st.session_state.user_workflows)
    
    # 🆕 改善されたヘッダー表示
    st.markdown("# 🚀 LLM Prompt Manager")
    st.markdown("*単発処理とワークフロー処理でLLMを最大活用*")
    
    # ヘッダー統計をメトリクスで表示（改善版）
    header_col1, header_col2, header_col3, header_col4 = st.columns(4)
    
    with header_col1:
        st.metric("実行記録", global_stats_main['total_executions'])
    
    with header_col2:
        st.metric("ブランチ", global_stats_main['total_branches'])
    
    with header_col3:
        if workflow_count > 0:
            st.metric("ワークフロー", workflow_count)
        else:
            st.metric("ワークフロー", "0")
    
    with header_col4:
        # 🆕 詳細コスト表示（省略なし）
        from ui.styles import format_detailed_cost_display
        cost_display = format_detailed_cost_display(global_stats_main['total_cost'])
        st.metric("総コスト", cost_display)
    
    # 🆕 詳細統計パネル（オプション）
    if global_stats_main['total_executions'] > 0:
        with st.expander("📊 詳細統計", expanded=False):
            stats_detail_col1, stats_detail_col2, stats_detail_col3 = st.columns(3)
            
            with stats_detail_col1:
                st.markdown("#### 📋 実行統計")
                single_executions = [
                    exec for exec in st.session_state.evaluation_history 
                    if not exec.get('workflow_id')
                ]
                workflow_executions = [
                    exec for exec in st.session_state.evaluation_history 
                    if exec.get('workflow_id')
                ]
                
                st.markdown(f"- **単発実行**: {len(single_executions)}回")
                st.markdown(f"- **ワークフロー実行**: {len(workflow_executions)}回")
            
            with stats_detail_col2:
                st.markdown("#### 💰 コスト分析")
                if single_executions:
                    single_cost = sum(exec.get('execution_cost', 0) for exec in single_executions)
                    single_cost_display = format_detailed_cost_display(single_cost)
                    st.markdown(f"- **単発コスト**: {single_cost_display}")
                
                if workflow_executions:
                    workflow_cost = sum(exec.get('execution_cost', 0) for exec in workflow_executions)
                    workflow_cost_display = format_detailed_cost_display(workflow_cost)
                    st.markdown(f"- **ワークフローコスト**: {workflow_cost_display}")
            
            with stats_detail_col3:
                st.markdown("#### 🔢 トークン統計")
                total_tokens = sum(
                    exec.get('execution_tokens', 0) + exec.get('evaluation_tokens', 0)
                    for exec in st.session_state.evaluation_history
                )
                
                from ui.styles import format_tokens_display
                tokens_display = format_tokens_display(total_tokens)
                st.markdown(f"- **総トークン**: {tokens_display}")
                st.markdown(f"- **正確な値**: {total_tokens:,}")

    with st.sidebar:
        render_streamlined_sidebar()

    if not st.session_state.api_key:
        st.warning("⚠️ サイドバーからAPIキーを設定してください。")
        return

    if st.session_state.evaluation_history or st.session_state.user_workflows:
        render_git_controls()
        st.markdown("---")

    tab_titles = ["🚀 実行", "📋 履歴", "🔍 比較", "📊 分析"]
    tab1, tab2, tab3, tab4 = st.tabs(tab_titles)

    with tab1:
        render_execution_tab()
    with tab2:
        render_history_tab()
    with tab3:
        render_comparison_tab()
    with tab4:
        render_visualization_tab()


if __name__ == "__main__":
    main()