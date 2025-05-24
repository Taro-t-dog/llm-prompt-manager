"""
実行履歴タブ
過去の実行記録を表示・管理する機能
"""

import streamlit as st
from core import GitManager
from ui.components import render_execution_card

# DataManagerのインポート（一時的な回避策対応）
try:
    from core import DataManager
except ImportError:
    # 簡易版DataManagerを使用
    class DataManager:
        @staticmethod
        def export_to_csv():
            if not st.session_state.evaluation_history:
                return ""
            import pandas as pd
            df = pd.DataFrame(st.session_state.evaluation_history)
            if 'timestamp' in df.columns:
                df['timestamp'] = df['timestamp'].apply(
                    lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x)
                )
            return df.to_csv(index=False, encoding='utf-8-sig')
        
        @staticmethod
        def get_file_suggestion(file_type="csv"):
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            record_count = len(st.session_state.evaluation_history)
            return f"prompt_execution_history_{timestamp}_{record_count}records.csv"


def render_history_tab():
    """実行履歴タブをレンダリング"""
    st.header("📋 実行履歴")
    
    # フィルターとエクスポート
    _render_filter_and_export_section()
    
    # 実行記録の表示
    executions_to_show = _get_executions_to_show()
    
    if not executions_to_show:
        st.info("まだ実行履歴がありません。「新規実行」タブでプロンプトを実行してください。")
        return
    
    st.markdown("---")
    
    # 実行記録の表示
    _display_execution_records(executions_to_show)


def _render_filter_and_export_section():
    """フィルターとエクスポートセクションをレンダリング"""
    filter_col1, filter_col2 = st.columns([3, 1])
    
    with filter_col1:
        show_all_branches = st.checkbox("全ブランチ表示", value=False)
        # セッション状態に保存
        st.session_state.show_all_branches = show_all_branches
    
    with filter_col2:
        if st.button("📥 履歴エクスポート"):
            csv_data = DataManager.export_to_csv()
            filename = DataManager.get_file_suggestion("csv")
            st.download_button(
                label="CSV ダウンロード",
                data=csv_data,
                file_name=filename,
                mime="text/csv"
            )


def _get_executions_to_show():
    """表示する実行記録を取得"""
    show_all_branches = getattr(st.session_state, 'show_all_branches', False)
    
    if show_all_branches:
        return st.session_state.evaluation_history
    else:
        return GitManager.get_branch_executions()


def _display_execution_records(executions_to_show):
    """実行記録を表示"""
    # 検索・フィルター機能
    search_options = _render_search_options()
    
    # フィルター適用
    filtered_executions = _apply_filters(executions_to_show, search_options)
    
    # ページネーション設定
    executions_per_page = st.selectbox(
        "1ページあたりの表示数",
        [5, 10, 20, 50],
        index=1,  # デフォルト10件
        key="pagination_size"
    )
    
    # ページネーション実装
    total_executions = len(filtered_executions)
    total_pages = (total_executions - 1) // executions_per_page + 1 if total_executions > 0 else 1
    
    if total_pages > 1:
        page_col1, page_col2, page_col3 = st.columns([1, 2, 1])
        with page_col2:
            current_page = st.number_input(
                f"ページ (1-{total_pages})",
                min_value=1,
                max_value=total_pages,
                value=1,
                key="current_page"
            )
    else:
        current_page = 1
    
    # 表示範囲の計算
    start_idx = (current_page - 1) * executions_per_page
    end_idx = min(start_idx + executions_per_page, total_executions)
    
    # ページ情報表示
    if total_executions > executions_per_page:
        st.info(f"📄 {start_idx + 1}-{end_idx}件目を表示 (全{total_executions}件、{total_pages}ページ)")
    
    # 実行記録の表示
    page_executions = list(reversed(filtered_executions))[start_idx:end_idx]
    
    for execution in page_executions:
        render_execution_card(execution, show_details=True)
        st.markdown("---")


def _render_search_options():
    """検索・フィルターオプションをレンダリング"""
    with st.expander("🔍 検索・フィルター"):
        search_col1, search_col2 = st.columns(2)
        
        with search_col1:
            # テキスト検索
            search_text = st.text_input(
                "🔍 テキスト検索",
                placeholder="コミットメッセージ、プロンプト、回答で検索...",
                key="search_text"
            )
            
            # ブランチフィルター
            all_branches = list(st.session_state.branches.keys())
            selected_branches = st.multiselect(
                "🌿 ブランチフィルター",
                all_branches,
                default=all_branches,
                key="branch_filter"
            )
        
        with search_col2:
            # モデルフィルター
            all_models = list(set([
                execution.get('model_name', 'Unknown') 
                for execution in st.session_state.evaluation_history
            ]))
            selected_models = st.multiselect(
                "🤖 モデルフィルター",
                all_models,
                default=all_models,
                key="model_filter"
            )
            
            # 日付範囲フィルター
            date_range = st.date_input(
                "📅 実行日フィルター",
                value=(),
                key="date_filter"
            )
    
    return {
        'search_text': search_text,
        'selected_branches': selected_branches,
        'selected_models': selected_models,
        'date_range': date_range
    }


def _apply_filters(executions, search_options):
    """フィルターを適用"""
    filtered = executions.copy()
    
    # テキスト検索
    if search_options['search_text']:
        search_text = search_options['search_text'].lower()
        filtered = [
            exec for exec in filtered
            if (search_text in exec.get('commit_message', '').lower() or
                search_text in exec.get('final_prompt', '').lower() or
                search_text in exec.get('response', '').lower())
        ]
    
    # ブランチフィルター
    if search_options['selected_branches']:
        filtered = [
            exec for exec in filtered
            if exec.get('branch', 'unknown') in search_options['selected_branches']
        ]
    
    # モデルフィルター
    if search_options['selected_models']:
        filtered = [
            exec for exec in filtered
            if exec.get('model_name', 'Unknown') in search_options['selected_models']
        ]
    
    # 日付フィルター
    if search_options['date_range']:
        if len(search_options['date_range']) == 2:
            start_date, end_date = search_options['date_range']
            filtered = [
                exec for exec in filtered
                if _is_execution_in_date_range(exec, start_date, end_date)
            ]
    
    return filtered


def _is_execution_in_date_range(execution, start_date, end_date):
    """実行記録が日付範囲内かチェック"""
    try:
        timestamp = execution.get('timestamp')
        if isinstance(timestamp, str):
            if 'T' in timestamp:
                import datetime
                exec_date = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
            else:
                exec_date = datetime.datetime.strptime(timestamp[:10], '%Y-%m-%d').date()
        else:
            exec_date = timestamp.date()
        
        return start_date <= exec_date <= end_date
    except:
        return True  # パースできない場合は表示