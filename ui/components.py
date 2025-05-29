# ============================================
# ui/components.py (SyntaxError修正・完全版)
# ============================================
"""
改善されたUIコンポーネント
既存機能 + ワークフロー機能のコンポーネントを追加
"""
import streamlit as st
import datetime
import json
import sys
import os
import time
from typing import Dict, List, Any, Optional
import pandas as pd # render_import_section, render_workflow_result_tabs で使用
from enum import Enum # ダミークラス ExecutionStatus で使用

# パスの追加 (アプリケーションのルート構造に依存するため、環境に合わせて調整が必要な場合がある)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # ui ディレクトリの親 (プロジェクトルートを想定)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 安全なインポート (styles と core.workflow_engine)
try:
    # 通常のパッケージ内インポート (推奨)
    from .styles import (
        get_response_box_html, get_evaluation_box_html, get_metric_card_html,
        format_detailed_cost_display, format_tokens_display
    )
except ImportError: # スクリプトとして直接実行されたり、パス設定が特殊な場合のフォールバック
    try: # ui.styles を試す (ui ディレクトリがPYTHONPATH直下にある場合など)
        from ui.styles import (
            get_response_box_html, get_evaluation_box_html, get_metric_card_html,
            format_detailed_cost_display, format_tokens_display
        )
    except ImportError: # styles を直接試す (プロジェクトルートがPYTHONPATHに含まれ、stylesがそこにある場合)
        from styles import (
            get_response_box_html, get_evaluation_box_html, get_metric_card_html,
            format_detailed_cost_display, format_tokens_display
        )
        st.warning("stylesモジュールを相対パス以外からインポートしました。プロジェクト構造を確認してください。")


try:
    from core.workflow_engine import StepResult, WorkflowExecutionResult, ExecutionStatus
except ImportError:
    # 開発環境やテスト時にモックやダミークラスを提供することも検討
    # これにより、coreモジュールが完全に利用できない状況でもUI部品のプレビュー程度は可能になる
    class StepResult:
        def __init__(self, success=False, step_number=0, step_name="", prompt="", response="", tokens=0, cost=0.0, execution_time=0.0, error=None, git_record=None, metadata=None, model_name=None): # model_name追加
            self.success = success; self.step_number = step_number; self.step_name = step_name; self.prompt = prompt; self.response = response; self.tokens = tokens; self.cost = cost; self.execution_time = execution_time; self.error = error; self.git_record = git_record; self.metadata = metadata; self.model_name=model_name
    class WorkflowExecutionResult:
        def __init__(self, success=False, execution_id="", workflow_name="", start_time=None, end_time=None, duration_seconds=0.0, status=None, steps=None, total_cost=0.0, total_tokens=0, final_output=None, error=None, metadata=None):
            self.success = success; self.execution_id = execution_id; self.workflow_name = workflow_name; self.start_time = start_time or datetime.datetime.now(); self.end_time = end_time; self.duration_seconds = duration_seconds; self.status = status; self.steps = steps or []; self.total_cost = total_cost; self.total_tokens = total_tokens; self.final_output = final_output; self.error = error; self.metadata = metadata
    class ExecutionStatus(Enum):
        PENDING = "pending"; RUNNING = "running"; COMPLETED = "completed"; FAILED = "failed"; CANCELLED = "cancelled"
        def __str__(self): return self.value
        def __eq__(self, other):
            if isinstance(other, ExecutionStatus):
                return self.value == other.value
            if isinstance(other, str):
                return self.value == other
            return False

    st.warning("core.workflow_engine のインポートに失敗しました。ダミークラスを使用します。一部のコンポーネントが正しく動作しない可能性があります。")


def render_response_box(content: str, title: str = "🤖 回答", border_color: str = "#667eea"):
    """LLMの回答を表示するボックス"""
    st.markdown(f"**{title}**")
    html_content = get_response_box_html(content if content is not None else "応答がありません。", border_color)
    st.markdown(html_content, unsafe_allow_html=True)


def render_evaluation_box(content: str, title: str = "⭐ 評価"):
    """評価結果を表示するボックス"""
    st.markdown(f"**{title}**")
    html_content = get_evaluation_box_html(content if content is not None else "評価がありません。")
    st.markdown(html_content, unsafe_allow_html=True)


def render_cost_metrics(execution_cost: float, evaluation_cost: float, total_cost: float,
                       execution_tokens: int, evaluation_tokens: int):
    """コスト情報を表示"""
    st.subheader("💰 コスト")
    cost_col1, cost_col2, cost_col3 = st.columns(3)
    with cost_col1:
        st.markdown(get_metric_card_html("実行コスト", f"${execution_cost:.6f}", f"{execution_tokens:,} tokens"), unsafe_allow_html=True)
    with cost_col2:
        st.markdown(get_metric_card_html("評価コスト", f"${evaluation_cost:.6f}", f"{evaluation_tokens:,} tokens"), unsafe_allow_html=True)
    with cost_col3:
        st.markdown(get_metric_card_html("総コスト", f"${total_cost:.6f}", f"{execution_tokens + evaluation_tokens:,} tokens"), unsafe_allow_html=True)


def render_execution_card(execution: Dict[str, Any], tags: Optional[List[str]] = None, show_details: bool = True):
    """実行記録カード（改善版）"""
    timestamp_str = execution.get('timestamp', datetime.datetime.now().isoformat())
    timestamp = format_timestamp(timestamp_str)
    exec_hash = execution.get('commit_hash', 'N/A')
    exec_memo = execution.get('commit_message', 'メモなし')
    branch = execution.get('branch', 'unknown')
    model_name = execution.get('model_name', 'Unknown')
    is_workflow = execution.get('workflow_id') is not None
    workflow_icon = "🔄" if is_workflow else "📝"
    execution_type_str = "ワークフロー" if is_workflow else "単発実行"
    
    header_col1, header_col2, header_col3 = st.columns([3, 1, 1])
    with header_col1:
        st.markdown(f"""
        <div class="commit-card">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <span class="branch-tag">{branch}</span>
                <span style="font-size: 1.1em;">{workflow_icon}</span>
                <strong>{exec_memo}</strong>
                <small style="color: #666;">({execution_type_str})</small>
            </div>
            <div style="color: #666; font-size: 0.9rem;">
                🤖 {model_name} | 📅 {timestamp[:16]} | <span class="commit-hash">{exec_hash}</span>
            </div>
        </div>""", unsafe_allow_html=True)
    
    with header_col2:
        execution_cost_val = execution.get('execution_cost', 0.0)
        cost_display = format_detailed_cost_display(execution_cost_val)
        st.metric("実行コスト", cost_display)
    
    with header_col3:
        exec_tokens_val = execution.get('execution_tokens', 0)
        eval_tokens_val = execution.get('evaluation_tokens', 0)
        total_tokens_val = exec_tokens_val + eval_tokens_val
        formatted_tokens = format_tokens_display(total_tokens_val)
        st.metric("トークン", formatted_tokens, help=f"正確な値: {total_tokens_val:,}")
    
    if show_details:
        with st.expander("📋 詳細を表示", key=f"details_expander_{exec_hash}"):
            detail_col1, detail_col2 = st.columns([2, 1])
            with detail_col1:
                render_response_box(execution.get('response', '応答なし'))
                if execution.get('evaluation'):
                    render_evaluation_box(execution.get('evaluation', '評価なし'))
            with detail_col2:
                st.markdown("**📊 詳細メトリクス**")
                st.metric("実行トークン", f"{exec_tokens_val:,}")
                st.metric("評価トークン", f"{eval_tokens_val:,}")
                
                exec_cost_display = format_detailed_cost_display(execution_cost_val)
                eval_cost_display = format_detailed_cost_display(execution.get('evaluation_cost', 0.0))
                total_cost_display = format_detailed_cost_display(execution_cost_val + execution.get('evaluation_cost', 0.0))
                
                st.metric("実行コスト", exec_cost_display)
                st.metric("評価コスト", eval_cost_display)
                st.metric("総コスト", total_cost_display)
                
                if is_workflow:
                    st.markdown("**🔄 ワークフロー情報**")
                    if execution.get('step_number'): st.metric("ステップ番号", execution['step_number'])
                    if execution.get('workflow_id'): st.code(f"実行ID: {execution['workflow_id']}")
                    if execution.get('workflow_name'): st.markdown(f"**WF名:** {execution['workflow_name']}")

                if st.button("📝 プロンプト確認", key=f"prompt_details_button_{exec_hash}"):
                    st.code(execution.get('final_prompt', 'プロンプト情報なし'), language='text')


def render_comparison_metrics(exec1: Dict[str, Any], exec2: Dict[str, Any]):
    """比較メトリクス"""
    st.subheader("📊 比較")
    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
    with metrics_col1:
        cost1 = exec1.get('execution_cost', 0.0) + exec1.get('evaluation_cost', 0.0)
        cost2 = exec2.get('execution_cost', 0.0) + exec2.get('evaluation_cost', 0.0)
        cost_diff = cost2 - cost1
        st.metric("総コスト", f"${cost2:.6f}", f"{cost_diff:+.6f}")
    with metrics_col2:
        total_tokens1 = exec1.get('execution_tokens', 0) + exec1.get('evaluation_tokens', 0)
        total_tokens2 = exec2.get('execution_tokens', 0) + exec2.get('evaluation_tokens', 0)
        token_diff = total_tokens2 - total_tokens1
        st.metric("総トークン", f"{total_tokens2:,}", f"{token_diff:+,}")
    with metrics_col3:
        exec_token_diff = exec2.get('execution_tokens', 0) - exec1.get('execution_tokens', 0)
        st.metric("実行トークン", f"{exec2.get('execution_tokens', 0):,}", f"{exec_token_diff:+,}")
    with metrics_col4:
        eval_token_diff = exec2.get('evaluation_tokens', 0) - exec1.get('evaluation_tokens', 0)
        st.metric("評価トークン", f"{exec2.get('evaluation_tokens', 0):,}", f"{eval_token_diff:+,}")


def render_comparison_responses(exec1: Dict[str, Any], exec2: Dict[str, Any]):
    """回答比較"""
    st.subheader("🤖 回答比較")
    response_col1, response_col2 = st.columns(2)
    with response_col1:
        render_response_box(exec1.get('response', '応答なし'), f"比較元 ({exec1.get('commit_hash', 'N/A')[:8]})", "#667eea")
    with response_col2:
        render_response_box(exec2.get('response', '応答なし'), f"比較先 ({exec2.get('commit_hash', 'N/A')[:8]})", "#f5576c")


def render_comparison_evaluations(exec1: Dict[str, Any], exec2: Dict[str, Any]):
    """評価比較"""
    st.subheader("⭐ 評価比較")
    eval_col1, eval_col2 = st.columns(2)
    with eval_col1:
        render_evaluation_box(exec1.get('evaluation', '評価なし'), f"比較元 ({exec1.get('commit_hash', 'N/A')[:8]})")
    with eval_col2:
        render_evaluation_box(exec2.get('evaluation', '評価なし'), f"比較先 ({exec2.get('commit_hash', 'N/A')[:8]})")


def render_export_section(data_manager_class: Any):
    """エクスポートセクション (DataManagerクラスを想定)"""
    st.subheader("📤 エクスポート")
    export_col1, export_col2 = st.columns(2)
    with export_col1:
        if st.button("💾 JSON (完全)", use_container_width=True, key="export_json_button_comp"):
            if hasattr(data_manager_class, 'export_to_json') and hasattr(data_manager_class, 'get_file_suggestion'):
                json_data_str = data_manager_class.export_to_json(include_metadata=True)
                filename_json = data_manager_class.get_file_suggestion("json")
                st.download_button("⬇️ JSONダウンロード", json_data_str, filename_json, "application/json", key="download_json_export_comp")
            else:
                st.error("DataManager に必要なエクスポートメソッドがありません。")
    with export_col2:
        if st.button("📊 CSV (データ)", use_container_width=True, key="export_csv_button_comp"):
            if hasattr(data_manager_class, 'export_to_csv') and hasattr(data_manager_class, 'get_file_suggestion'):
                csv_data_str = data_manager_class.export_to_csv()
                filename_csv = data_manager_class.get_file_suggestion("csv")
                st.download_button("⬇️ CSVダウンロード", csv_data_str, filename_csv, "text/csv", key="download_csv_export_comp")
            else:
                st.error("DataManager に必要なエクスポートメソッドがありません。")


def render_import_section(data_manager_class: Any):
    """インポートセクション (DataManagerクラスを想定)"""
    st.subheader("📂 インポート")
    uploaded_file_obj = st.file_uploader("インポートするファイルを選択 (JSON または CSV)", type=["json", "csv"], key="import_file_uploader_comp")
    
    if uploaded_file_obj is not None:
        file_name_str = uploaded_file_obj.name
        file_extension = file_name_str.split('.')[-1].lower()
        
        try:
            if file_extension == 'json':
                json_content_str = uploaded_file_obj.read().decode('utf-8')
                history_data_dict = json.loads(json_content_str)
                
                total_records = len(history_data_dict.get('evaluation_history', []))
                st.info(f"📊 選択されたJSONファイルには {total_records} 件の記録が含まれています。")
                
                import_mode = st.radio("インポート方法を選択:", ["現在のデータを置き換える (完全置換)", "現在のデータに追加する"], horizontal=True, key="json_import_mode_radio_comp")
                
                if st.button("📥 JSONファイルをインポート", key="import_json_confirm_button_comp"):
                    if not hasattr(data_manager_class, 'import_from_json'):
                        st.error("DataManager に import_from_json メソッドがありません。"); return

                    result_import: Dict[str, Any]
                    if import_mode == "現在のデータを置き換える (完全置換)":
                        result_import = data_manager_class.import_from_json(history_data_dict)
                    else: # "現在のデータに追加する"
                        if not hasattr(data_manager_class, 'export_to_json'):
                             st.error("追加インポートには DataManager.export_to_json メソッドが必要です。"); return
                        
                        current_data_json_str = data_manager_class.export_to_json(include_metadata=False)
                        current_data_dict = json.loads(current_data_json_str) if current_data_json_str else {'evaluation_history': [], 'branches': {}, 'tags': {}, 'current_branch': 'main'}
                        
                        current_data_dict['evaluation_history'].extend(history_data_dict.get('evaluation_history', []))
                        for branch_name, executions in history_data_dict.get('branches', {}).items():
                            if branch_name not in current_data_dict['branches']:
                                current_data_dict['branches'][branch_name] = []
                            current_data_dict['branches'][branch_name].extend(executions)
                        current_data_dict['tags'].update(history_data_dict.get('tags', {}))
                        current_data_dict['current_branch'] = history_data_dict.get('current_branch', current_data_dict.get('current_branch', 'main'))

                        result_import = data_manager_class.import_from_json(current_data_dict)

                    if result_import.get('success'):
                        st.success(f"✅ {result_import.get('imported_count', 0)} 件の記録をインポートしました。")
                        st.rerun()
                    else:
                        st.error(f"❌ インポートに失敗しました: {result_import.get('error', '詳細不明')}")
            
            elif file_extension == 'csv':
                df_uploaded = pd.read_csv(uploaded_file_obj)
                st.info(f"📊 選択されたCSVファイルには {len(df_uploaded)} 件の記録が含まれています。")
                
                if st.button("📥 CSVファイルをインポート", key="import_csv_confirm_button_comp"):
                    if not hasattr(data_manager_class, 'import_from_csv'):
                        st.error("DataManager に import_from_csv メソッドがありません。"); return
                        
                    result_import_csv = data_manager_class.import_from_csv(df_uploaded)
                    if result_import_csv.get('success'):
                        st.success(f"✅ {result_import_csv.get('imported_count', 0)} 件の記録をCSVからインポートしました。")
                        st.rerun()
                    else:
                        st.error(f"❌ CSVインポートに失敗しました: {result_import_csv.get('error', '詳細不明')}")
            
        except Exception as e_import_file:
            st.error(f"❌ ファイルの読み込みまたは処理中にエラーが発生しました: {str(e_import_file)}")


def render_statistics_summary(global_stats: Dict[str, Any], data_stats: Dict[str, Any]): # data_stats は将来用
    """統計サマリー"""
    stats_col1, stats_col2, stats_col3 = st.columns(3)
    with stats_col1: st.metric("ブランチ数", global_stats.get('total_branches', 0))
    with stats_col2: st.metric("総実行数", global_stats.get('total_executions', 0))
    with stats_col3:
        cost_display = format_detailed_cost_display(global_stats.get('total_cost', 0.0))
        st.metric("総コスト", cost_display)


def render_detailed_statistics(data_stats: Dict[str, Any], data_manager_class: Any):
    """詳細統計 (DataManagerクラスを想定)"""
    with st.expander("📊 詳細統計を見る"):
        detail_col1, detail_col2 = st.columns(2)
        with detail_col1:
            st.markdown("**🤖 モデル使用状況**")
            models_used_dict = data_stats.get('models_used', {})
            total_records_stats = data_stats.get('total_records', 0)
            if models_used_dict:
                for model_name_stats, count_stats in models_used_dict.items():
                    percentage = (count_stats / total_records_stats) * 100 if total_records_stats > 0 else 0
                    st.write(f"• **{model_name_stats}**: {count_stats}回 ({percentage:.1f}%)")
            else:
                st.caption("モデル使用情報はありません。")
        
        with detail_col2:
            st.markdown("**📅 データ期間**")
            date_range_dict = data_stats.get('date_range')
            if date_range_dict and date_range_dict.get('start') and date_range_dict.get('end'):
                st.write(f"最初の日付: {format_timestamp(date_range_dict['start'])[:10]}")
                st.write(f"最後の日付: {format_timestamp(date_range_dict['end'])[:10]}")
            else:
                st.caption("日付範囲情報はありません。")
            
            st.markdown("**💾 データ整合性**")
            if hasattr(data_manager_class, 'validate_data_integrity'):
                integrity_result = data_manager_class.validate_data_integrity()
                if integrity_result.get('is_valid'):
                    st.success("✅ データは正常です。")
                else:
                    st.warning("⚠️ データに問題が見つかりました。")
                    for issue_item in integrity_result.get('issues', []): st.error(f"- 問題: {issue_item}")
                    for warning_item in integrity_result.get('warnings', []): st.warning(f"- 警告: {warning_item}")
            else:
                st.info("データ整合性チェック機能は利用できません。")


def format_timestamp(timestamp: Any) -> str:
    """タイムスタンプを適切な文字列形式にフォーマットする。"""
    if isinstance(timestamp, datetime.datetime):
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(timestamp, str):
        try:
            ts_processed = timestamp.replace('Z', '+00:00')
            if '.' in ts_processed:
                parts = ts_processed.split('.')
                if len(parts) == 2:
                    sec_and_tz = parts[1]
                    tz_index = -1
                    plus_idx = sec_and_tz.rfind('+')
                    minus_idx = sec_and_tz.rfind('-')
                    if plus_idx != -1 and minus_idx != -1: tz_index = max(plus_idx, minus_idx)
                    elif plus_idx != -1: tz_index = plus_idx
                    elif minus_idx != -1: tz_index = minus_idx
                    if tz_index > 0:
                        microsec_part = sec_and_tz[:tz_index]
                        tz_part = sec_and_tz[tz_index:]
                        ts_processed = f"{parts[0]}.{microsec_part[:6]}{tz_part}"
                    elif tz_index == -1 and len(sec_and_tz) > 6 :
                         ts_processed = f"{parts[0]}.{sec_and_tz[:6]}"
            dt_object = datetime.datetime.fromisoformat(ts_processed)
            return dt_object.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            if len(timestamp) >= 19:
                try:
                    datetime.datetime.strptime(timestamp[:19], '%Y-%m-%d %H:%M:%S')
                    return timestamp[:19]
                except ValueError: pass
            return timestamp
    return str(timestamp)


def render_branch_selector(available_branches: List[str], current_branch: str, key: str = "branch_selector_ui_comp"):
    """ブランチ選択用UIコンポーネント"""
    current_idx = 0
    if not available_branches:
        st.caption("利用可能なブランチがありません。")
        return st.session_state.get('current_branch', 'main') # フォールバック

    try:
        current_idx = available_branches.index(current_branch)
    except ValueError:
        if available_branches:
            st.warning(f"現在のブランチ '{current_branch}' は利用できません。'{available_branches[0]}' に切り替えます。")
            st.session_state.current_branch = available_branches[0] # セッション更新
            # この後リランが必要
            # st.rerun() # ここでリランすると無限ループの可能性があるので注意。呼び出し側で制御。
        else:
             st.error("ブランチリストが空で、現在のブランチも設定できません。")
             return st.session_state.get('current_branch', 'main') # フォールバック

    return st.selectbox(
        "現在のブランチ:",
        available_branches,
        index=current_idx,
        key=key,
        help="操作対象のブランチを選択します。"
    )


def render_execution_selector(executions: List[Dict[str, Any]], label: str, key: str):
    """実行記録選択用UIコンポーネント"""
    if not executions:
        st.caption(f"{label} 対象の実行記録がありません。")
        return None

    execution_options = [
        f"{ex.get('commit_hash', 'N/A')[:8]} - {ex.get('commit_message', 'メモなし')} ({format_timestamp(ex.get('timestamp',''))[:10]})"
        for ex in executions
    ]
    
    selected_idx = st.selectbox(
        label,
        range(len(execution_options)),
        format_func=lambda x_idx: execution_options[x_idx],
        key=key,
        help="比較や詳細表示のための実行記録を選択します。"
    )
    return executions[selected_idx] if selected_idx is not None and 0 <= selected_idx < len(executions) else None


def render_prompt_details(execution: Dict[str, Any]):
    """単一実行記録のプロンプト関連詳細を表示"""
    st.markdown("**📋 プロンプトと評価基準の詳細**")
    prompt_col, criteria_col = st.columns(2)
    with prompt_col:
        st.markdown("##### プロンプト情報")
        if execution.get('execution_mode') == "テンプレート + データ入力":
            st.markdown("**テンプレート:**")
            st.code(execution.get('prompt_template', '情報なし'), language='text')
            st.markdown("**入力データ:**")
            st.code(execution.get('user_input', '情報なし'), language='text')
        st.markdown("**最終プロンプト (LLMへ送信):**")
        st.code(execution.get('final_prompt', '情報なし'), language='text')
    with criteria_col:
        st.markdown("##### 評価基準")
        st.code(execution.get('criteria', '情報なし'), language='text')


def render_workflow_card(workflow: Dict[str, Any], show_actions: bool = True) -> Optional[str]:
    """ワークフロー情報カードを表示し、選択されたアクションを返す"""
    created_at_str = workflow.get('created_at', '')
    created_date = format_timestamp(created_at_str)[:10] if created_at_str else '日付不明'
    step_count = len(workflow.get('steps', []))
    var_count = len(workflow.get('global_variables', []))
    workflow_name_card = workflow.get('name', '無名ワークフロー')
    workflow_desc_card = workflow.get('description', '説明なし')
    
    card_col1, card_col2 = st.columns([3, 1])
    with card_col1:
        st.markdown(f"""
        <div class="workflow-card">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <span style="font-size: 1.2em;">🔄</span><strong>{workflow_name_card}</strong>
            </div>
            <div style="color: #666; font-size: 0.9rem; margin-bottom: 0.5rem;">{workflow_desc_card}</div>
            <div style="color: #888; font-size: 0.8rem;">📋 {step_count}ステップ | 📥 {var_count}変数 | 📅 {created_date}</div>
        </div>""", unsafe_allow_html=True)
        
    action_selected: Optional[str] = None
    with card_col2:
        if show_actions:
            workflow_id_card = workflow.get('id', workflow.get('workflow_id', f"unknown_wf_{workflow_name_card}_{str(datetime.datetime.now().timestamp())}"))
            if st.button("🚀 実行", key=f"run_wf_card_{workflow_id_card}", use_container_width=True): action_selected = "run"
            if st.button("✏️ 編集", key=f"edit_wf_card_{workflow_id_card}", use_container_width=True): action_selected = "edit"
            if st.button("🗑️ 削除", key=f"delete_wf_card_{workflow_id_card}", use_container_width=True): action_selected = "delete"
    return action_selected


def render_workflow_progress(current_step: int, total_steps: int, step_names: List[str], current_step_name: str = ""):
    """ワークフロー実行の全体進捗を表示"""
    progress_val = float(current_step) / total_steps if total_steps > 0 else 0.0
    st.progress(progress_val)
    step_info_col1, step_info_col2 = st.columns([2, 1])
    with step_info_col1:
        effective_step_name = current_step_name if current_step_name else (step_names[current_step-1] if 0 < current_step <= len(step_names) else f'ステップ {current_step}')
        st.markdown(f"**実行中:** {effective_step_name}")
    with step_info_col2:
        st.markdown(f"**{current_step}/{total_steps}** 完了")
    with st.expander("📋 全ステップの状況を見る", expanded=False):
        for i, name_of_step in enumerate(step_names):
            idx_plus_one = i + 1
            if idx_plus_one < current_step: st.success(f"✅ Step {idx_plus_one}: {name_of_step}")
            elif idx_plus_one == current_step: st.info(f"🔄 Step {idx_plus_one}: {name_of_step} (現在のターゲット)")
            else: st.markdown(f"⏸️ Step {idx_plus_one}: {name_of_step} (待機中)")


def render_workflow_result_tabs(result: WorkflowExecutionResult, debug_mode: bool = False):
    """ワークフロー実行結果をタブ形式で詳細表示"""
    if not getattr(result, 'success', False):
        error_message_result = getattr(result, 'error', 'ワークフロー実行中に不明なエラーが発生しました。')
        st.error(f"❌ ワークフロー実行失敗: {error_message_result}")
        if hasattr(result, 'steps') and result.steps:
            st.markdown("#### 失敗前のステップ結果:")
            for step_item_fail in result.steps:
                 render_workflow_step_card(step_item_fail, step_item_fail.step_number, show_prompt=debug_mode)
        return

    workflow_name_result = getattr(result, 'workflow_name', '無名ワークフロー')
    st.success(f"✅ ワークフロー「{workflow_name_result}」が正常に完了しました。")
    render_workflow_execution_summary(result)
    st.markdown("---")

    with st.expander("💡 コストとトークンの詳細メトリクス", expanded=False):
        detail_col_cost, detail_col_token = st.columns(2)
        with detail_col_cost:
            st.markdown("##### 💰 コスト詳細")
            st.markdown(f"- **総コスト**: `{format_detailed_cost_display(getattr(result, 'total_cost', 0.0))}`")
            steps_list_cost = getattr(result, 'steps', [])
            if steps_list_cost:
                avg_cost_per_step = getattr(result, 'total_cost', 0.0) / len(steps_list_cost) if len(steps_list_cost) > 0 else 0.0
                st.markdown(f"- **平均ステップコスト**: `{format_detailed_cost_display(avg_cost_per_step)}`")
                st.markdown("**ステップ別コスト内訳:**")
                for step_item_cost in steps_list_cost:
                    step_cost_str = format_detailed_cost_display(getattr(step_item_cost, 'cost', 0.0))
                    st.markdown(f"- Step {getattr(step_item_cost, 'step_number', '?')}: `{step_cost_str}`")
        with detail_col_token:
            st.markdown("##### 🔢 トークン詳細")
            st.markdown(f"- **総トークン数**: `{getattr(result, 'total_tokens', 0):,}`")
            steps_list_token = getattr(result, 'steps', [])
            if steps_list_token:
                avg_tokens_per_step = getattr(result, 'total_tokens', 0) // len(steps_list_token) if len(steps_list_token) > 0 else 0
                st.markdown(f"- **平均ステップトークン数**: `{avg_tokens_per_step:,}`")
                st.markdown("**ステップ別トークン内訳:**")
                for step_item_token in steps_list_token:
                    st.markdown(f"- Step {getattr(step_item_token, 'step_number', '?')}: `{getattr(step_item_token, 'tokens', 0):,}`")
    
    tab_titles_list = ["🎯 最終結果", "📋 ステップ詳細"]
    tab_titles_list.append("🐛 デバッグ情報" if debug_mode else "📊 統計情報")
    tab_objects_list = st.tabs(tab_titles_list)
    
    with tab_objects_list[0]:
        st.markdown("### 🎯 最終出力")
        final_output_str = getattr(result, 'final_output', "")
        if final_output_str:
            char_count_final = len(final_output_str)
            word_count_final = len(final_output_str.split())
            st.caption(f"📝 {char_count_final:,} 文字, {word_count_final:,} 単語")
        st.text_area("最終出力結果", value=final_output_str, height=400, key="workflow_final_result_textarea_comp")
        action_col_copy, action_col_download = st.columns(2)
        with action_col_copy:
            if st.button("📋 結果をクリップボードにコピー", key="copy_final_workflow_output_button_comp"):
                st.code(final_output_str, language='text')
                st.toast("結果が上記のコードブロックに表示されました。手動でコピーしてください。")
        with action_col_download:
            if final_output_str:
                st.download_button(
                    label="💾 テキストファイルでダウンロード", data=final_output_str,
                    file_name=f"workflow_result_{getattr(result, 'execution_id', 'unknown_exec_id')}.txt",
                    mime="text/plain", use_container_width=True, key="download_final_workflow_output_button_comp"
                )
    
    with tab_objects_list[1]:
        st.markdown("### 📋 各ステップの詳細結果")
        steps_data_list = getattr(result, 'steps', [])
        if steps_data_list:
            step_summary_df_data = []
            for step_item_summary in steps_data_list:
                step_summary_df_data.append({
                    'ステップ番号': getattr(step_item_summary, 'step_number', '?'),
                    'ステップ名': getattr(step_item_summary, 'step_name', '無名'),
                    'コスト(USD)': format_detailed_cost_display(getattr(step_item_summary, 'cost', 0.0)),
                    'トークン数': f"{getattr(step_item_summary, 'tokens', 0):,}",
                    '実行時間(秒)': f"{getattr(step_item_summary, 'execution_time', 0.0):.1f}",
                    '出力文字数': len(getattr(step_item_summary, 'response', "") or "")
                })
            df_summary = pd.DataFrame(step_summary_df_data)
            st.dataframe(df_summary, use_container_width=True, hide_index=True)
            st.markdown("---")
        for i, step_result_detail in enumerate(steps_data_list):
            render_workflow_step_card(step_result_detail, step_result_detail.step_number, show_prompt=debug_mode)

    with tab_objects_list[2]:
        if debug_mode:
            st.markdown("### 🐛 デバッグ情報")
            debug_info_dict = {
                'execution_id': getattr(result, 'execution_id', None),
                'status': str(getattr(result, 'status', None)),
                'duration_seconds': getattr(result, 'duration_seconds', None),
                'total_cost': getattr(result, 'total_cost', None),
                'total_tokens': getattr(result, 'total_tokens', None),
                'workflow_name': getattr(result, 'workflow_name', None),
                'start_time': format_timestamp(getattr(result, 'start_time', None)),
                'end_time': format_timestamp(getattr(result, 'end_time', None)),
                'error_message': getattr(result, 'error', None),
                'metadata': getattr(result, 'metadata', {})
            }
            st.json(debug_info_dict)
        else:
            st.markdown("### 📊 実行統計")
            steps_list_stats = getattr(result, 'steps', [])
            if steps_list_stats:
                stats_cost_col, stats_token_col = st.columns(2)
                with stats_cost_col:
                    st.markdown("#### 💰 コスト分析")
                    if steps_list_stats:
                        most_expensive_step = max(steps_list_stats, key=lambda s: getattr(s, 'cost', 0.0))
                        st.markdown(f"**最もコストが高いステップ:** Step {getattr(most_expensive_step, 'step_number', '?')} ({format_detailed_cost_display(getattr(most_expensive_step, 'cost', 0.0))})")
                with stats_token_col:
                    st.markdown("#### 🔢 トークン分析")
                    if steps_list_stats:
                        most_tokens_step = max(steps_list_stats, key=lambda s: getattr(s, 'tokens', 0))
                        st.markdown(f"**最もトークン数が多いステップ:** Step {getattr(most_tokens_step, 'step_number', '?')} ({getattr(most_tokens_step, 'tokens', 0):,})")
                st.markdown("#### ⚡ パフォーマンス分析")
                perf_time_col, perf_efficiency_col, perf_throughput_col = st.columns(3)
                with perf_time_col:
                    actual_processing_time = sum(getattr(s, 'execution_time', 0.0) for s in steps_list_stats)
                    st.metric("ステップ合計処理時間", f"{actual_processing_time:.1f}秒", help="各ステップの純粋な実行時間の合計")
                with perf_efficiency_col:
                    total_tokens_val_stats = getattr(result, 'total_tokens', 0)
                    total_cost_val_stats = getattr(result, 'total_cost', 0.0)
                    if total_tokens_val_stats > 0:
                        cost_per_1m_tokens = (total_cost_val_stats / total_tokens_val_stats) * 1_000_000
                        st.metric("コスト効率", f"${cost_per_1m_tokens:.2f} / 1M トークン", help="100万トークンあたりのコスト")
                    else: st.metric("コスト効率", "N/A (トークン0)", help="トークン数が0のため計算不可")
                with perf_throughput_col:
                    duration_val_stats = getattr(result, 'duration_seconds', 0.0)
                    if duration_val_stats > 0:
                        tokens_per_second = getattr(result, 'total_tokens', 0) / duration_val_stats
                        st.metric("スループット", f"{tokens_per_second:.0f} トークン/秒", help="ワークフロー全体の秒間処理トークン数")
                    else: st.metric("スループット", "N/A (時間0)", help="実行時間が0のため計算不可")
            else: st.caption("ステップ情報がないため、詳細な統計は表示できません。")


def render_variable_substitution_help():
    """変数置換（フィルター含む）のヘルプ情報を表示"""
    with st.expander("💡 変数置換とフィルターの使い方", expanded=False):
        st.markdown("""
        プロンプトテンプレート内では、中括弧 `{}` を使って変数を埋め込むことができます。
        さらに、パイプ `|` を使ってフィルターを適用し、値を加工できます。

        #### 基本的な変数参照
        -   `{variable_name}`: グローバル入力変数 `variable_name` の値を参照します。
        -   `{step_N_output}`: `N`番目のステップ（例: `step_1_output`）の出力結果全体を参照します。

        #### セクション抽出 (例)
        -   `{step_1_output.要約}`: `step_1_output` の中から「要約」という見出し（例: `### 要約`）に続く内容を抽出します。
            *(注意: セクション抽出は実験的な機能であり、マークダウンの見出し構造に依存します。)*

        #### 利用可能なフィルター
        -   `{variable|default:デフォルト値}`: `variable` が空または未定義の場合に「デフォルト値」を使用します。
            例: `{user_query|default:一般的な質問}`
        -   `{variable|truncate:100}`: `variable` の値を最初の100文字に切り詰め、「...」を付加します。
            例: `{long_text|truncate:50}`
        -   `{variable|upper}`: `variable` の値をすべて大文字に変換します。
        -   `{variable|lower}`: `variable` の値をすべて小文字に変換します。
        -   `{variable|strip}`: `variable` の値の前後の空白文字を除去します。
        -   `{variable|first_line}`: `variable` の値の最初の行のみを取得します。

        #### フィルターの組み合わせ
        フィルターは複数組み合わせることができます。左から順に適用されます。
        例: `{user_input|strip|truncate:200|default:入力がありませんでした}`
        この例では、まず空白を除去し、次に200文字に切り詰め、もし結果が空ならデフォルト値を設定します。

        #### 使用例
        ```plaintext
        # ワークフローのグローバル入力
        # document_title = "AI技術の最新動向レポート"
        # user_instructions = "特に倫理的側面について強調して"

        # ステップ1のプロンプトテンプレート
        # 文書「{document_title}」を要約してください。指示: {user_instructions|default:特になし}
        #
        # ステップ2のプロンプトテンプレート (step_1_outputを参照)
        # 前のステップの要約は以下の通りです。
        # ---
        # {step_1_output|strip|truncate:300}
        # ---
        # この要約に基づいて、重要なポイントを3点挙げてください。
        ```
        """)


def render_error_details(error_type: str, error_message: str, suggestions: List[str]):
    """エラータイプ、メッセージ、推奨される対処法を構造化して表示"""
    st.error(f"**エラータイプ:** {error_type}")
    with st.expander("エラーメッセージ詳細を見る", expanded=False):
        st.code(error_message, language='text')
    if suggestions:
        st.markdown("##### 💡 推奨される対処法:")
        for i, suggestion_item in enumerate(suggestions, 1):
            st.markdown(f"{i}. {suggestion_item}")
    else:
        st.markdown("💡 具体的な対処法の提案はありません。エラーメッセージを確認してください。")


def render_workflow_template_selector() -> Optional[str]:
    """定義済みのワークフローテンプレートを選択するためのUIを表示し、選択されたテンプレートIDを返す"""
    st.markdown("### 📋 テンプレートから新規ワークフローを開始")
    st.caption("よく使われるパターンのテンプレートを選んで、カスタマイズを始めましょう。")

    predefined_templates = {
        "document_analysis_basic": {
            "name": "基本文書分析フロー",
            "description": "文書を読み込み、要約し、キーワードを抽出する基本的な3ステップのフローです。",
            "steps_count": 3,
            "variables_list": ["document_text"]
        },
        "research_summary_generation": {
            "name": "研究トピック要約フロー",
            "description": "指定された研究トピックに関する情報を収集・整理し（模擬）、要約を生成します。",
            "steps_count": 3,
            "variables_list": ["research_topic", "source_urls"]
        },
        "customer_feedback_analysis": {
            "name": "顧客フィードバック分析",
            "description": "顧客からのフィードバックテキストを分析し、感情分類と主要な意見の抽出を行います。",
            "steps_count": 3,
            "variables_list": ["feedback_text_list"]
        },
        "code_documentation_generation": {
            "name": "コード説明文生成フロー",
            "description": "提供されたコードスニペットの機能説明と使用例を生成します。",
            "steps_count": 2,
            "variables_list": ["code_snippet", "programming_language"]
        }
    }
    
    template_cols_list = st.columns(2)
    selected_template_id: Optional[str] = None

    for i, (template_key, template_details) in enumerate(predefined_templates.items()):
        current_col = template_cols_list[i % 2]
        with current_col:
            with st.container(border=True):
                # SyntaxError箇所を修正: HTMLコメントを標準形式に
                st.markdown(f"""
                <div class="template-card-content"> <!-- CSSでスタイルを適用するためのクラス -->
                    <h4>{template_details['name']}</h4>
                    <p style="color: #555; font-size: 0.9em;">{template_details['description']}</p>
                    <div style="font-size: 0.8em; color: #777;">
                        <span title="ステップ数">📋 {template_details['steps_count']} ステップ</span> | 
                        <span title="必要な入力変数">📥 {len(template_details['variables_list'])} 変数</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"「{template_details['name']}」を使用", key=f"use_template_button_{template_key}", use_container_width=True):
                    selected_template_id = template_key
    
    if selected_template_id:
        st.success(f"テンプレート「{predefined_templates[selected_template_id]['name']}」が選択されました。上のビルダーで内容を調整してください。")
    
    return selected_template_id


def get_additional_styles() -> str:
    """UIコンポーネント用の追加CSSスタイルを定義する"""
    return """
    <style>
    /* 実行記録カードのスタイル */
    .commit-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0; /* Tailwind gray-300 */
        border-radius: 0.75rem; /* 12px */
        padding: 1rem; /* 16px */
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
    }
    .branch-tag {
        background-color: #e2e8f0; /* Tailwind gray-200 */
        color: #4a5568; /* Tailwind gray-700 */
        padding: 0.2em 0.5em;
        border-radius: 0.25rem; /* 4px */
        font-size: 0.8em;
        font-weight: 600;
    }
    .commit-hash {
        font-family: monospace;
        color: #718096; /* Tailwind gray-500 */
        font-size: 0.9em;
    }

    /* ワークフローカードのスタイル */
    .workflow-card {
        background: white;
        border: 1px solid #e2e8f0; /* Tailwind gray-300 */
        border-radius: 12px; /* 0.75rem */
        padding: 1rem; /* 16px */
        margin: 0.5rem 0; /* 8px上下マージン */
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease-in-out;
    }
    .workflow-card:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px); /* 少し浮き上がる効果 */
    }
    
    /* ワークフローテンプレートカードのスタイル */
    .template-card-content { /* template-card から変更 */
        /* st.container(border=True) を使うため、背景や枠線はStreamlit側で設定 */
        padding: 0.5rem; /* 内側のパディングを少し調整 */
    }
    .template-card-content h4 {
        margin-top: 0;
        margin-bottom: 0.5rem; /* 8px */
        color: #2d3748; /* Tailwind gray-800 */
        font-size: 1.1em;
    }
    .template-card-content p {
        margin-bottom: 0.5rem; /* 8px */
    }
    </style>
    """

# ============================================
# ワークフロー専用コンポーネント (統合・調整済み)
# ============================================

# ui/components.py

import time # time モジュールのインポートを確認（なければ追加）
# ... (他のインポート) ...

def render_workflow_step_card(step_result: StepResult, 
                              step_number: int, 
                              show_prompt: bool = False, 
                              workflow_execution_id: Optional[str] = None): # <<<--- workflow_execution_id 引数を追加
    """特定のワークフローステップの結果をカード形式で表示する。 (統合・調整版)"""
    is_success = getattr(step_result, 'success', False)
    status_icon = "✅" if is_success else "❌"
    status_color = "#48bb78" if is_success else "#f56565"
    
    step_name_display = getattr(step_result, 'step_name', f'ステップ {step_number}')
    
    exec_time_val = getattr(step_result, 'execution_time', 0.0)
    tokens_val = getattr(step_result, 'tokens', 0)
    cost_val = getattr(step_result, 'cost', 0.0)
    model_name_val = getattr(step_result, 'model_name', None)

    # --- ユニークなキー接尾辞の生成 ---
    key_suffix = workflow_execution_id if workflow_execution_id else str(time.time()).replace('.', '')
    # ---------------------------------

    card_header_html = f"""
        <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
            <span style="font-size: 1.3em; margin-right: 0.5rem; color: {status_color};">{status_icon}</span>
            <h5 style="margin: 0; color: {status_color};">{st.markdown(f"Step {step_number}: {step_name_display}")}</h5>
        </div>
    """
    metrics_html = f"""
        <div style="font-size: 0.85rem; color: #555; margin-left: 2.3rem;">
            実行時間: {exec_time_val:.1f}秒 | 
            トークン: {tokens_val:,} | 
            コスト: ${cost_val:.6f}
            {f"| モデル: {model_name_val}" if model_name_val else ""}
        </div>
    """
    
    # ui/components.py の render_workflow_step_card 関数内 (修正箇所のみ)

# ... (関数定義と前半のコード) ...

    with st.container(border=True):
        st.markdown(card_header_html, unsafe_allow_html=True)
        st.markdown(metrics_html, unsafe_allow_html=True)

        if is_success:
            response_text_val = getattr(step_result, 'response', "応答なし")
            # expanderのkey引数を削除
            with st.expander(f"Step {step_number} の出力を見る", expanded=False): 
                char_count_step = len(response_text_val)
                word_count_step = len(response_text_val.split())
                st.caption(f"📝 {char_count_step:,} 文字, {word_count_step:,} 単語")
                st.text_area(f"出力内容##{step_number}", value=response_text_val, height=200,
                            key=f"textarea_step_output_{step_number}_{key_suffix}", 
                            disabled=True, label_visibility="collapsed")
            
            if show_prompt:
                prompt_text_val = getattr(step_result, 'prompt', "プロンプト情報なし")
                if st.button(f"Step {step_number} のプロンプトを表示", 
                             key=f"button_show_prompt_{step_number}_{key_suffix}"):
                    # expanderのkey引数を削除
                    with st.expander(f"Step {step_number} 使用プロンプト", expanded=True):
                        st.code(prompt_text_val, language='text')
        else:
            error_text_val = str(getattr(step_result, 'error', '詳細不明のエラー'))
            st.error(f"このステップでエラーが発生しました: {error_text_val}")


def render_workflow_execution_summary(result: WorkflowExecutionResult):
    """ワークフロー全体の実行結果サマリーを表示する。(統合・調整版)"""
    is_success_result = getattr(result, 'success', False)
    workflow_name_summary = getattr(result, 'workflow_name', '無名ワークフロー')

    if is_success_result:
        st.success(f"🎉 ワークフロー「{workflow_name_summary}」が正常に完了しました！")
    else:
        st.error(f"❌ ワークフロー「{workflow_name_summary}」の実行に失敗しました。")
        error_message_summary = getattr(result, 'error', None)
        if error_message_summary:
            st.caption(f"主なエラー原因: {str(error_message_summary)}")

    summary_metric_col1, summary_metric_col2, summary_metric_col3, summary_metric_col4 = st.columns(4)
    with summary_metric_col1:
        st.metric("総実行時間", f"{getattr(result, 'duration_seconds', 0.0):.1f}秒")
    with summary_metric_col2:
        steps_list_summary = getattr(result, 'steps', [])
        completed_steps_count_summary = len([s for s in steps_list_summary if getattr(s, 'success', False)])
        st.metric("完了ステップ数", f"{completed_steps_count_summary}/{len(steps_list_summary)}")
    with summary_metric_col3:
        st.metric("総コスト (USD)", format_detailed_cost_display(getattr(result, 'total_cost', 0.0)))
    with summary_metric_col4:
        st.metric("総トークン数", format_tokens_display(getattr(result, 'total_tokens', 0)))


def render_workflow_live_step(step_number: int, step_name: str, status: str = "running") -> st.empty:
    """ワークフロー実行中の特定のステップのライブステータスを表示する。
       UI更新のためにStreamlitのemptyプレースホルダーを返す。(統合・調整版)
    """
    live_step_placeholder = st.empty()
    with live_step_placeholder.container():
        if status == "running":
            st.info(f"🔄 Step {step_number}: 「{step_name}」を実行中...")
        elif status == "completed":
            st.success(f"✅ Step {step_number}: 「{step_name}」- 完了 (ライブ情報)")
        elif status == "failed":
            st.error(f"❌ Step {step_number}: 「{step_name}」- 失敗 (ライブ情報)")
    return live_step_placeholder