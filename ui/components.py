# ============================================
# ui/components.py (ワークフロー機能対応拡張版)
# ============================================
"""
改善されたUIコンポーネント
既存機能 + ワークフロー機能のコンポーネントを追加
"""

import streamlit as st
import datetime
import json
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
    # 🆕 統一されたコスト表示のためにformat_cost_displayをインポート
    from ui.styles import format_cost_display
    
    # 基本情報
    timestamp = format_timestamp(execution['timestamp'])
    exec_hash = execution['commit_hash']
    exec_memo = execution.get('commit_message', 'メモなし')
    branch = execution.get('branch', 'unknown')
    model_name = execution.get('model_name', 'Unknown')
    
    # 🆕 ワークフロー実行かどうかの判定
    is_workflow = execution.get('workflow_id') is not None
    workflow_icon = "🔄" if is_workflow else "📝"
    execution_type = "ワークフロー" if is_workflow else "単発実行"
    
    # ヘッダー部分
    header_col1, header_col2, header_col3 = st.columns([3, 1, 1])
    
    with header_col1:
        st.markdown(f"""
        <div class="commit-card">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <span class="branch-tag">{branch}</span>
                <span style="font-size: 1.1em;">{workflow_icon}</span>
                <strong>{exec_memo}</strong>
                <small style="color: #666;">({execution_type})</small>
            </div>
            <div style="color: #666; font-size: 0.9rem;">
                🤖 {model_name} | 📅 {timestamp[:16]} | <span class="commit-hash">{exec_hash}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with header_col2:
        cost_display = format_cost_display(execution['execution_cost'])
        st.metric("コスト", cost_display)
    
    with header_col3:
        total_tokens = execution['execution_tokens'] + execution['evaluation_tokens']
        st.metric("トークン", f"{total_tokens:,}")
    
    if show_details:
        if st.expander("📋 詳細を表示"):
            detail_col1, detail_col2 = st.columns([2, 1])
            
            with detail_col1:
                render_response_box(execution['response'])
                if execution.get('evaluation'):  # 評価がある場合のみ表示
                    render_evaluation_box(execution['evaluation'])
            
            with detail_col2:
                st.markdown("**📊 メトリクス**")
                st.metric("実行トークン", f"{execution['execution_tokens']:,}")
                st.metric("評価トークン", f"{execution['evaluation_tokens']:,}")
                
                exec_cost_display = format_cost_display(execution['execution_cost'])
                st.metric("実行コスト", exec_cost_display)
                
                # 🆕 ワークフロー固有の情報
                if is_workflow:
                    st.markdown("**🔄 ワークフロー情報**")
                    if execution.get('step_number'):
                        st.metric("ステップ番号", execution['step_number'])
                    if execution.get('workflow_id'):
                        st.code(f"ID: {execution['workflow_id']}")
                
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
    # 🆕 統一されたコスト表示のためにformat_cost_displayをインポート
    from ui.styles import format_cost_display
    
    stats_col1, stats_col2, stats_col3 = st.columns(3)
    
    with stats_col1:
        st.metric("ブランチ", global_stats['total_branches'])
    
    with stats_col2:
        st.metric("実行数", global_stats['total_executions'])
    
    with stats_col3:
        cost_display = format_cost_display(global_stats['total_cost'])
        st.metric("総コスト", cost_display)


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


# 🆕 ワークフロー専用コンポーネント

def render_workflow_card(workflow: Dict[str, Any], show_actions: bool = True):
    """ワークフロー情報カード"""
    created_date = workflow.get('created_at', '')[:10] if workflow.get('created_at') else 'Unknown'
    step_count = len(workflow.get('steps', []))
    var_count = len(workflow.get('global_variables', []))
    
    card_col1, card_col2 = st.columns([3, 1])
    
    with card_col1:
        st.markdown(f"""
        <div class="workflow-card">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <span style="font-size: 1.2em;">🔄</span>
                <strong>{workflow['name']}</strong>
            </div>
            <div style="color: #666; font-size: 0.9rem; margin-bottom: 0.5rem;">
                {workflow.get('description', '説明なし')}
            </div>
            <div style="color: #888; font-size: 0.8rem;">
                📋 {step_count}ステップ | 📥 {var_count}変数 | 📅 {created_date}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with card_col2:
        if show_actions:
            if st.button("🚀 実行", key=f"run_{workflow['id']}", use_container_width=True):
                return "run"
            if st.button("✏️ 編集", key=f"edit_{workflow['id']}", use_container_width=True):
                return "edit"
            if st.button("🗑️ 削除", key=f"delete_{workflow['id']}", use_container_width=True):
                return "delete"
    
    return None


def render_workflow_progress(current_step: int, total_steps: int, step_names: List[str], 
                           current_step_name: str = ""):
    """ワークフロー実行進捗表示"""
    # プログレスバー
    progress = current_step / total_steps if total_steps > 0 else 0
    st.progress(progress)
    
    # 現在のステップ情報
    step_info_col1, step_info_col2 = st.columns([2, 1])
    
    with step_info_col1:
        if current_step_name:
            st.markdown(f"**実行中:** {current_step_name}")
        else:
            st.markdown(f"**Step {current_step}** を実行中...")
    
    with step_info_col2:
        st.markdown(f"**{current_step}/{total_steps}** 完了")
    
    # ステップ一覧表示
    with st.expander("📋 全ステップ", expanded=False):
        for i, step_name in enumerate(step_names):
            if i + 1 < current_step:
                st.success(f"✅ Step {i+1}: {step_name}")
            elif i + 1 == current_step:
                st.info(f"🔄 Step {i+1}: {step_name} (実行中)")
            else:
                st.markdown(f"⏸️ Step {i+1}: {step_name} (待機中)")


def render_workflow_result_tabs(result, debug_mode: bool = False):
    """ワークフロー結果のタブ表示"""
    if not result.success:
        st.error(f"❌ ワークフロー実行失敗: {result.error}")
        return
    
    # タブ作成
    tabs = ["🎯 最終結果", "📋 ステップ詳細"]
    if debug_mode:
        tabs.append("🐛 デバッグ情報")
    else:
        tabs.append("📊 統計情報")
    
    tab_objects = st.tabs(tabs)
    
    # 最終結果タブ
    with tab_objects[0]:
        st.markdown("### 🎯 最終出力")
        st.text_area("", value=result.final_output or "", height=400, key="workflow_final_result")
        
        if st.button("📋 結果をコピー"):
            st.code(result.final_output or "")
    
    # ステップ詳細タブ
    with tab_objects[1]:
        st.markdown("### 📋 各ステップの詳細")
        for i, step_result in enumerate(result.steps):
            with st.expander(f"Step {step_result.step_number}: {step_result.step_name}"):
                step_detail_col1, step_detail_col2 = st.columns([3, 1])
                
                with step_detail_col1:
                    st.markdown("**出力:**")
                    st.text_area("", value=step_result.response, height=200, 
                               key=f"workflow_step_result_{i}")
                
                with step_detail_col2:
                    st.metric("実行時間", f"{step_result.execution_time:.1f}秒")
                    st.metric("トークン", step_result.tokens)
                    st.metric("コスト", f"${step_result.cost:.4f}")
                    
                    if st.button("🔍 プロンプト確認", key=f"workflow_step_prompt_{i}"):
                        st.code(step_result.prompt)
    
    # デバッグ/統計タブ
    with tab_objects[2]:
        if debug_mode:
            st.markdown("### 🐛 デバッグ情報")
            debug_info = {
                'execution_id': result.execution_id,
                'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
                'duration_seconds': result.duration_seconds,
                'metadata': result.metadata or {}
            }
            st.json(debug_info)
        else:
            st.markdown("### 📊 実行統計")
            if result.steps:
                import pandas as pd
                
                step_data = []
                for step in result.steps:
                    step_data.append({
                        'ステップ': f"Step {step.step_number}",
                        '名前': step.step_name,
                        'コスト ($)': f"{step.cost:.4f}",
                        'トークン': step.tokens,
                        '実行時間 (秒)': f"{step.execution_time:.1f}"
                    })
                
                df = pd.DataFrame(step_data)
                st.dataframe(df, use_container_width=True)


def render_variable_substitution_help():
    """変数置換のヘルプ表示"""
    with st.expander("💡 変数置換の使い方", expanded=False):
        st.markdown("""
        ### 🔧 基本的な変数参照
        - `{variable_name}` - 基本的な変数参照
        - `{step_1_output}` - 前のステップの結果を参照
        - `{step_2_output}` - 2ステップ前の結果を参照
        
        ### 🎯 高度な機能
        - `{variable|default:デフォルト値}` - 変数が空の場合のデフォルト値
        - `{variable|truncate:100}` - 最初の100文字のみ使用
        - `{variable|upper}` - 大文字に変換
        - `{variable|lower}` - 小文字に変換
        
        ### 📝 セクション抽出
        - `{step_1_output.要約}` - 特定セクションのみ抽出
        - `{step_1_output.結論}` - 結論セクションのみ抽出
        
        ### 💡 使用例
        ```
        前のステップの分析結果：
        {step_1_output}
        
        上記を踏まえて、{input_data|truncate:200}について
        さらに詳しく分析してください。
        ```
        """)


def render_error_details(error_type: str, error_message: str, suggestions: List[str]):
    """エラー詳細と対処法の表示"""
    error_col1, error_col2 = st.columns([2, 1])
    
    with error_col1:
        st.markdown("### 🚨 エラー詳細")
        st.error(f"**エラータイプ:** {error_type}")
        st.markdown(f"**詳細メッセージ:**")
        st.code(error_message)
    
    with error_col2:
        st.markdown("### 💡 推奨対処法")
        for i, suggestion in enumerate(suggestions, 1):
            st.markdown(f"{i}. {suggestion}")


def render_workflow_template_selector():
    """ワークフロー テンプレート選択UI"""
    st.markdown("### 📋 テンプレートから開始")
    
    # 定義済みテンプレート
    templates = {
        "document_analysis": {
            "name": "文書分析ワークフロー",
            "description": "文書を分析 → 要点抽出 → レポート生成",
            "steps": 3,
            "variables": ["document"]
        },
        "research_workflow": {
            "name": "調査研究ワークフロー", 
            "description": "情報収集 → 比較分析 → 結論導出",
            "steps": 3,
            "variables": ["research_topic", "sources"]
        },
        "business_analysis": {
            "name": "ビジネス分析ワークフロー",
            "description": "現状分析 → 課題特定 → 解決策提案",
            "steps": 3,
            "variables": ["business_data", "objectives"]
        },
        "content_creation": {
            "name": "コンテンツ作成ワークフロー",
            "description": "アイデア整理 → 構成作成 → 本文執筆",
            "steps": 3,
            "variables": ["topic", "target_audience"]
        }
    }
    
    template_cols = st.columns(2)
    
    for i, (template_id, template_info) in enumerate(templates.items()):
        col = template_cols[i % 2]
        
        with col:
            with st.container():
                st.markdown(f"""
                <div class="template-card">
                    <h4>{template_info['name']}</h4>
                    <p style="color: #666; font-size: 0.9rem;">{template_info['description']}</p>
                    <div style="font-size: 0.8rem; color: #888;">
                        📋 {template_info['steps']}ステップ | 📥 {len(template_info['variables'])}変数
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"このテンプレートを使用", key=f"template_{template_id}", use_container_width=True):
                    return template_id
    
    return None


# CSS for new components
def get_additional_styles():
    """追加のCSS スタイル"""
    return """
    <style>
    .workflow-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    
    .workflow-card:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        transform: translateY(-1px);
    }
    
    .template-card {
        background: linear-gradient(135deg, #f8faff 0%, #f1f5ff 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }
    
    .template-card:hover {
        background: linear-gradient(135deg, #e6f3ff 0%, #ddeeff 100%);
        border-color: #667eea;
    }
    
    .template-card h4 {
        margin: 0 0 0.5rem 0;
        color: #2d3748;
    }
    
    .template-card p {
        margin: 0 0 0.5rem 0;
    }
    </style>
    """