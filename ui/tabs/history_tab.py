"""
改善された実行履歴タブ
"""

import streamlit as st
from core import GitManager
from ui.components import render_execution_card


def render_history_tab():
    """改善された履歴タブ"""
    # ヘッダー
    header_col1, header_col2, header_col3 = st.columns([2, 1, 1])
    
    with header_col1:
        st.markdown("### 📋 実行履歴")
    
    with header_col2:
        show_all_branches = st.checkbox("全ブランチ", value=False)
    
    with header_col3:
        current_branch = GitManager.get_current_branch()
        st.markdown(f"**現在:** `{current_branch}`")
    
    # 実行記録取得
    executions_to_show = _get_executions_to_show(show_all_branches)
    
    if not executions_to_show:
        st.info("実行履歴がありません。「実行」タブでプロンプトを実行してください。")
        return
    
    # フィルターと検索
    filtered_executions = _render_filters_and_search(executions_to_show)
    
    # ページネーション
    _render_paginated_executions(filtered_executions)


def _get_executions_to_show(show_all_branches: bool):
    """表示する実行記録を取得"""
    if show_all_branches:
        return st.session_state.evaluation_history
    else:
        return GitManager.get_branch_executions()


def _render_filters_and_search(executions_to_show):
    """フィルターと検索"""
    filter_col1, filter_col2, filter_col3 = st.columns([2, 1, 1])
    
    with filter_col1:
        search_text = st.text_input(
            "🔍 検索",
            placeholder="メッセージ、プロンプト、回答で検索...",
            key="search_text"
        )
    
    with filter_col2:
        # モデルフィルター
        all_models = list(set([
            execution.get('model_name', 'Unknown') 
            for execution in executions_to_show
        ]))
        selected_model = st.selectbox(
            "🤖 モデル",
            ['すべて'] + all_models,
            key="model_filter"
        )
    
    with filter_col3:
        # ソート
        sort_options = {
            "新しい順": lambda x: x.get('timestamp', ''),
            "古い順": lambda x: x.get('timestamp', ''),
            "コスト高": lambda x: x.get('execution_cost', 0),
            "コスト低": lambda x: x.get('execution_cost', 0)
        }
        
        sort_method = st.selectbox(
            "📊 並び順",
            list(sort_options.keys()),
            key="sort_method"
        )
    
    # フィルター適用
    filtered = executions_to_show.copy()
    
    # テキスト検索
    if search_text:
        search_lower = search_text.lower()
        filtered = [
            exec for exec in filtered
            if (search_lower in exec.get('commit_message', '').lower() or
                search_lower in exec.get('final_prompt', '').lower() or
                search_lower in exec.get('response', '').lower())
        ]
    
    # モデルフィルター
    if selected_model != 'すべて':
        filtered = [
            exec for exec in filtered
            if exec.get('model_name', 'Unknown') == selected_model
        ]
    
    # ソート
    reverse_sort = sort_method in ["新しい順", "コスト高"]
    filtered.sort(key=sort_options[sort_method], reverse=reverse_sort)
    
    return filtered


def _render_paginated_executions(filtered_executions):
    """ページネーション付き実行記録表示"""
    total_executions = len(filtered_executions)
    
    if total_executions == 0:
        st.info("検索条件に合う実行記録が見つかりません。")
        return
    
    # ページネーション設定
    pagination_col1, pagination_col2, pagination_col3 = st.columns([1, 2, 1])
    
    with pagination_col1:
        page_size = st.selectbox(
            "表示数",
            [5, 10, 20, 50],
            index=1,
            key="page_size"
        )
    
    with pagination_col2:
        total_pages = (total_executions - 1) // page_size + 1 if total_executions > 0 else 1
        
        if total_pages > 1:
            current_page = st.number_input(
                f"ページ (1-{total_pages})",
                min_value=1,
                max_value=total_pages,
                value=1,
                key="current_page"
            )
        else:
            current_page = 1
    
    with pagination_col3:
        st.metric("件数", total_executions)
    
    # 表示範囲計算
    start_idx = (current_page - 1) * page_size
    end_idx = min(start_idx + page_size, total_executions)
    
    # ページ情報
    if total_executions > page_size:
        st.markdown(f"**{start_idx + 1}-{end_idx}件目** (全{total_executions}件)")
    
    st.markdown("---")
    
    # 実行記録表示
    page_executions = filtered_executions[start_idx:end_idx]
    
    for i, execution in enumerate(page_executions):
        render_execution_card(execution, show_details=False)
        
        # 詳細表示の展開
        if st.expander(f"📋 詳細 - {execution['commit_hash'][:8]}", expanded=False):
            _render_execution_details(execution)
        
        if i < len(page_executions) - 1:  # 最後以外に区切り線
            st.markdown("---")


def _render_execution_details(execution):
    """実行記録の詳細表示"""
    detail_col1, detail_col2 = st.columns([2, 1])
    
    with detail_col1:
        # プロンプトと回答
        with st.expander("📝 プロンプト", expanded=True):
            if execution.get('execution_mode') == "テンプレート + データ入力":
                st.markdown("**テンプレート:**")
                st.code(execution.get('prompt_template', ''), language=None)
                st.markdown("**データ:**")
                st.code(execution.get('user_input', ''), language=None)
                st.markdown("**最終プロンプト:**")
            st.code(execution.get('final_prompt', ''), language=None)
        
        with st.expander("🤖 回答", expanded=True):
            st.markdown(execution.get('response', ''))
        
        with st.expander("⭐ 評価", expanded=False):
            st.markdown("**評価基準:**")
            st.code(execution.get('criteria', ''), language=None)
            st.markdown("**評価結果:**")
            st.markdown(execution.get('evaluation', ''))
    
    with detail_col2:
        # メタデータ
        st.markdown("### 📊 詳細情報")
        
        # 基本情報
        st.markdown(f"""
        **ID:** `{execution['commit_hash']}`  
        **ブランチ:** `{execution.get('branch', 'unknown')}`  
        **モデル:** {execution.get('model_name', 'Unknown')}  
        **実行時刻:** {execution.get('timestamp', 'Unknown')}
        """)
        
        # メトリクス
        st.markdown("### 💰 コスト・トークン")
        st.metric("実行トークン", f"{execution.get('execution_tokens', 0):,}")
        st.metric("評価トークン", f"{execution.get('evaluation_tokens', 0):,}")
        st.metric("実行コスト", f"${execution.get('execution_cost', 0):.6f}")
        st.metric("評価コスト", f"${execution.get('evaluation_cost', 0):.6f}")
        
        total_cost = execution.get('execution_cost', 0) + execution.get('evaluation_cost', 0)
        st.metric("総コスト", f"${total_cost:.6f}")
        
        # アクション
        st.markdown("### 🔧 アクション")
        
        if st.button("📋 プロンプトをコピー", key=f"copy_{execution['commit_hash']}", use_container_width=True):
            st.code(execution.get('final_prompt', ''), language=None)


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