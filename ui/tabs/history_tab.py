"""
改善された実行履歴タブ (ワークフロー対応版)
"""
import streamlit as st
from core import GitManager
from ui.components import render_execution_card

def render_history_tab():
    """改善された履歴タブ"""
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1: st.markdown("### 📋 実行履歴")
    with header_col2:
        show_all_branches = st.checkbox("全ブランチの履歴を表示", value=False)
        if not show_all_branches: st.caption(f"現在のブランチ: `{GitManager.get_current_branch()}`")
    
    all_executions = _get_executions_to_show(show_all_branches)
    if not all_executions:
        st.info("表示対象の実行履歴がありません。"); return
    
    # 親レコード（単発実行とワークフローサマリー）のみをフィルタリング
    parent_executions = [ex for ex in all_executions if ex.get('execution_mode') != 'Workflow Step']
    
    filtered_executions = _render_filters_and_search(parent_executions)
    _render_paginated_executions(filtered_executions)

def _get_executions_to_show(show_all_branches: bool):
    """表示する実行記録を取得"""
    history = st.session_state.get('evaluation_history', []) if show_all_branches else GitManager.get_branch_executions()
    return sorted(history, key=lambda x: str(x.get('timestamp', '1970-01-01')), reverse=True)

def _render_filters_and_search(executions):
    st.markdown("---")
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1: search_text = st.text_input("🔍 検索", placeholder="メモ、プロンプト、回答内容...", label_visibility="collapsed")
    with filter_col2:
        all_models = sorted(list(set(ex.get('model_name', 'Unknown') for ex in executions)))
        selected_model = st.selectbox("🤖 モデル", ['すべて'] + all_models, label_visibility="collapsed")
    
    if search_text:
        search_lower = search_text.lower()
        executions = [ex for ex in executions if (search_lower in ex.get('commit_message', '').lower() or
                                                 search_lower in ex.get('final_prompt', '').lower() or
                                                 search_lower in (ex.get('response') or '').lower())]
    if selected_model != 'すべて':
        executions = [ex for ex in executions if ex.get('model_name', 'Unknown') == selected_model]
    return executions

def _render_paginated_executions(executions):
    total = len(executions)
    if total == 0:
        st.info("条件に合う実行記録が見つかりません。"); return
    
    c1, c2 = st.columns([1, 3])
    with c1:
        page_size = st.selectbox("表示件数", [5, 10, 20, 50], index=0, key="history_page_size")
        st.metric("ヒット件数", total)
    total_pages = (total - 1) // page_size + 1
    with c2: current_page = st.number_input(f"ページ (1〜{total_pages})", 1, total_pages, 1, key="history_current_page")
    start_idx, end_idx = (current_page - 1) * page_size, min((current_page - 1) * page_size + page_size, total)
    
    st.caption(f"{start_idx + 1} - {end_idx} 件目を表示中 (全 {total} 件)"); st.markdown("---")
    
    for execution in executions[start_idx:end_idx]:
        with st.container(border=True):
            render_execution_card(execution, show_details=True)