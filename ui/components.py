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
        st.markdown(f"{icon} **Step {step_result.step_name}** ({step_result.execution_time:.2f}s)")
        if show_prompt: st.code(step_result.prompt, language='text')
        st.text_area("出力", step_result.response, height=100, key=f"step_out_{step_result.step_name}_{workflow_execution_id}", disabled=True)

def render_workflow_execution_summary(result: 'WorkflowExecutionResult'):
    c1, c2, c3 = st.columns(3)
    c1.metric("実行時間", f"{result.duration_seconds:.1f}秒")
    c2.metric("総コスト", f"${result.total_cost:.6f}")
    c3.metric("総トークン", f"{result.total_tokens:,}")

def render_workflow_live_step(step_name: str, status: str = "running"):
    """並列実行中の個々のステップ（ノード）のプレースホルダーを返す"""
    placeholder = st.empty()
    status_icon = "🔄" if status == "running" else ("✅" if status == "completed" else "❌")
    with placeholder.container():
        st.info(f"{status_icon} {status.capitalize()}: {step_name}")
    return placeholder

# ui/components.py に追加するメソッド（既存のコードの最後に追加）

def render_workflow_edit_status(workflow_def: Dict[str, Any]) -> None:
    """編集中のワークフローの状態を表示"""
    if workflow_def.get('updated_at'):
        st.info(f"📝 このワークフローは {workflow_def['updated_at'][:16]} に更新されました。")
    else:
        st.info("📝 編集モードです。変更を保存してください。")

def render_workflow_validation_errors(errors: List[str]) -> None:
    """ワークフローのバリデーションエラーを表示"""
    if errors:
        st.error("❌ 以下のエラーを修正してください：")
        for error in errors:
            st.markdown(f"- {error}")

def render_workflow_backup_info(workflow_id: str) -> None:
    """ワークフローのバックアップ情報を表示"""
    from core import WorkflowManager
    
    history = WorkflowManager.get_workflow_history(workflow_id)
    if history:
        with st.expander("📅 更新履歴"):
            for entry in reversed(history):
                action_icon = "🆕" if entry['action'] == 'created' else "✏️"
                timestamp = entry['timestamp'][:16] if isinstance(entry['timestamp'], str) else str(entry['timestamp'])[:16]
                st.markdown(f"{action_icon} **{entry['description']}** - {timestamp}")

def render_workflow_dependency_graph(workflow_def: Dict[str, Any]) -> None:
    """ワークフローの依存関係グラフを表示"""
    if 'source_yaml' not in workflow_def or not workflow_def['source_yaml'].get('nodes'):
        st.caption("依存関係グラフを表示するには、YAML形式での定義が必要です。")
        return
    
    nodes = workflow_def['source_yaml']['nodes']
    global_vars = workflow_def.get('global_variables', [])
    
    with st.expander("🔗 依存関係グラフ"):
        # Mermaid形式でグラフを生成
        mermaid_code = ["graph TD"]
        
        # グローバル変数をノードとして追加
        for var in global_vars:
            mermaid_code.append(f'    {var}["{var} (入力)"]')
            mermaid_code.append(f'    {var} --> {var}_style["fas:fa-database"]')
        
        # 各ノードと依存関係を追加
        for node_id, node_def in nodes.items():
            if node_def.get('type') == 'llm':
                mermaid_code.append(f'    {node_id}["{node_id}"]')
                
                # 依存関係を矢印で表現
                dependencies = _get_node_dependencies_for_graph(node_def)
                for dep in dependencies:
                    if dep in global_vars or dep in nodes:
                        mermaid_code.append(f'    {dep} --> {node_id}')
        
        # 結果ノードをハイライト
        for node_id, node_def in nodes.items():
            if node_def.get('isResult'):
                mermaid_code.append(f'    {node_id} --> RESULT["🎯 最終結果"]')
        
        mermaid_text = "\n".join(mermaid_code)
        st.code(mermaid_text, language='mermaid')

def _get_node_dependencies_for_graph(node_def: Dict) -> List[str]:
    """グラフ表示用のノード依存関係を抽出"""
    dependencies = []
    
    # inputs からの依存関係
    inputs = node_def.get('inputs', [])
    if isinstance(inputs, list):
        for inp in inputs:
            if isinstance(inp, str) and inp.startswith(':'):
                dependencies.append(inp[1:])
    elif isinstance(inputs, dict):
        for value in inputs.values():
            if isinstance(value, str) and value.startswith(':'):
                dependencies.append(value[1:])
    
    return dependencies

def render_workflow_quick_actions(workflow_id: str, workflow_def: Dict[str, Any]) -> Optional[str]:
    """ワークフロー用のクイックアクションボタン群"""
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        if st.button("⚡ クイック実行", key=f"quick_run_{workflow_id}", use_container_width=True):
            return "quick_run"
    
    with c2:
        if st.button("📊 統計表示", key=f"stats_{workflow_id}", use_container_width=True):
            return "show_stats"
    
    with c3:
        if st.button("🔄 テスト実行", key=f"test_{workflow_id}", use_container_width=True):
            return "test_run"
    
    with c4:
        if st.button("📋 プレビュー", key=f"preview_{workflow_id}", use_container_width=True):
            return "preview"
    
    return None

def render_workflow_template_preview(workflow_def: Dict[str, Any]) -> None:
    """ワークフローテンプレートのプレビュー表示"""
    st.markdown("#### 📋 ワークフロープレビュー")
    
    global_vars = workflow_def.get('global_variables', [])
    if global_vars:
        st.markdown("##### 🌐 必要な入力変数")
        for var in global_vars:
            st.markdown(f"- `{var}`")
    
    if 'source_yaml' in workflow_def and workflow_def['source_yaml'].get('nodes'):
        nodes = workflow_def['source_yaml']['nodes']
        llm_nodes = [(nid, ndef) for nid, ndef in nodes.items() if ndef.get('type') == 'llm']
        
        st.markdown(f"##### ⚙️ 処理ステップ ({len(llm_nodes)}個)")
        for i, (node_id, node_def) in enumerate(llm_nodes, 1):
            with st.container(border=True):
                st.markdown(f"**Step {i}: {node_id}**")
                
                # 依存関係を表示
                deps = _get_node_dependencies_for_graph(node_def)
                if deps:
                    deps_display = ", ".join([f"`{d}`" for d in deps])
                    st.caption(f"依存: {deps_display}")
                
                # プロンプトテンプレートのプレビュー
                prompt = node_def.get('prompt_template', '')
                if prompt:
                    preview_lines = prompt.split('\n')[:3]
                    preview_text = '\n'.join(preview_lines)
                    if len(prompt.split('\n')) > 3:
                        preview_text += '\n...'
                    st.code(preview_text, language='text')
                
                # 結果ノードの表示
                if node_def.get('isResult'):
                    st.success("🎯 このステップの出力が最終結果となります")
    else:
        # 旧形式の場合
        steps = workflow_def.get('steps', [])
        st.markdown(f"##### ⚙️ 処理ステップ ({len(steps)}個)")
        for i, step in enumerate(steps, 1):
            with st.container(border=True):
                st.markdown(f"**Step {i}: {step.get('name', f'step_{i}')}**")
                prompt = step.get('prompt_template', '')
                if prompt:
                    preview_lines = prompt.split('\n')[:3]
                    preview_text = '\n'.join(preview_lines)
                    if len(prompt.split('\n')) > 3:
                        preview_text += '\n...'
                    st.code(preview_text, language='text')

def render_workflow_execution_metrics(workflow_def: Dict[str, Any]) -> None:
    """ワークフローの実行メトリクス予測を表示"""
    from core import GitManager
    
    # このワークフローの過去の実行履歴を検索
    workflow_name = workflow_def.get('name', '')
    executions = [ex for ex in GitManager.get_branch_executions() 
                 if ex.get('workflow_name') == workflow_name and ex.get('execution_mode') == 'Workflow Summary']
    
    if executions:
        st.markdown("#### 📊 実行履歴メトリクス")
        
        total_runs = len(executions)
        avg_cost = sum(ex.get('total_cost', 0) for ex in executions) / total_runs
        avg_tokens = sum(ex.get('execution_tokens', 0) for ex in executions) / total_runs
        
        c1, c2, c3 = st.columns(3)
        c1.metric("実行回数", f"{total_runs}回")
        c2.metric("平均コスト", f"${avg_cost:.6f}")
        c3.metric("平均トークン", f"{avg_tokens:.0f}")
        
        # 最近の実行ステータス
        recent_executions = sorted(executions, key=lambda x: x.get('timestamp', ''), reverse=True)[:5]
        success_rate = sum(1 for ex in recent_executions if '成功' in ex.get('evaluation', '')) / len(recent_executions) * 100
        
        if success_rate >= 80:
            st.success(f"✅ 直近の成功率: {success_rate:.0f}% (安定)")
        elif success_rate >= 60:
            st.warning(f"⚠️ 直近の成功率: {success_rate:.0f}% (要注意)")
        else:
            st.error(f"❌ 直近の成功率: {success_rate:.0f}% (要改善)")
    else:
        st.info("📊 まだ実行履歴がありません。実行後にメトリクスが表示されます。")

def render_workflow_comparison_selector(current_workflow_id: str) -> Optional[str]:
    """他のワークフローとの比較用セレクター"""
    from core import WorkflowManager
    
    workflows = WorkflowManager.get_saved_workflows()
    other_workflows = {wid: wf for wid, wf in workflows.items() if wid != current_workflow_id}
    
    if not other_workflows:
        st.caption("比較可能な他のワークフローがありません。")
        return None
    
    st.markdown("#### 🔍 他のワークフローと比較")
    options = {wid: wf.get('name', '無名') for wid, wf in other_workflows.items()}
    selected_id = st.selectbox(
        "比較対象を選択", 
        ['選択なし'] + list(options.keys()), 
        format_func=lambda x: "選択してください" if x == '選択なし' else options.get(x, x),
        key=f"compare_selector_{current_workflow_id}"
    )
    
    return selected_id if selected_id != '選択なし' else None