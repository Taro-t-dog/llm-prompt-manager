# ============================================
# app.py (ImportError修正)
# ============================================
import streamlit as st
import pandas as pd
import json
import datetime
from typing import Dict, List, Any, Union
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

from config import get_model_config, get_model_options, get_model_labels, is_free_model
from core import GeminiEvaluator, OpenAIEvaluator, GitManager, WorkflowEngine, WorkflowManager
from core.data_manager import DataManager

from ui import (
    load_styles,
    render_response_box,
    render_evaluation_box,
    render_execution_card,
    render_execution_tab,
    render_history_tab,
    render_comparison_tab,
    render_visualization_tab,
    format_detailed_cost_display,
    format_tokens_display
)

# スタイル読み込み
load_styles()

# セッション状態の初期化
def initialize_all_session_state():
    GitManager.initialize_session_state()
    
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ""
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = ""

    if 'selected_model' not in st.session_state:
        model_options = get_model_options()
        default_model_candidate = next((m for m in model_options if get_model_config(m).get('api_provider', 'gemini') == 'gemini'), None)
        if not default_model_candidate and model_options:
            default_model_candidate = model_options[0]
        elif not model_options:
             default_model_candidate = "gemini-1.5-flash-latest"

        st.session_state.selected_model = default_model_candidate

    workflow_defaults = {
        'user_workflows': {}, 'current_workflow_execution': None, 'workflow_execution_progress': {},
        'workflow_temp_variables': ['input_1'], 'workflow_temp_steps': [{}], 'show_workflow_debug': False,
        'processing_mode': 'single'
    }
    for key, default_value in workflow_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

initialize_all_session_state()


def render_streamlined_sidebar():
    st.header("⚙️ 設定")
    
    st.subheader("🔑 APIキー")
    gemini_api_key = st.text_input("Gemini API Key", value=st.session_state.api_key, type="password", help="Google AI Studio から取得したAPIキー")
    if gemini_api_key != st.session_state.api_key:
        st.session_state.api_key = gemini_api_key

    openai_api_key = st.text_input("OpenAI API Key", value=st.session_state.openai_api_key, type="password", help="OpenAI Platform から取得したAPIキー")
    if openai_api_key != st.session_state.openai_api_key:
        st.session_state.openai_api_key = openai_api_key
    
    st.subheader("🤖 モデル選択")
    model_options = get_model_options()
    model_labels = get_model_labels()
    current_model_id = st.session_state.selected_model
    
    if current_model_id not in model_options:
        current_model_id = model_options[0] if model_options else None
        st.session_state.selected_model = current_model_id

    selected_model_idx = model_options.index(current_model_id) if current_model_id and current_model_id in model_options else 0
    
    selected_model_id = st.selectbox("モデルを選択", model_options, format_func=lambda x: model_labels[model_options.index(x)] if x in model_options else x, index=selected_model_idx, label_visibility="collapsed")
    if selected_model_id != st.session_state.selected_model:
        st.session_state.selected_model = selected_model_id
        st.rerun()

    if st.session_state.selected_model:
        config = get_model_config(st.session_state.selected_model)
        provider = config.get('api_provider', 'gemini').capitalize()
        st.caption(f"プロバイダー: {provider}")

        if is_free_model(st.session_state.selected_model):
            st.success("💰 無料または無料ティア対象の可能性")
        else:
            input_cost = config.get('input_cost_per_token', 0) * 1000000
            output_cost = config.get('output_cost_per_token', 0) * 1000000
            st.info(f"💰 ${input_cost:.2f} / 1M入力トークン")
            st.info(f"💰 ${output_cost:.2f} / 1M出力トークン")

    if st.session_state.evaluation_history:
        st.markdown("---")
        st.subheader("📊 統計")
        stats = GitManager.get_global_stats()
        st.metric("総実行数 (全ブランチ)", stats['total_executions'])
        st.metric("総コスト (全ブランチ)", format_detailed_cost_display(stats['total_cost']))
        
        if st.expander("📈 詳細統計", expanded=False):
            st.markdown("**ブランチ別統計:**")
            for branch in GitManager.get_all_branches():
                branch_stats = GitManager.get_branch_stats(branch)
                if branch_stats['execution_count'] > 0:
                    st.markdown(f"- `{branch}`: {branch_stats['execution_count']}回, {format_detailed_cost_display(branch_stats['total_cost'])}")
        
        st.markdown("---")
        st.subheader("💾 データ管理")
        c1, c2 = st.columns(2)
        if c1.button("📤 JSONエクスポート", use_container_width=True):
            st.download_button("📥 ダウンロード", DataManager.export_to_json(), DataManager.get_file_suggestion("json"), "application/json")
        if c2.button("📊 CSVエクスポート", use_container_width=True):
            st.download_button("📥 ダウンロード", DataManager.export_to_csv(), DataManager.get_file_suggestion("csv"), "text/csv")

        uploaded_file = st.file_uploader("📂 インポート (JSON/CSV)", type=["json", "csv"])
        if uploaded_file:
            if st.button("⬆️ インポート実行", use_container_width=True):
                try:
                    if uploaded_file.name.endswith('.json'):
                        result = DataManager.import_from_json(json.load(uploaded_file))
                    else:
                        result = DataManager.import_from_csv(pd.read_csv(uploaded_file))
                    if result.get('success'): st.success(f"✅ {result.get('imported_count', 0)}件の記録をインポートしました。"); st.rerun()
                    else: st.error(f"❌ インポート失敗: {result.get('error', '不明なエラー')}")
                except Exception as e: st.error(f"❌ ファイル処理エラー: {e}")

def render_git_controls():
    st.subheader("🌿 ブランチ管理")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**現在のブランチ**")
        branches = GitManager.get_all_branches()
        current_branch = GitManager.get_current_branch()
        idx = branches.index(current_branch) if current_branch in branches else 0
        selected = st.selectbox("ブランチ", branches, index=idx, label_visibility="collapsed")
        if selected != current_branch:
            if GitManager.switch_branch(selected): st.rerun()
    with c2:
        st.write("**新しいブランチを作成**")
        new_branch = st.text_input("新しいブランチ名", label_visibility="collapsed")
        if st.button("🌱 作成", use_container_width=True):
            if new_branch and GitManager.create_branch(new_branch):
                if GitManager.switch_branch(new_branch): st.success(f"ブランチ '{new_branch}' を作成し、切り替えました。"); st.rerun()
            elif not new_branch: st.warning("ブランチ名を入力してください。")
            else: st.error(f"ブランチ '{new_branch}' の作成に失敗しました。")

def main():
    stats = GitManager.get_global_stats()
    wf_count = len(st.session_state.get('user_workflows', {}))
    
    st.markdown("# 🚀 LLM Prompt Manager")
    st.markdown("*単発処理とワークフロー処理でLLMを最大活用*")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("実行記録", stats['total_executions'])
    c2.metric("ブランチ", stats['total_branches'])
    c3.metric("ワークフロー", wf_count)
    c4.metric("総コスト", format_detailed_cost_display(stats['total_cost']))
    
    with st.sidebar:
        render_streamlined_sidebar()

    evaluator: Union[GeminiEvaluator, OpenAIEvaluator, None] = None
    config = get_model_config(st.session_state.selected_model)
    provider = config.get('api_provider', 'gemini')

    api_key_ok = False
    try:
        if provider == 'openai':
            if st.session_state.openai_api_key:
                evaluator = OpenAIEvaluator(st.session_state.openai_api_key, config)
                api_key_ok = True
            else:
                st.warning("⚠️ OpenAIモデルが選択されていますが、サイドバーからOpenAI APIキーが設定されていません。")
        else: # gemini
            if st.session_state.api_key:
                evaluator = GeminiEvaluator(st.session_state.api_key, config)
                api_key_ok = True
            else:
                st.warning("⚠️ Geminiモデルが選択されていますが、サイドバーからGemini APIキーが設定されていません。")
    except Exception as e:
        st.error(f"❌ 評価エンジンの初期化に失敗: {e}")
            
    if not api_key_ok:
        st.error("選択されたモデルに対応するAPIキーを設定してください。機能が制限されます。")

    if st.session_state.evaluation_history or st.session_state.user_workflows:
        render_git_controls()
        st.markdown("---")

    tab_titles = ["🚀 実行", "📋 履歴", "🔍 比較", "📊 分析"]
    tab1, tab2, tab3, tab4 = st.tabs(tab_titles)

    with tab1:
        if evaluator:
            render_execution_tab(evaluator)
        else:
            st.error(f"実行タブは、選択されたモデル ({config.get('name')}) のAPIキーが設定されるまで利用できません。")
    with tab2: render_history_tab()
    with tab3: render_comparison_tab()
    with tab4: render_visualization_tab()

if __name__ == "__main__":
    main()