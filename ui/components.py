"""
改善されたUIコンポーネント
"""

import streamlit as st
import datetime
from typing import Dict, List, Any, Optional
from ui.styles import get_response_box_html, get_evaluation_box_html, get_metric_card_html


def render_response_box(content: str, title: str = "🤖 回答", border_color: str = "#667eea"):
    """LLMの回答を表示するボックス"""
    st.markdown(f"**{title}**")
    st.markdown(get_response_box_html(content, border_color), unsafe_allow_html=True)


def render_evaluation_box(content: str, title: str = "⭐ 評価"):
    """評価結果を表示するボックス"""
    st.markdown(f"**{title}**")
    st.markdown(get_evaluation_box_html(content), unsafe_allow_html=True)


def render_cost_metrics(execution_cost: float, evaluation_cost: float, total_cost: float, 
                       execution_tokens: int, evaluation_tokens: int):
    """コスト情報を表示"""
    st.subheader("💰 コスト")
    
    cost_col1, cost_col2, cost_col3 = st.columns(3)
    
    with cost_col1:
        st.markdown(get_metric_card_html(
            "実行コスト", 
            f"${execution_cost:.6f}",
            f"{execution_tokens:,} tokens"
        ), unsafe_allow_html=True)
    
    with cost_col2:
        st.markdown(get_metric_card_html(
            "評価コスト", 
            f"${evaluation_cost:.6f}",
            f"{evaluation_tokens:,} tokens"
        ), unsafe_allow_html=True)
    
    with cost_col3:
        st.markdown(get_metric_card_html(
            "総コスト", 
            f"${total_cost:.6f}",
            f"{execution_tokens + evaluation_tokens:,} tokens"
        ), unsafe_allow_html=True)


def render_execution_card(execution: Dict[str, Any], tags: List[str] = None, show_details: bool = True):
    """実行記録カード"""
    
    # 基本情報
    timestamp = format_timestamp(execution['timestamp'])
    exec_hash = execution['commit_hash']
    exec_memo = execution.get('commit_message', 'メモなし')
    branch = execution.get('branch', 'unknown')
    model_name = execution.get('model_name', 'Unknown')
    
    # ヘッダー部分
    header_col1, header_col2, header_col3 = st.columns([3, 1, 1])
    
    with header_col1:
        st.markdown(f"""
        <div class="commit-card">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <span class="branch-tag">{branch}</span>
                <strong>{exec_memo}</strong>
            </div>
            <div style="color: #666; font-size: 0.9rem;">
                🤖 {model_name} | 📅 {timestamp[:16]} | <span class="commit-hash">{exec_hash}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with header_col2:
        st.metric("コスト", f"${execution['execution_cost']:.4f}")
    
    with header_col3:
        total_tokens = execution['execution_tokens'] + execution['evaluation_tokens']
        st.metric("トークン", f"{total_tokens:,}")
    
    if show_details:
        if st.expander("📋 詳細を表示"):
            detail_col1, detail_col2 = st.columns([2, 1])
            
            with detail_col1:
                render_response_box(execution['response'])
                render_evaluation_box(execution['evaluation'])
            
            with detail_col2:
                st.markdown("**📊 メトリクス**")
                st.metric("実行トークン", f"{execution['execution_tokens']:,}")
                st.metric("評価トークン", f"{execution['evaluation_tokens']:,}")
                st.metric("実行コスト", f"${execution['execution_cost']:.6f}")
                
                if st.button("📝 プロンプト確認", key=f"prompt_{exec_hash}"):
                    st.code(execution.get('final_prompt', ''), language=None)


def render_comparison_metrics(exec1: Dict[str, Any], exec2: Dict[str, Any]):
    """比較メトリクス"""
    st.subheader("📊 比較")
    
    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
    
    with metrics_col1:
        cost_diff = exec2['execution_cost'] - exec1['execution_cost']
        st.metric("実行コスト", f"${exec2['execution_cost']:.6f}", f"{cost_diff:+.6f}")
    
    with metrics_col2:
        token_diff = (exec2['execution_tokens'] + exec2['evaluation_tokens']) - (exec1['execution_tokens'] + exec1['evaluation_tokens'])
        st.metric("総トークン", f"{exec2['execution_tokens'] + exec2['evaluation_tokens']:,}", f"{token_diff:+,}")
    
    with metrics_col3:
        exec_token_diff = exec2['execution_tokens'] - exec1['execution_tokens']
        st.metric("実行トークン", f"{exec2['execution_tokens']:,}", f"{exec_token_diff:+,}")
    
    with metrics_col4:
        eval_token_diff = exec2['evaluation_tokens'] - exec1['evaluation_tokens']
        st.metric("評価トークン", f"{exec2['evaluation_tokens']:,}", f"{eval_token_diff:+,}")


def render_comparison_responses(exec1: Dict[str, Any], exec2: Dict[str, Any]):
    """回答比較"""
    st.subheader("🤖 回答比較")
    
    response_col1, response_col2 = st.columns(2)
    
    with response_col1:
        render_response_box(
            exec1['response'], 
            f"比較元 ({exec1['commit_hash'][:8]})",
            "#667eea"
        )
    
    with response_col2:
        render_response_box(
            exec2['response'], 
            f"比較先 ({exec2['commit_hash'][:8]})",
            "#f5576c"
        )


def render_comparison_evaluations(exec1: Dict[str, Any], exec2: Dict[str, Any]):
    """評価比較"""
    st.subheader("⭐ 評価比較")
    
    eval_col1, eval_col2 = st.columns(2)
    
    with eval_col1:
        render_evaluation_box(
            exec1['evaluation'], 
            f"比較元 ({exec1['commit_hash'][:8]})"
        )
    
    with eval_col2:
        render_evaluation_box(
            exec2['evaluation'], 
            f"比較先 ({exec2['commit_hash'][:8]})"
        )


def render_export_section(data_manager_class):
    """エクスポートセクション"""
    st.subheader("📤 エクスポート")
    
    export_col1, export_col2 = st.columns(2)
    
    with export_col1:
        if st.button("💾 JSON (完全)", use_container_width=True):
            json_data = data_manager_class.export_to_json(include_metadata=True)
            filename = data_manager_class.get_file_suggestion("json")
            st.download_button("⬇️ ダウンロード", json_data, filename, "application/json")
    
    with export_col2:
        if st.button("📊 CSV (データ)", use_container_width=True):
            csv_data = data_manager_class.export_to_csv()
            filename = data_manager_class.get_file_suggestion("csv")
            st.download_button("⬇️ ダウンロード", csv_data, filename, "text/csv")


def render_import_section(data_manager_class):
    """インポートセクション"""
    import json
    import pandas as pd
    
    st.subheader("📂 インポート")
    
    uploaded_file = st.file_uploader("ファイル選択", type=["json", "csv"])
    
    if uploaded_file is not None:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        try:
            if file_extension == 'json':
                history_data = json.load(uploaded_file)
                total_records = len(history_data.get('evaluation_history', []))
                st.info(f"📊 {total_records}件の記録")
                
                import_mode = st.radio("方法", ["完全置換", "追加"], horizontal=True)
                
                if st.button("📥 インポート"):
                    if import_mode == "完全置換":
                        result = data_manager_class.import_from_json(history_data)
                    else:
                        # 追加処理
                        current_data = {
                            'evaluation_history': st.session_state.evaluation_history,
                            'branches': st.session_state.branches,
                            'tags': st.session_state.tags,
                            'current_branch': st.session_state.current_branch
                        }
                        
                        current_data['evaluation_history'].extend(history_data.get('evaluation_history', []))
                        for branch, executions in history_data.get('branches', {}).items():
                            if branch not in current_data['branches']:
                                current_data['branches'][branch] = []
                            current_data['branches'][branch].extend(executions)
                        current_data['tags'].update(history_data.get('tags', {}))
                        
                        result = data_manager_class.import_from_json(current_data)
                    
                    if result['success']:
                        st.success(f"✅ {result['imported_count']}件をインポート")
                        st.rerun()
                    else:
                        st.error(f"❌ {result['error']}")
            
            elif file_extension == 'csv':
                df = pd.read_csv(uploaded_file)
                st.info(f"📊 {len(df)}件の記録")
                
                if st.button("📥 CSV インポート"):
                    result = data_manager_class.import_from_csv(df)
                    
                    if result['success']:
                        st.success(f"✅ {result['imported_count']}件をインポート")
                        st.rerun()
                    else:
                        st.error(f"❌ {result['error']}")
            
        except Exception as e:
            st.error(f"❌ ファイル読み込みエラー: {str(e)}")


def render_statistics_summary(global_stats: Dict[str, Any], data_stats: Dict[str, Any]):
    """統計サマリー"""
    stats_col1, stats_col2, stats_col3 = st.columns(3)
    
    with stats_col1:
        st.metric("ブランチ", global_stats['total_branches'])
    
    with stats_col2:
        st.metric("実行数", global_stats['total_executions'])
    
    with stats_col3:
        st.metric("総コスト", f"${global_stats['total_cost']:.4f}")


def render_detailed_statistics(data_stats: Dict[str, Any], data_manager_class):
    """詳細統計"""
    if st.expander("📊 詳細統計"):
        detail_col1, detail_col2 = st.columns(2)
        
        with detail_col1:
            st.markdown("**🤖 使用モデル**")
            if data_stats['models_used']:
                for model, count in data_stats['models_used'].items():
                    percentage = (count / data_stats['total_records']) * 100 if data_stats['total_records'] > 0 else 0
                    st.write(f"• {model}: {count}回 ({percentage:.1f}%)")
        
        with detail_col2:
            st.markdown("**📅 データ期間**")
            if data_stats['date_range']:
                st.write(f"開始: {data_stats['date_range']['start'][:10]}")
                st.write(f"終了: {data_stats['date_range']['end'][:10]}")
            
            # データ整合性
            integrity = data_manager_class.validate_data_integrity()
            if integrity['is_valid']:
                st.success("✅ データ正常")
            else:
                st.warning("⚠️ データに問題")


def format_timestamp(timestamp):
    """タイムスタンプをフォーマット"""
    if isinstance(timestamp, str):
        if 'T' in timestamp:
            try:
                dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                return timestamp[:19]
        return timestamp
    else:
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')


def render_branch_selector(available_branches: List[str], current_branch: str, key: str = "branch_selector"):
    """ブランチ選択"""
    current_index = available_branches.index(current_branch) if current_branch in available_branches else 0
    
    return st.selectbox(
        "ブランチ",
        available_branches,
        index=current_index,
        key=key
    )


def render_execution_selector(executions: List[Dict[str, Any]], label: str, key: str):
    """実行記録選択"""
    execution_options = [f"{execution['commit_hash'][:8]} - {execution.get('commit_message', 'メモなし')}" 
                        for execution in executions]
    
    return st.selectbox(
        label,
        range(len(execution_options)),
        format_func=lambda x: execution_options[x],
        key=key
    )


def render_prompt_details(execution: Dict[str, Any]):
    """プロンプト詳細"""
    st.markdown("**📋 詳細**")
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        if execution.get('execution_mode') == "テンプレート + データ入力":
            st.markdown("**テンプレート**")
            st.code(execution.get('prompt_template', ''), language=None)
            st.markdown("**データ**")
            st.code(execution.get('user_input', ''), language=None)
        
        st.markdown("**最終プロンプト**")
        st.code(execution.get('final_prompt', ''), language=None)
    
    with info_col2:
        st.markdown("**評価基準**")
        st.code(execution['criteria'], language=None)