"""
分析タブ
ブランチ構造と統計情報を表示する機能
"""

import streamlit as st
from core import GitManager
from core.data_manager import DataManager
from ui import format_timestamp, render_statistics_summary

def render_visualization_tab():
    st.header("📊 プロジェクト分析")
    if not st.session_state.get('evaluation_history', []):
        st.info("まだ実行履歴がありません。「実行」タブでプロンプトを実行してください。"); return
    
    global_stats, data_stats = GitManager.get_global_stats(), DataManager.get_data_statistics()
    st.subheader("📈 統計サマリー"); render_statistics_summary(global_stats, data_stats); st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🌿 ブランチ構造"); _render_branch_tree()
    with col2:
        st.subheader("🤖 モデル使用状況")
        if data_stats.get('models_used'):
            for model, count in data_stats['models_used'].items(): st.metric(label=model, value=f"{count} 回")
        else: st.caption("モデル使用情報はありません。")
        st.subheader("💾 データ整合性")
        integrity = DataManager.validate_data_integrity()
        if integrity.get('is_valid'):
            st.success("✅ データは正常です。")
            if integrity.get('warnings'):
                 for warning in integrity.get('warnings'): st.warning(warning)
        else:
            for issue in integrity.get('issues', []): st.error(issue)

def _render_branch_tree():
    branch_tree = GitManager.get_branch_tree()
    for branch_name, executions in branch_tree.items():
        if not executions: continue
        with st.container(border=True):
            stats = GitManager.get_branch_stats(branch_name)
            c1, c2 = st.columns([3, 1])
            with c1: st.markdown(f"<h5>🌿 {branch_name}</h5>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div style='text-align: right;'><i>{stats['execution_count']} commits | ${stats['total_cost']:.4f}</i></div>", unsafe_allow_html=True)
            st.markdown("###### 最新のコミット:")
            for execution in reversed(executions[-3:]):
                ts, memo = format_timestamp(execution['timestamp']), execution.get('commit_message', 'メモなし')
                st.markdown(f"<small><code>{execution['commit_hash'][:7]}</code> {memo} ({ts})</small>", unsafe_allow_html=True)
            if len(executions) > 3: st.markdown(f"<small><i>...他{len(executions)-3}件</i></small>", unsafe_allow_html=True)