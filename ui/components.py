"""
再利用可能UIコンポーネント
共通のUI要素を関数化して、コードの重複を削減
"""

import streamlit as st
import datetime
from typing import Dict, List, Any, Optional
from ui.styles import get_response_box_html, get_evaluation_box_html, get_metric_card_html


def render_response_box(content: str, title: str = "🤖 LLMの回答", border_color: str = "#667eea"):
    """
    LLMの回答を表示するボックス
    
    Args:
        content: 表示する内容
        title: ボックスのタイトル
        border_color: ボーダーの色
    """
    st.write(f"**{title}**")
    st.markdown(get_response_box_html(content, border_color), unsafe_allow_html=True)


def render_evaluation_box(content: str, title: str = "⭐ 評価結果"):
    """
    評価結果を表示するボックス
    
    Args:
        content: 評価内容
        title: ボックスのタイトル
    """
    st.write(f"**{title}**")
    st.markdown(get_evaluation_box_html(content), unsafe_allow_html=True)


def render_cost_metrics(execution_cost: float, evaluation_cost: float, total_cost: float, 
                       execution_tokens: int, evaluation_tokens: int):
    """
    コスト情報を3列レイアウトで表示
    
    Args:
        execution_cost: 実行コスト
        evaluation_cost: 評価コスト
        total_cost: 総コスト
        execution_tokens: 実行トークン数
        evaluation_tokens: 評価トークン数
    """
    st.subheader("💰 コスト情報")
    
    cost_col1, cost_col2, cost_col3 = st.columns(3)
    
    with cost_col1:
        st.markdown(get_metric_card_html(
            "実行コスト", 
            f"${execution_cost:.6f}",
            f"トークン: {execution_tokens:,}"
        ), unsafe_allow_html=True)
    
    with cost_col2:
        st.markdown(get_metric_card_html(
            "評価コスト（参考）", 
            f"${evaluation_cost:.6f}",
            f"トークン: {evaluation_tokens:,}"
        ), unsafe_allow_html=True)
    
    with cost_col3:
        st.markdown(get_metric_card_html(
            "総コスト（実行のみ）", 
            f"${total_cost:.6f}",
            f"実行トークン: {execution_tokens:,}"
        ), unsafe_allow_html=True)


def render_execution_card(execution: Dict[str, Any], tags: List[str] = None, show_details: bool = True):
    """
    実行記録をカード形式で表示
    
    Args:
        execution: 実行記録辞書
        tags: タグリスト
        show_details: 詳細表示するかどうか
    """
    from core import GitManager
    
    # 基本情報の取得
    timestamp = format_timestamp(execution['timestamp'])
    exec_hash = execution['commit_hash']
    exec_memo = execution.get('commit_message', 'メモなし')
    branch = execution.get('branch', 'unknown')
    model_name = execution.get('model_name', 'Unknown Model')
    
    # タグ情報の取得
    if tags is None:
        tags = GitManager.get_tags_for_commit(exec_hash)
    
    # カード表示
    st.markdown(f"""
    <div class="commit-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <div>
                <span class="branch-tag">{branch}</span>
                {' '.join([f'<span class="tag-label">{tag}</span>' for tag in tags])}
                <strong>{exec_memo}</strong>
                <br><small>🤖 {model_name}</small>
            </div>
            <span class="commit-hash">{exec_hash}</span>
        </div>
        <div style="color: #6c757d; font-size: 0.9rem;">
            📅 {timestamp} | 💰 ${execution['execution_cost']:.6f} | 🔢 {execution['execution_tokens'] + execution['evaluation_tokens']:,} tokens
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if show_details:
        # 詳細情報表示
        detail_col1, detail_col2 = st.columns([3, 1])
        
        with detail_col1:
            # 回答と評価結果
            render_response_box(execution['response'])
            render_evaluation_box(execution['evaluation'])
        
        with detail_col2:
            # メトリクス
            st.metric("実行トークン", f"{execution['execution_tokens']:,}")
            st.metric("評価トークン", f"{execution['evaluation_tokens']:,}")
            st.metric("実行コスト", f"${execution['execution_cost']:.6f}")
            st.metric("評価コスト（参考）", f"${execution['evaluation_cost']:.6f}")
        
        # プロンプト詳細情報
        render_prompt_details(execution)


def render_prompt_details(execution: Dict[str, Any]):
    """
    プロンプトの詳細情報を表示
    
    Args:
        execution: 実行記録辞書
    """
    st.write("**📋 詳細情報**")
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        # テンプレートモードの場合
        if execution.get('execution_mode') == "テンプレート + データ入力":
            st.write("**🔧 プロンプトテンプレート**")
            st.code(execution.get('prompt_template', ''), language=None)
            st.write("**📊 入力データ**")
            st.code(execution.get('user_input', ''), language=None)
        
        st.write("**📝 最終プロンプト**")
        st.code(execution.get('final_prompt', ''), language=None)
    
    with info_col2:
        st.write("**📋 評価基準**")
        st.code(execution['criteria'], language=None)


def render_comparison_metrics(exec1: Dict[str, Any], exec2: Dict[str, Any]):
    """
    2つの実行記録の比較メトリクスを表示
    
    Args:
        exec1: 比較元実行記録
        exec2: 比較先実行記録
    """
    st.subheader("📊 比較結果")
    
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
    """
    2つの実行記録の回答比較を表示
    
    Args:
        exec1: 比較元実行記録
        exec2: 比較先実行記録
    """
    st.subheader("🤖 LLMの回答比較")
    
    response_col1, response_col2 = st.columns(2)
    
    with response_col1:
        render_response_box(
            exec1['response'], 
            f"比較元 ({exec1['commit_hash']})",
            "#667eea"
        )
    
    with response_col2:
        render_response_box(
            exec2['response'], 
            f"比較先 ({exec2['commit_hash']})",
            "#f5576c"
        )


def render_comparison_evaluations(exec1: Dict[str, Any], exec2: Dict[str, Any]):
    """
    2つの実行記録の評価結果比較を表示
    
    Args:
        exec1: 比較元実行記録
        exec2: 比較先実行記録
    """
    st.subheader("⭐ 評価結果比較")
    
    eval_col1, eval_col2 = st.columns(2)
    
    with eval_col1:
        render_evaluation_box(
            exec1['evaluation'], 
            f"比較元 ({exec1['commit_hash']})"
        )
    
    with eval_col2:
        render_evaluation_box(
            exec2['evaluation'], 
            f"比較先 ({exec2['commit_hash']})"
        )


def render_branch_selector(available_branches: List[str], current_branch: str, key: str = "branch_selector"):
    """
    ブランチ選択セレクトボックス
    
    Args:
        available_branches: 利用可能なブランチリスト
        current_branch: 現在のブランチ
        key: セレクトボックスのキー
        
    Returns:
        選択されたブランチ名
    """
    current_index = available_branches.index(current_branch) if current_branch in available_branches else 0
    
    return st.selectbox(
        "ブランチを選択",
        available_branches,
        index=current_index,
        key=key
    )


def render_execution_selector(executions: List[Dict[str, Any]], label: str, key: str):
    """
    実行記録選択セレクトボックス
    
    Args:
        executions: 実行記録リスト
        label: ラベル
        key: セレクトボックスのキー
        
    Returns:
        選択されたインデックス
    """
    execution_options = [f"{execution['commit_hash']} - {execution.get('commit_message', 'メモなし')}" 
                        for execution in executions]
    
    return st.selectbox(
        label,
        range(len(execution_options)),
        format_func=lambda x: execution_options[x],
        key=key
    )


def render_export_section(data_manager_class):
    """
    エクスポートセクションをレンダリング
    
    Args:
        data_manager_class: DataManagerクラス
    """
    st.subheader("📤 エクスポート")
    
    export_format = st.radio(
        "エクスポート形式",
        ["JSON (完全バックアップ)", "CSV (データ分析用)"],
        horizontal=True
    )
    
    if export_format.startswith("JSON"):
        history_json = data_manager_class.export_to_json(include_metadata=True)
        filename = data_manager_class.get_file_suggestion("json")
        
        st.download_button(
            label="💾 JSON形式でダウンロード",
            data=history_json,
            file_name=filename,
            mime="application/json",
            help="完全なデータバックアップ（ブランチ、タグ情報含む）"
        )
    else:
        history_csv = data_manager_class.export_to_csv()
        filename = data_manager_class.get_file_suggestion("csv")
        
        st.download_button(
            label="📊 CSV形式でダウンロード",
            data=history_csv,
            file_name=filename,
            mime="text/csv",
            help="データ分析用（Excel、Google Sheetsで利用可能）"
        )


def render_import_section(data_manager_class):
    """
    インポートセクションをレンダリング
    
    Args:
        data_manager_class: DataManagerクラス
    """
    import json
    import pandas as pd
    
    st.subheader("📂 インポート")
    
    uploaded_file = st.file_uploader(
        "ファイルを選択",
        type=["json", "csv"],
        help="JSONファイル（完全復元）またはCSVファイル（基本データのみ）を読み込みます"
    )
    
    if uploaded_file is not None:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        try:
            if file_extension == 'json':
                history_data = json.load(uploaded_file)
                
                total_records = len(history_data.get('evaluation_history', []))
                export_time = history_data.get('export_timestamp', 'Unknown')
                st.info(f"📊 {total_records}件の記録\n📅 エクスポート日時: {export_time}")
                
                import_mode = st.radio(
                    "インポート方法",
                    ["完全置換 (既存データを削除)", "追加 (既存データに追加)"],
                    key="json_import_mode"
                )
                
                if st.button("📥 JSON履歴をインポート"):
                    if import_mode.startswith("完全置換"):
                        result = data_manager_class.import_from_json(history_data)
                    else:
                        # 追加モード処理
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
                        st.success(f"✅ JSON履歴をインポートしました！（{result['imported_count']}件）")
                        st.rerun()
                    else:
                        st.error(f"❌ インポートエラー: {result['error']}")
            
            elif file_extension == 'csv':
                df = pd.read_csv(uploaded_file)
                
                st.info(f"📊 {len(df)}件の記録\n📋 列数: {len(df.columns)}")
                
                if st.checkbox("🔍 CSVデータをプレビュー"):
                    st.dataframe(df.head(), use_container_width=True)
                
                if st.button("📥 CSV履歴をインポート"):
                    result = data_manager_class.import_from_csv(df)
                    
                    if result['success']:
                        st.success(f"✅ CSV履歴をインポートしました！（{result['imported_count']}件）")
                        st.rerun()
                    else:
                        st.error(f"❌ インポートエラー: {result['error']}")
            
        except Exception as e:
            st.error(f"❌ ファイル読み込みエラー: {str(e)}")


def render_statistics_summary(global_stats: Dict[str, Any], data_stats: Dict[str, Any]):
    """
    統計サマリーを4列レイアウトで表示
    
    Args:
        global_stats: グローバル統計情報
        data_stats: データ統計情報
    """
    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
    
    with stats_col1:
        st.metric("総ブランチ数", global_stats['total_branches'])
    
    with stats_col2:
        st.metric("総実行数", global_stats['total_executions'])
    
    with stats_col3:
        st.metric("総タグ数", global_stats['total_tags'])
    
    with stats_col4:
        st.metric("総実行コスト", f"${global_stats['total_cost']:.6f}")


def render_detailed_statistics(data_stats: Dict[str, Any], data_manager_class):
    """
    詳細統計情報をエクスパンダーで表示
    
    Args:
        data_stats: データ統計情報
        data_manager_class: DataManagerクラス
    """
    if st.expander("📊 詳細統計情報"):
        detail_col1, detail_col2 = st.columns(2)
        
        with detail_col1:
            st.subheader("🤖 使用モデル統計")
            if data_stats['models_used']:
                for model, count in data_stats['models_used'].items():
                    percentage = (count / data_stats['total_records']) * 100 if data_stats['total_records'] > 0 else 0
                    st.write(f"- **{model}**: {count}回 ({percentage:.1f}%)")
            else:
                st.write("使用モデルデータがありません")
        
        with detail_col2:
            st.subheader("📅 データ期間")
            if data_stats['date_range']:
                st.write(f"**開始**: {data_stats['date_range']['start'][:10]}")
                st.write(f"**終了**: {data_stats['date_range']['end'][:10]}")
            else:
                st.write("日付データがありません")
            
            # データ整合性チェック
            integrity = data_manager_class.validate_data_integrity()
            if integrity['is_valid']:
                st.success("✅ データ整合性: 正常")
            else:
                st.warning("⚠️ データ整合性に問題があります")
                for issue in integrity['issues']:
                    st.error(f"- {issue}")
                for warning in integrity['warnings']:
                    st.warning(f"- {warning}")


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
    