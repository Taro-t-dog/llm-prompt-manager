# ============================================
# ui/components.py (統計情報タブ実装)
# ============================================
import streamlit as st
import datetime
import json
import sys
import os
import time
from typing import Dict, List, Any, Optional
import pandas as pd
from enum import Enum
import plotly.express as px

# パスの追加
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 安全なインポート
try:
    from ui.styles import get_response_box_html, get_evaluation_box_html, get_metric_card_html, format_detailed_cost_display, format_tokens_display
except ImportError:
    from styles import get_response_box_html, get_evaluation_box_html, get_metric_card_html, format_detailed_cost_display, format_tokens_display

try:
    from core.workflow_engine import StepResult, WorkflowExecutionResult, ExecutionStatus
except ImportError:
    class StepResult: pass
    class WorkflowExecutionResult: pass
    class ExecutionStatus(Enum): PENDING, RUNNING, COMPLETED, FAILED, CANCELLED = "pending", "running", "completed", "failed", "cancelled"

def render_response_box(content: str, title: str = "🤖 回答", border_color: str = "#667eea"):
    st.markdown(f"**{title}**")
    st.markdown(get_response_box_html(content if content is not None else "応答がありません。", border_color), unsafe_allow_html=True)

def render_evaluation_box(content: str, title: str = "⭐ 評価"):
    st.markdown(f"**{title}**")
    st.markdown(get_evaluation_box_html(content if content is not None else "評価がありません。"), unsafe_allow_html=True)

def render_cost_metrics(execution_cost: float, evaluation_cost: float, total_cost: float, execution_tokens: int, evaluation_tokens: int):
    st.subheader("💰 コスト")
    c1, c2, c3 = st.columns(3)
    c1.metric("実行コスト", f"${execution_cost:.6f}", f"{execution_tokens:,} tokens")
    c2.metric("評価コスト", f"${evaluation_cost:.6f}", f"{evaluation_tokens:,} tokens")
    c3.metric("総コスト", f"${total_cost:.6f}", f"{execution_tokens + evaluation_tokens:,} tokens")

def format_timestamp(timestamp: Any) -> str:
    if isinstance(timestamp, datetime.datetime): return timestamp.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(timestamp, str):
        try:
            return datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            return timestamp
    return str(timestamp)
    
def render_execution_card(execution: Dict[str, Any], show_details: bool = True):
    exec_mode = execution.get('execution_mode', '単発実行')
    is_workflow_summary = exec_mode == 'Workflow Summary'
    is_workflow_step = exec_mode == 'Workflow Step'
    icon = "🔄" if is_workflow_summary else ("⚙️" if is_workflow_step else "📝")
    type_str = "ワークフロー概要" if is_workflow_summary else ("ステップ" if is_workflow_step else "単発実行")
    
    with st.container():
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <span class="branch-tag">{execution.get('branch', 'N/A')}</span>
                <span style="font-size: 1.1em;">{icon}</span>
                <strong>{execution.get('commit_message', 'メモなし')}</strong>
                <small style="color: #666;">({type_str})</small>
            </div>
            <div style="color: #666; font-size: 0.9rem;">
                🤖 {execution.get('model_name', 'N/A')} | 📅 {format_timestamp(execution.get('timestamp'))[:16]} | <span class="commit-hash">{execution.get('commit_hash', 'N/A')}</span>
            </div>""", unsafe_allow_html=True)
        c2.metric("総コスト", format_detailed_cost_display(execution.get('total_cost', 0.0)))
        c3.metric("総トークン", format_tokens_display(execution.get('execution_tokens', 0) + execution.get('evaluation_tokens', 0)))

        if show_details:
            with st.expander("📋 詳細を表示"):
                if is_workflow_summary:
                    _render_workflow_summary_details(execution)
                else:
                    _render_single_execution_details(execution)

def _render_single_execution_details(execution: Dict[str, Any]):
    c1, c2 = st.columns([2, 1])
    with c1:
        render_response_box(execution.get('response', '応答なし'))
        if execution.get('evaluation'): render_evaluation_box(execution.get('evaluation', '評価なし'))
    with c2:
        st.markdown("**📊 詳細メトリクス**")
        st.metric("実行トークン", f"{execution.get('execution_tokens', 0):,}")
        st.metric("評価トークン", f"{execution.get('evaluation_tokens', 0):,}")
        st.metric("実行コスト", format_detailed_cost_display(execution.get('execution_cost', 0.0)))
        st.metric("評価コスト", format_detailed_cost_display(execution.get('evaluation_cost', 0.0)))
        if execution.get('execution_mode') == 'Workflow Step':
            st.markdown("**⚙️ ステップ情報**")
            st.markdown(f"**WF名:** {execution.get('workflow_name', 'N/A')}")
            st.markdown(f"**WF実行ID:** `{execution.get('workflow_execution_id', 'N/A')}`")
        if st.button("📝 プロンプト確認", key=f"prompt_btn_{execution['commit_hash']}"):
            st.code(execution.get('final_prompt', 'N/A'), language='text')

def _render_workflow_summary_details(summary_execution: Dict[str, Any]):
    wf_exec_id = summary_execution.get('workflow_execution_id')
    if not wf_exec_id: st.warning("ワークフロー実行IDが見つかりません。"); return

    st.markdown(f"#### ワークフロー: {summary_execution.get('workflow_name', '無名')}")
    st.markdown(f"**最終結果:**")
    st.info(summary_execution.get('response') or "最終結果なし")

    steps = sorted([ex for ex in st.session_state.evaluation_history if ex.get('workflow_execution_id') == wf_exec_id and ex.get('execution_mode') == 'Workflow Step'], key=lambda x: x.get('step_number', 0))
    if not steps: st.warning("このワークフロー実行に対応するステップが見つかりませんでした。"); return

    st.markdown("---")
    st.markdown("##### ⚙️ 実行ステップ一覧")
    for step in steps:
        with st.container(border=True):
            st.markdown(f"**Step {step.get('step_number', '?')}: {step.get('step_name', '無名')}**")
            st.caption(f"モデル: {step.get('model_name', 'N/A')} | コスト: {format_detailed_cost_display(step.get('total_cost', 0.0))} | トークン: {format_tokens_display(step.get('execution_tokens', 0))}")
            _render_single_execution_details(step)

def render_prompt_details(execution: Dict[str, Any]):
    st.markdown("**📋 プロンプトと評価基準の詳細**")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### プロンプト情報")
        if execution.get('execution_mode') == "テンプレート + データ入力":
            st.markdown("**テンプレート:**"); st.code(execution.get('prompt_template', '情報なし'), language='text')
            st.markdown("**入力データ:**"); st.code(execution.get('user_input', '情報なし'), language='text')
        st.markdown("**最終プロンプト:**"); st.code(execution.get('final_prompt', '情報なし'), language='text')
    with c2:
        st.markdown("##### 評価基準"); st.code(execution.get('criteria', '情報なし'), language='text')

def render_comparison_metrics(exec1: Dict[str, Any], exec2: Dict[str, Any]):
    st.subheader("📊 比較")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        cost1, cost2 = exec1.get('total_cost', 0.0), exec2.get('total_cost', 0.0)
        st.metric("総コスト", f"${cost2:.6f}", f"{cost2 - cost1:+.6f}")
    with c2:
        t1 = exec1.get('execution_tokens', 0) + exec1.get('evaluation_tokens', 0)
        t2 = exec2.get('execution_tokens', 0) + exec2.get('evaluation_tokens', 0)
        st.metric("総トークン", f"{t2:,}", f"{t2 - t1:+,}")
    with c3:
        t1, t2 = exec1.get('execution_tokens', 0), exec2.get('execution_tokens', 0)
        st.metric("実行トークン", f"{t2:,}", f"{t2 - t1:+,}")
    with c4:
        t1, t2 = exec1.get('evaluation_tokens', 0), exec2.get('evaluation_tokens', 0)
        st.metric("評価トークン", f"{t2:,}", f"{t2 - t1:+,}")

def render_comparison_responses(exec1: Dict[str, Any], exec2: Dict[str, Any]):
    st.subheader("🤖 回答比較")
    c1, c2 = st.columns(2)
    with c1: render_response_box(exec1.get('response', '応答なし'), f"比較元 ({exec1.get('commit_hash', 'N/A')[:8]})", "#667eea")
    with c2: render_response_box(exec2.get('response', '応答なし'), f"比較先 ({exec2.get('commit_hash', 'N/A')[:8]})", "#f5576c")

def render_comparison_evaluations(exec1: Dict[str, Any], exec2: Dict[str, Any]):
    st.subheader("⭐ 評価比較")
    c1, c2 = st.columns(2)
    with c1: render_evaluation_box(exec1.get('evaluation', '評価なし'), f"比較元 ({exec1.get('commit_hash', 'N/A')[:8]})")
    with c2: render_evaluation_box(exec2.get('evaluation', '評価なし'), f"比較先 ({exec2.get('commit_hash', 'N/A')[:8]})")

def render_branch_selector(available_branches: List[str], current_branch: str, key: str = "branch_selector_ui_comp"):
    idx = available_branches.index(current_branch) if current_branch in available_branches else 0
    return st.selectbox("現在のブランチ:", available_branches, index=idx, key=key)

def render_execution_selector(executions: List[Dict[str, Any]], label: str, key: str):
    if not executions: st.caption(f"{label} 対象の実行記録がありません。"); return None
    options = {i: f"{ex.get('commit_hash', 'N/A')[:8]} - {ex.get('commit_message', 'メモなし')}" for i, ex in enumerate(executions)}
    idx = st.selectbox(label, options.keys(), format_func=lambda i: options[i], key=key)
    return executions[idx] if idx is not None else None

def render_export_section(data_manager_class: Any):
    st.subheader("📤 エクスポート")
    c1, c2 = st.columns(2)
    if c1.button("💾 JSON", use_container_width=True):
        st.download_button("⬇️ ダウンロード", data_manager_class.export_to_json(), data_manager_class.get_file_suggestion("json"), "application/json")
    if c2.button("📊 CSV", use_container_width=True):
        st.download_button("⬇️ ダウンロード", data_manager_class.export_to_csv(), data_manager_class.get_file_suggestion("csv"), "text/csv")

def render_import_section(data_manager_class: Any):
    st.subheader("📂 インポート")
    uploaded = st.file_uploader("インポートファイルを選択 (JSON/CSV)", type=["json", "csv"])
    if uploaded and st.button("📥 インポート実行"):
        try:
            if uploaded.name.endswith('.json'):
                result = data_manager_class.import_from_json(json.load(uploaded))
            else:
                result = data_manager_class.import_from_csv(pd.read_csv(uploaded))
            if result.get('success'): st.success(f"✅ {result.get('imported_count', 0)}件インポートしました。"); st.rerun()
            else: st.error(f"❌ インポート失敗: {result.get('error', '不明')}")
        except Exception as e: st.error(f"❌ ファイル処理エラー: {e}")

def render_statistics_summary(global_stats: Dict[str, Any], data_stats: Dict[str, Any]):
    c1, c2, c3 = st.columns(3)
    c1.metric("ブランチ数", global_stats.get('total_branches', 0))
    c2.metric("総実行数", global_stats.get('total_executions', 0))
    c3.metric("総コスト", format_detailed_cost_display(global_stats.get('total_cost', 0.0)))

def render_detailed_statistics(data_stats: Dict[str, Any], data_manager_class: Any):
    with st.expander("📊 詳細統計を見る"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🤖 モデル使用状況**")
            if data_stats.get('models_used'):
                for model, count in data_stats['models_used'].items(): st.write(f"• **{model}**: {count}回")
            else: st.caption("モデル使用情報なし")
        with c2:
            st.markdown("**💾 データ整合性**")
            integrity = data_manager_class.validate_data_integrity()
            if integrity.get('is_valid'): st.success("✅ データは正常です。")
            else: st.warning("⚠️ データに問題が見つかりました。")

def render_workflow_card(workflow: Dict[str, Any], show_actions: bool = True) -> Optional[str]:
    created_date = format_timestamp(workflow.get('created_at', ''))[:10]
    st.markdown(f"**{workflow.get('name', '無名')}** - {len(workflow.get('steps',[]))}ステップ ({created_date})")
    if show_actions:
        if st.button("実行", key=f"run_{workflow.get('id')}"): return "run"
    return None

def render_workflow_progress(current_step: int, total_steps: int, step_names: List[str], current_step_name: str = ""):
    progress = float(current_step) / total_steps if total_steps > 0 else 0.0
    st.progress(progress, text=f"Step {current_step}/{total_steps}: {current_step_name}")

def render_workflow_result_tabs(result: 'WorkflowExecutionResult', debug_mode: bool = False):
    if not result.success:
        st.error(f"❌ ワークフロー実行失敗: {result.error}")
        return
    st.success(f"✅ ワークフロー「{result.workflow_name}」完了")
    render_workflow_execution_summary(result)
    
    tab_titles = ["🎯 最終結果", "📋 ステップ詳細", "📊 統計情報"]
    if debug_mode: tab_titles.append("🐛 デバッグ情報")
    tabs = st.tabs(tab_titles)
    
    with tabs[0]:
        st.markdown("### 🎯 最終出力")
        st.text_area("最終出力結果", getattr(result, 'final_output', ""), height=300)
    with tabs[1]:
        st.markdown("### 📋 各ステップの詳細結果")
        for step in getattr(result, 'steps', []): render_workflow_step_card(step, step.step_number, show_prompt=debug_mode)
    with tabs[2]:
        _render_statistics_tab_content(result)
    if debug_mode:
        with tabs[3]:
            st.markdown("### 🐛 デバッグ情報")
            st.json(getattr(result, 'metadata', {"info": "No metadata available."}))

def _render_statistics_tab_content(result: 'WorkflowExecutionResult'):
    st.markdown("### 📊 実行統計")
    steps = result.steps
    if not steps:
        st.info("統計情報を表示するためのステップデータがありません。"); return

    st.markdown("#### パフォーマンス")
    c1, c2, c3 = st.columns(3)
    c1.metric("スループット (Tokens/Sec)", f"{result.total_tokens / result.duration_seconds:.1f}" if result.duration_seconds > 0 else "N/A")
    c2.metric("コスト効率 ($/1K Tokens)", f"${result.total_cost / (result.total_tokens / 1000):.4f}" if result.total_tokens > 0 else "N/A")
    c3.metric("ステップ平均時間 (Sec)", f"{sum(s.execution_time for s in steps) / len(steps):.2f}" if steps else "N/A")
    
    st.markdown("---")
    st.markdown("#### コストとトークンの分析")
    df = pd.DataFrame([{"ステップ": f"Step {s.step_number}: {s.step_name}", "コスト (USD)": s.cost, "トークン数": s.tokens, "実行時間 (秒)": s.execution_time} for s in steps])
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**コスト内訳**")
        if df["コスト (USD)"].sum() > 0:
            fig = px.pie(df, names='ステップ', values='コスト (USD)', title='ステップ別コスト割合', hole=.3)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else: st.caption("コストが発生していません。")
            
    with c2:
        st.markdown("**トークン使用量内訳**")
        if df["トークン数"].sum() > 0:
            fig = px.pie(df, names='ステップ', values='トークン数', title='ステップ別トークン使用量割合', hole=.3)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else: st.caption("トークンが使用されていません。")
            
    st.markdown("---")
    st.markdown("#### 実行時間の分析")
    if not df.empty:
        fig = px.bar(df, x='ステップ', y='実行時間 (秒)', title='各ステップの実行時間', text_auto='.2s')
        st.plotly_chart(fig, use_container_width=True)

def render_variable_substitution_help():
    with st.expander("💡 変数とフィルターの使い方"): st.markdown("...")

def render_error_details(error_type: str, error_message: str, suggestions: List[str]):
    st.error(f"**エラータイプ:** {error_type}")
    with st.expander("エラー詳細"): st.code(error_message, language='text')
    if suggestions: st.markdown("##### 💡 対処法:"); [st.markdown(f"- {s}") for s in suggestions]

def render_workflow_template_selector() -> Optional[str]: return None

def render_workflow_step_card(step_result: 'StepResult', step_number: int, show_prompt: bool = False, workflow_execution_id: Optional[str] = None):
    icon = "✅" if step_result.success else "❌"
    with st.container(border=True):
        st.markdown(f"{icon} **Step {step_number}: {step_result.step_name}**")
        if show_prompt: st.code(step_result.prompt, language='text')
        st.text_area("出力", step_result.response, height=100, key=f"step_out_{step_number}_{workflow_execution_id}", disabled=True)

def render_workflow_execution_summary(result: 'WorkflowExecutionResult'):
    c1, c2, c3 = st.columns(3)
    c1.metric("実行時間", f"{result.duration_seconds:.1f}秒")
    c2.metric("総コスト", f"${result.total_cost:.6f}")
    c3.metric("総トークン", f"{result.total_tokens:,}")

def render_workflow_live_step(step_number: int, step_name: str, status: str = "running") -> st.empty:
    placeholder = st.empty()
    with placeholder.container():
        st.info(f"🔄 Step {step_number}: 「{step_name}」を実行中...")
    return placeholder