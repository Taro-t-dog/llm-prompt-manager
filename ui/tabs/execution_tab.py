# ============================================
# ui/tabs/execution_tab.py (大幅拡張・修正版 - 省略なし)
# ============================================
"""
実行タブ - 単発処理と多段階ワークフロー実行
4つの重要ポイントを全て実装:
- 変数置換の柔軟性
- エラーハンドリングの汎用性
- UI のわかりやすさ
- 実行速度の最適化
"""
import sys
import os
import streamlit as st
import datetime
import json
import time
from typing import Dict, List, Any, Optional, Tuple 

# core モジュールからのインポート
from config.models import get_model_config
from core import GeminiEvaluator, GitManager, WorkflowEngine, WorkflowManager # GitManager, WorkflowManager をcoreから
from core.workflow_engine import StepResult, ExecutionStatus, WorkflowExecutionResult, WorkflowErrorHandler, VariableProcessor # VariableProcessor を追加

# ui モジュールからのインポート
from ui.components import (
    render_response_box,
    render_evaluation_box,
    render_workflow_result_tabs,
    render_error_details,
    render_workflow_step_card,
    render_workflow_live_step,
    render_workflow_execution_summary # これは主に render_workflow_result_tabs 内、またはテスト用
)
from ui.styles import format_detailed_cost_display, format_tokens_display


# セッション状態の初期化
def _initialize_session_state():
    """execution_tabで使われるセッション状態のキーを初期化"""
    defaults = {
        'execution_memo': "",
        'execution_mode': "テンプレート + データ入力",
        'prompt_template': "以下のテキストを要約してください：\n\n{user_input}",
        'user_input_data': "",
        'single_prompt': "",
        'evaluation_criteria': """1. 正確性（30点）
2. 網羅性（25点）
3. 分かりやすさ（25点）
4. 論理性（20点）""",
        'latest_execution_result': None,
        # user_workflows は WorkflowManager.get_saved_workflows() から取得するため、セッション状態に直接持たない
        'current_workflow_execution': None, # 現在実行中のワークフロー結果オブジェクト
        'workflow_execution_progress': {}, # ステップごとの進捗詳細 (あまり使わない想定)
        'show_workflow_debug': False, # ワークフローのデバッグ情報表示フラグ
        'processing_mode': 'single', # 'single' または 'workflow'
        'current_workflow_steps': [], # 実行中のワークフローのステップ結果を一時保存（表示用）
        'temp_variables': ['input_1'], # 新規ワークフロービルダー用
        'temp_steps': [{}], # 新規ワークフロービルダー用
    }
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def render_execution_tab():
    """実行タブメイン（単発処理 + ワークフロー処理）"""
    _initialize_session_state() # GitManager.initialize_session_state() は main.py や app_setup で呼び出す想定

    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.markdown("### 🚀 プロンプト実行")
    with header_col2:
        current_branch = GitManager.get_current_branch() # GitManager を直接使用
        st.markdown(f"**ブランチ:** `{current_branch}`")

    st.markdown("#### 実行モードを選択")
    mode_col1, mode_col2 = st.columns(2)

    with mode_col1:
        if st.button("📝 単発処理", use_container_width=True, help="1つのプロンプトを実行して結果を取得"):
            st.session_state.processing_mode = "single"

    with mode_col2:
        if st.button("🔄 ワークフロー処理", use_container_width=True, help="複数のステップを連鎖実行して最終結果を取得"):
            st.session_state.processing_mode = "workflow"

    if 'processing_mode' not in st.session_state: # デフォルト設定
        st.session_state.processing_mode = "single"

    st.markdown("---")

    if st.session_state.processing_mode == "single":
        _render_single_execution()
    else:
        _render_workflow_execution()

def _render_single_execution():
    """既存の単発実行機能"""
    st.markdown("### 📝 単発プロンプト実行")

    exec_col1, exec_col2 = st.columns([3, 1])
    with exec_col1:
        st.markdown("新しいプロンプトを実行し自動評価")
    with exec_col2:
        current_branch = GitManager.get_current_branch()
        st.markdown(f"**ブランチ:** `{current_branch}`")

    with st.form("execution_form", clear_on_submit=False):
        memo_col1, memo_col2 = st.columns([4, 1])
        with memo_col1:
            execution_memo = st.text_input(
                "📝 実行メモ", value=st.session_state.execution_memo,
                placeholder="変更内容や実験目的...", key="memo_input_form"
            )
        with memo_col2:
            execution_mode_display = st.radio(
                "モード", ["テンプレート", "単一"],
                index=0 if st.session_state.execution_mode == "テンプレート + データ入力" else 1,
                horizontal=True, key="mode_radio_form"
            )
        execution_mode_full = "テンプレート + データ入力" if execution_mode_display == "テンプレート" else "単一プロンプト"

        prompt_template_val, user_input_data_val, single_prompt_val = _render_prompt_section_form(execution_mode_full)
        evaluation_criteria_val = _render_evaluation_section_form()
        submitted = st.form_submit_button("🚀 実行 & 自動評価", type="primary", use_container_width=True)

    if submitted:
        st.session_state.execution_memo = execution_memo
        st.session_state.execution_mode = execution_mode_full
        st.session_state.prompt_template = prompt_template_val
        st.session_state.user_input_data = user_input_data_val
        st.session_state.single_prompt = single_prompt_val
        st.session_state.evaluation_criteria = evaluation_criteria_val

        placeholder_intermediate_resp = st.empty()
        placeholder_intermediate_metrics = st.empty()
        placeholder_final_eval_info = st.empty()

        _execute_prompt_and_evaluation_sequentially(
            execution_memo, execution_mode_full,
            prompt_template_val, user_input_data_val, single_prompt_val, evaluation_criteria_val,
            placeholder_intermediate_resp, placeholder_intermediate_metrics, placeholder_final_eval_info
        )

    if st.session_state.latest_execution_result:
        st.markdown("---")
        st.subheader("✅ 実行・評価完了結果")
        _display_latest_results()

def _render_workflow_execution():
    """ワークフロー実行UI"""
    st.markdown("### 🔄 多段階ワークフロー実行")
    st.caption("複数のLLM処理ステップを順次実行し、前のステップの結果を次のステップで活用できます")

    workflow_tab1, workflow_tab2, workflow_tab3 = st.tabs([
        "💾 保存済みワークフロー", "🆕 新規ワークフロー作成", "🔧 高度な設定"
    ])

    with workflow_tab1:
        _render_saved_workflow_execution()
    with workflow_tab2:
        _render_workflow_builder()
    with workflow_tab3:
        _render_advanced_workflow_settings()

def _render_saved_workflow_execution():
    """保存済みワークフロー実行UI"""
    saved_workflows = WorkflowManager.get_saved_workflows() # WorkflowManager を使用

    if not saved_workflows:
        st.info("💡 保存済みワークフローがありません。「新規ワークフロー作成」タブで作成してください。")
        with st.expander("📝 ワークフロー作成のヒント"):
            st.markdown("""
            **よく使われるワークフローパターン:**

            📄 **文書分析フロー**
            1. 文書構造分析 → 2. 重要ポイント抽出 → 3. 要約・レポート生成

            🔍 **調査研究フロー**
            1. 情報収集・整理 → 2. 比較分析 → 3. 考察・提案
            
            💼 **ビジネス分析フロー**
            1. 現状分析 → 2. 課題特定 → 3. 解決策提案
            
            コンテンツ作成フロー
            1. アイデア整理 → 2. 構成作成 → 3. 本文執筆
            
            各ステップで前のステップの結果を `{step_1_output}`, `{step_2_output}` として参照できます。
            """)
        return

    workflow_col1, workflow_col2 = st.columns([3, 1])
    selected_id: Optional[str] = None
    with workflow_col1:
        workflow_options = {}
        for wid, wdef in saved_workflows.items():
            created_date_str = wdef.get('created_at', '')
            created_date = created_date_str[:10] if created_date_str else '日付不明'
            step_count = len(wdef.get('steps', []))
            display_name = f"{wdef.get('name', '無名ワークフロー')} ({step_count}ステップ, {created_date})"
            workflow_options[wid] = display_name

        if workflow_options: # 選択肢がある場合のみ selectbox を表示
            selected_id = st.selectbox(
                "ワークフロー選択",
                options=list(workflow_options.keys()),
                format_func=lambda x: workflow_options[x],
                help="実行したいワークフローを選択してください",
                index=0
            )
        else:
            st.caption("利用可能な保存済みワークフローはありません。")


    with workflow_col2:
        if selected_id:
            if st.button("🗑️ 削除", help="選択したワークフローを削除", key=f"delete_wf_{selected_id}"):
                if WorkflowManager.delete_workflow(selected_id):
                    st.success("✅ ワークフローを削除しました")
                    st.rerun()
                else:
                    st.error("ワークフローの削除に失敗しました。")

            if st.button("📋 複製", help="選択したワークフローを複製", key=f"duplicate_wf_{selected_id}"):
                original_workflow = WorkflowManager.get_workflow(selected_id)
                if original_workflow:
                    original_name = original_workflow.get('name', '無名ワークフロー')
                    new_name = f"{original_name} (コピー)"
                    new_id = WorkflowManager.duplicate_workflow(selected_id, new_name)
                    if new_id:
                        st.success(f"✅ ワークフロー「{new_name}」を作成しました")
                        st.rerun()
                    else:
                        st.error("ワークフローの複製に失敗しました。")
                else:
                    st.error("複製元のワークフローが見つかりませんでした。")


    if selected_id:
        workflow_def = WorkflowManager.get_workflow(selected_id)
        if workflow_def:
            _render_workflow_info_panel(workflow_def)
            input_values = _render_workflow_input_section(workflow_def)
            execution_options = _render_execution_options()

            if st.button("🚀 ワークフロー実行", type="primary", use_container_width=True, key=f"run_wf_{selected_id}"):
                _execute_workflow_with_progress(workflow_def, input_values, execution_options)
        else:
            st.error(f"選択されたワークフロー ID '{selected_id}' の定義が見つかりませんでした。リストを更新してください。")


def _render_workflow_info_panel(workflow_def: Dict):
    """ワークフロー情報パネル"""
    st.markdown("#### 📊 ワークフロー詳細情報")

    info_col1, info_col2, info_col3 = st.columns(3)
    created_date_str = workflow_def.get('created_at', 'Unknown')
    created_date = created_date_str[:10] if created_date_str and created_date_str != 'Unknown' else '日付不明'

    info_col1.metric("ステップ数", len(workflow_def.get('steps', [])))
    info_col2.metric("必要変数数", len(workflow_def.get('global_variables', [])))
    info_col3.metric("作成日", created_date)

    if workflow_def.get('description'):
        st.markdown(f"**説明:** {workflow_def['description']}")

    st.markdown("**ワークフロー構造:**")
    for i, step in enumerate(workflow_def.get('steps', [])):
        step_preview = step.get('prompt_template', '')[:100] + "..." if len(step.get('prompt_template', '')) > 100 else step.get('prompt_template', '')
        st.markdown(f"""
        **Step {i+1}: {step.get('name', '無名ステップ')}**
        ```
        {step_preview}
        ```
        """)
        if i < len(workflow_def.get('steps', [])) - 1:
            st.markdown("⬇️")
    st.markdown("---")

def _render_workflow_input_section(workflow_def: Dict) -> Dict[str, str]:
    """改善された入力変数設定UI"""
    input_values: Dict[str, str] = {}
    global_vars = workflow_def.get('global_variables')
    if global_vars and isinstance(global_vars, list): # Ensure global_vars is a list
        st.markdown("### 📥 入力データ設定")
        for var_name in global_vars:
            var_description = _generate_variable_description(var_name)
            # Use a more unique key for text_area to prevent conflicts across different workflows or reruns
            workflow_identifier = workflow_def.get('id', workflow_def.get('name', 'unknown_workflow'))
            input_values[var_name] = st.text_area(
                f"**{var_name}**",
                help=f"{var_description}",
                placeholder=f"{var_name}の内容を入力してください...",
                key=f"workflow_input_{workflow_identifier}_{var_name}",
                height=120
            )
            if input_values[var_name]:
                char_count = len(input_values[var_name])
                st.caption(f"📝 {char_count:,} 文字")
    elif global_vars is not None: # It exists but is not a list
        st.warning("ワークフロー定義の 'global_variables' が不正な形式です。リストであるべきです。")

    return input_values

def _generate_variable_description(var_name: str) -> str:
    """変数名から説明を自動生成"""
    descriptions = {
        'document': '分析対象の文書やテキスト', 'data': '処理するデータ', 'input': '入力情報',
        'text': 'テキスト内容', 'content': 'コンテンツ', 'source': 'ソース情報',
        'requirement': '要件や条件', 'context': '背景情報や文脈'
    }
    for key, desc in descriptions.items():
        if key in var_name.lower():
            return f"ワークフローで使用される{desc}"
    return f"ワークフローで使用される変数 '{var_name}' の値"

def _render_execution_options() -> Dict[str, Any]:
    """実行オプション設定"""
    with st.expander("⚙️ 実行オプション", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            show_progress = st.checkbox("進捗表示", value=True, help="実行中の詳細な進捗を表示", key="wf_opt_show_progress")
            # cache_results のデフォルトはTrue、エンジン側が対応している場合のみ有効
            cache_results = st.checkbox("結果キャッシュ利用", value=True, help="同じプロンプトの結果を再利用（エンジンが対応する場合）", key="wf_opt_cache")
        with col2:
            # auto_retry のデフォルトはTrue、エンジン側が対応している場合のみ有効
            auto_retry = st.checkbox("自動リトライ（エラー時）", value=True, help="エラー発生時の自動再試行（エンジンが対応する場合）", key="wf_opt_retry")
            # デバッグモードはセッション状態と同期
            current_debug_mode = st.session_state.get('show_workflow_debug', False)
            debug_mode = st.checkbox("デバッグモード", value=current_debug_mode, help="詳細なデバッグ情報を表示", key="wf_opt_debug")
            st.session_state.show_workflow_debug = debug_mode # UIの変更をセッション状態に反映
        return {'show_progress': show_progress, 'cache_results': cache_results, 'auto_retry': auto_retry, 'debug_mode': debug_mode}

def _render_workflow_builder():
    """改善されたワークフロービルダー"""
    st.markdown("### 🆕 新規ワークフロー作成")

    # ステップ1: 基本情報
    with st.expander("📝 Step 1: 基本情報", expanded=True):
        basic_col1, basic_col2 = st.columns(2)
        with basic_col1:
            # セッション状態に保存された一時的な値を読み込むか、空文字で初期化
            workflow_name = st.text_input("ワークフロー名", 
                                          value=st.session_state.get('wf_builder_name_cache', ""), 
                                          placeholder="例: 文書分析ワークフロー", help="わかりやすい名前", 
                                          key="wf_builder_name_input")
            st.session_state.wf_builder_name_cache = workflow_name # 入力を一時保存
        with basic_col2:
            description = st.text_input("説明（任意）", 
                                        value=st.session_state.get('wf_builder_desc_cache', ""),
                                        placeholder="例: 文書を分析し要約とレポートを生成", help="このワークフローの目的や内容", 
                                        key="wf_builder_desc_input")
            st.session_state.wf_builder_desc_cache = description # 入力を一時保存


    # ステップ2: 入力変数設定
    with st.expander("📥 Step 2: 入力変数設定", expanded=True):
        st.markdown("このワークフローで使用するグローバル入力変数を定義してください（例: `document_text`, `user_query`）。")
        # st.session_state.temp_variables は _initialize_session_state で初期化
        
        global_variables: List[str] = []
        input_values_for_test: Dict[str, str] = {}

        # temp_variables の編集中に変更が起きる可能性があるため、コピーに対してループ
        current_temp_vars = list(st.session_state.temp_variables)
        for i, var_name_in_session in enumerate(current_temp_vars):
            var_col1, var_col2, var_col3 = st.columns([2, 3, 1])
            with var_col1:
                new_var_name = st.text_input(f"変数名 {i+1}", value=var_name_in_session, key=f"var_name_builder_{i}", help="英数字とアンダースコアのみ")
                if new_var_name != var_name_in_session: # 変更があった場合のみ更新を試みる
                    if new_var_name.isidentifier():
                        st.session_state.temp_variables[i] = new_var_name
                        # ここで st.rerun() を呼ぶと入力がリセットされるため、直接更新
                    elif new_var_name: # 空でなく、無効な名前
                        st.warning(f"変数名 '{new_var_name}' は無効です。英数字とアンダースコアのみ使用できます。'{var_name_in_session}' を維持します。")
                        new_var_name = var_name_in_session # 元の名前に戻す
                    else: # 空にしようとした場合
                        st.warning(f"変数名は空にできません。'{var_name_in_session}' を維持します。")
                        new_var_name = var_name_in_session # 元の名前に戻す
                
                # 有効な最終的な変数名を使用
                if new_var_name.isidentifier() and new_var_name not in global_variables:
                    global_variables.append(new_var_name)


            with var_col2:
                if new_var_name and new_var_name.isidentifier(): # 有効な変数名の場合のみテストデータ入力欄を表示
                     input_values_for_test[new_var_name] = st.text_area(
                         f"「{new_var_name}」のテスト用データ",
                         value=st.session_state.get(f'var_test_builder_data_{new_var_name}', ""), # テストデータもセッションに保存
                         key=f"var_test_builder_{i}", height=80, help="ワークフローのテスト実行時に使用するデータ"
                     )
                     st.session_state[f'var_test_builder_data_{new_var_name}'] = input_values_for_test[new_var_name]


            with var_col3:
                st.write("") # Align button vertically
                st.write("")
                if len(st.session_state.temp_variables) > 1:
                    if st.button("➖", key=f"remove_var_builder_{i}", help="この変数を削除"):
                        st.session_state.temp_variables.pop(i)
                        # 関連するテストデータも削除
                        if var_name_in_session in st.session_state:
                            del st.session_state[f'var_test_builder_data_{var_name_in_session}']
                        st.rerun()

        if st.button("➕ 変数を追加", key="add_var_builder"):
            st.session_state.temp_variables.append(f"input_{len(st.session_state.temp_variables) + 1}")
            st.rerun()

    # ステップ3: ワークフローステップ設定
    with st.expander("🔧 Step 3: ワークフローステップ設定", expanded=True):
        # st.session_state.temp_steps は _initialize_session_state で初期化
        
        steps_config: List[Dict[str, Any]] = []

        current_temp_steps = list(st.session_state.temp_steps) # コピーに対してループ
        for i, step_data_in_session in enumerate(current_temp_steps):
            st.markdown(f"--- \n#### 📋 ステップ {i+1}")
            step_col1, step_col2 = st.columns([3, 1])
            
            # セッションから現在のステップ名とテンプレートを読み込む
            current_step_name = step_data_in_session.get('name', f"ステップ {i+1}")
            # 利用可能な変数を計算
            available_vars_for_step = global_variables.copy()
            if i > 0: available_vars_for_step.extend([f"step_{j+1}_output" for j in range(i)])
            current_prompt_template = step_data_in_session.get('template', _get_default_prompt_template(i, available_vars_for_step))


            with step_col1:
                step_name_input = st.text_input("ステップ名", value=current_step_name, key=f"step_name_builder_{i}", help="このステップの目的（例: 要約生成）")
            with step_col2:
                st.write("") # Align button vertically
                st.write("")
                if len(st.session_state.temp_steps) > 1:
                    if st.button("🗑️ このステップを削除", key=f"remove_step_builder_{i}"):
                        st.session_state.temp_steps.pop(i)
                        st.rerun()
            
            _render_variable_help(available_vars_for_step)

            prompt_template_input = st.text_area("プロンプトテンプレート", value=current_prompt_template, key=f"step_prompt_builder_{i}", height=150, help="このステップで実行するプロンプト。{変数名}で他の変数や前のステップ出力を参照。")
            
            if st.checkbox(f"ステップ {i+1} プレビュー表示", key=f"preview_builder_{i}", value=False):
                # _render_prompt_preview に渡すのは、現在までの確定したステップ設定
                _render_prompt_preview(prompt_template_input, input_values_for_test, i, steps_config)

            # 現在のループで処理しているステップの設定を steps_config に追加
            current_step_config = {'name': step_name_input, 'prompt_template': prompt_template_input}
            steps_config.append(current_step_config)
            
            # セッション状態を更新 (次のレンダリングのため)
            st.session_state.temp_steps[i] = current_step_config


        if st.button("➕ ステップを追加", key="add_step_builder"):
            st.session_state.temp_steps.append({}) # 新しい空のステップデータを追加
            st.rerun()

    st.markdown("### 🎯 アクション")
    action_col1, action_col2, action_col3 = st.columns(3)
    with action_col1:
        if st.button("💾 保存", use_container_width=True, key="save_wf_builder"):
            if _validate_and_save_workflow(workflow_name, description, steps_config, global_variables):
                # ビルダーの状態をリセット
                st.session_state.wf_builder_name_cache = ""
                st.session_state.wf_builder_desc_cache = ""
                st.session_state.temp_variables = ['input_1']
                st.session_state.temp_steps = [{}]
                for var_name in global_variables: # テストデータもクリア
                    if f'var_test_builder_data_{var_name}' in st.session_state:
                        del st.session_state[f'var_test_builder_data_{var_name}']
                st.rerun()
    with action_col2:
        if st.button("🧪 テスト実行", use_container_width=True, key="test_wf_builder"):
            if workflow_name and steps_config:
                workflow_def_to_test = {'name': workflow_name, 'description': description, 'steps': steps_config, 'global_variables': global_variables}
                # 実行オプションは固定またはUIから取得
                test_options = {'show_progress': True, 'debug_mode': True, 'cache_results': False, 'auto_retry': False}
                _execute_workflow_with_progress(workflow_def_to_test, input_values_for_test, test_options)
            else:
                st.warning("テスト実行には、ワークフロー名と少なくとも1つのステップ定義が必要です。")
    with action_col3:
        if st.button("🔄 リセット", use_container_width=True, key="reset_wf_builder"):
            st.session_state.wf_builder_name_cache = ""
            st.session_state.wf_builder_desc_cache = ""
            st.session_state.temp_variables = ['input_1']
            st.session_state.temp_steps = [{}]
            # テストデータもクリアする必要があるかもしれない
            active_global_vars = [] # 現在 builder UI に表示されている global_variables を再計算
            for temp_var_name in st.session_state.temp_variables:
                if temp_var_name.isidentifier(): active_global_vars.append(temp_var_name)
            for var_name in active_global_vars:
                if f'var_test_builder_data_{var_name}' in st.session_state:
                    del st.session_state[f'var_test_builder_data_{var_name}']
            st.rerun()


def _render_variable_help(available_vars: List[str]):
    """利用可能変数のヘルプ表示"""
    if available_vars:
        st.markdown("**💡 利用可能な変数:**")
        cols = st.columns(2)
        input_vars = [var for var in available_vars if not var.startswith('step_')]
        step_vars = [var for var in available_vars if var.startswith('step_')]
        with cols[0]:
            if input_vars:
                st.markdown("*グローバル入力:*")
                for var in input_vars: st.code(f"{{{var}}}")
        with cols[1]:
            if step_vars:
                st.markdown("*前のステップ結果:*")
                for var in step_vars: st.code(f"{{{var}}}")

def _render_prompt_preview(template: str, input_values: Dict[str, str], current_step_index: int, previous_steps_config: List[Dict[str, Any]]):
    """プロンプトのリアルタイムプレビュー
    Args:
        template: プレビュー対象のプロンプトテンプレート
        input_values: グローバル入力変数のテスト値
        current_step_index: 現在編集中のステップのインデックス (0-based)
        previous_steps_config: current_step_index より前のステップの設定リスト（nameを含む）
    """
    processor = VariableProcessor() # core.workflow_engine からインポート
    context_for_preview = input_values.copy()
    
    # Simulate previous step outputs for preview context
    # previous_steps_config には、現在プレビューしているステップより前のステップの設定のみが含まれるべき
    for i, prev_step_conf in enumerate(previous_steps_config):
        # i は previous_steps_config のインデックスであり、実際のステップ番号-1 となる
        # current_step_index は現在編集中のステップのインデックス
        # ここでは、previous_steps_config が既に current_step_index より前のステップのみを
        # 含んでいるという前提で、i をそのままステップ番号インデックスとして使うのは誤り。
        # previous_steps_config は、呼び出し元でスライスするなどして、適切な範囲のステップ設定を渡す必要がある。
        # この関数の呼び出し箇所で steps_config[:current_step_index] のように渡すことを想定。
        actual_prev_step_number = i + 1 # prev_step_conf のステップ番号
        context_for_preview[f'step_{actual_prev_step_number}_output'] = f"[Step {actual_prev_step_number} ({prev_step_conf.get('name', '')}) の模擬出力がここに挿入されます]"
        
    try:
        preview_content = processor.substitute_variables(template, context_for_preview)
        st.markdown("**プレビュー:**")
        preview_text_display = preview_content[:500] + "..." if len(preview_content) > 500 else preview_content
        st.text_area("プロンプトプレビュー", value=preview_text_display, height=150, 
                     key=f"preview_text_area_{current_step_index}_{template[:10]}", # よりユニークなキー
                     disabled=True)
    except Exception as e:
        st.warning(f"プレビューエラー: {str(e)}")


def _render_advanced_workflow_settings():
    """高度なワークフロー設定"""
    st.markdown("### 🔧 高度な設定")

    # キャッシュ管理
    st.markdown("#### 💾 キャッシュ管理")
    st.caption("実行結果のキャッシュを管理できます（エンジンが対応する場合）")
    cache_col1, cache_col2 = st.columns(2)
    with cache_col1:
        if st.button("🗑️ エンジンキャッシュクリア", use_container_width=True, key="clear_engine_cache_advanced"):
            if not st.session_state.get('api_key'):
                st.warning("APIキーが設定されていません。キャッシュクリアはスキップされました。")
                return

            selected_model_id = st.session_state.get('selected_model', 'default_model_id')
            model_config = get_model_config(selected_model_id)
            if not model_config:
                st.error(f"モデル設定 '{selected_model_id}' が見つかりません。キャッシュクリアはスキップされました。")
                return

            evaluator = GeminiEvaluator(st.session_state.api_key, model_config)
            engine = WorkflowEngine(evaluator) # WorkflowEngine は evaluator を引数に取る
            
            if hasattr(engine, 'clear_cache') and callable(engine.clear_cache):
                engine.clear_cache()
                st.success("✅ WorkflowEngineの実行キャッシュをクリアしました。")
            else:
                st.info("現在のWorkflowEngineはキャッシュクリア機能を持っていません。")
    with cache_col2:
        st.info("キャッシュ統計情報表示は実装予定です。") # 将来的な拡張ポイント

    st.markdown("---")

    # デバッグツール
    st.markdown("#### 🐛 デバッグツール")
    st.caption("ワークフロー開発とトラブルシューティング用のツール（主にアプリケーション開発者向け）")
    debug_col1, debug_col2 = st.columns(2)
    with debug_col1:
        st.checkbox("詳細ログ出力 (コンソール)", key="debug_verbose_logging_adv", value=False, help="アプリケーションログレベルを詳細に設定（別途ロギング設定要）")
        # UI上での変数置換表示は、_render_prompt_preview でのプレビューや、実行結果のデバッグタブで行う
        st.checkbox("変数置換の詳細表示 (UI)", key="debug_show_substitution_adv", value=st.session_state.get('show_workflow_debug', False), help="実行結果のデバッグタブで置換情報を表示")
        if st.session_state.debug_show_substitution_adv != st.session_state.get('show_workflow_debug', False):
             st.session_state.show_workflow_debug = st.session_state.debug_show_substitution_adv # 同期
             st.rerun()


    with debug_col2:
        # 実行時間の詳細表示は、render_workflow_result_tabs の統計タブやデバッグタブで行う
        st.checkbox("実行時間計測の詳細表示 (UI)", key="debug_measure_time_adv", value=st.session_state.get('show_workflow_debug', False), help="実行結果のデバッグタブで時間情報を表示")
        if st.session_state.debug_measure_time_adv != st.session_state.get('show_workflow_debug', False):
             st.session_state.show_workflow_debug = st.session_state.debug_measure_time_adv # 同期
             st.rerun()

        st.checkbox("メモリ使用量の監視 (コンソール)", key="debug_monitor_memory_adv", value=False, help="メモリ使用量を定期的にログ出力（別途実装要）")
    
    st.markdown("---")

    # エクスポート・インポート (ワークフロー定義)
    st.markdown("#### 📤 エクスポート・インポート (ワークフロー定義)")
    export_col1, export_col2 = st.columns(2)
    with export_col1:
        st.markdown("**エクスポート**")
        saved_workflows = WorkflowManager.get_saved_workflows()
        if saved_workflows:
            workflow_names = {wid: wdef.get('name', '無名ワークフロー') for wid, wdef in saved_workflows.items()}
            selected_export_id = st.selectbox(
                "エクスポートするワークフロー",
                options=list(saved_workflows.keys()),
                format_func=lambda x: workflow_names.get(x, x), # Display name, fallback to ID
                key="wf_export_select_adv"
            )
            if selected_export_id and st.button("📥 JSONでダウンロード", key="wf_export_button_adv"):
                json_data_export = WorkflowManager.export_workflow(selected_export_id) # Renamed
                if json_data_export:
                    st.download_button(
                        "💾 ダウンロード",
                        data=json_data_export,
                        file_name=f"{workflow_names.get(selected_export_id, selected_export_id)}.json",
                        mime="application/json",
                        key="wf_export_download_adv"
                    )
        else:
            st.caption("エクスポート可能な保存済みワークフローがありません。")

    with export_col2:
        st.markdown("**インポート**")
        uploaded_file_import = st.file_uploader("ワークフロー定義JSONファイルを選択", type=["json"], key="wf_import_uploader_adv") # Renamed
        if uploaded_file_import and st.button("📤 インポート", key="wf_import_button_adv"):
            try:
                json_data_str_import = uploaded_file_import.read().decode('utf-8') # Renamed
                import_result = WorkflowManager.import_workflow(json_data_str_import) # Renamed
                if import_result.get('success'):
                    st.success(f"✅ ワークフロー「{import_result.get('workflow_name', '')}」をインポートしました (ID: {import_result.get('workflow_id','')})")
                    st.rerun() # リストを更新するためにリラン
                else:
                    errors = import_result.get('errors', ['不明なインポートエラーが発生しました。'])
                    for err_item in errors: st.error(f"❌ {err_item}") # Renamed
            except Exception as e_import: # Renamed
                st.error(f"❌ インポート処理中にエラーが発生しました: {str(e_import)}")

# ==============================================================================
# ワークフロー実行とステップ表示関連の関数
# ==============================================================================

def _execute_workflow_with_progress(workflow_def: Dict, input_values: Dict, options: Dict):
    """ステップごとの出力を表示しながらワークフロー実行（エントリーポイント）"""
    # APIキーの存在チェック
    if not st.session_state.get('api_key'):
        st.error("❌ APIキーが設定されていません。設定タブでAPIキーを設定してください。")
        return
    
    # グローバル入力変数の値チェック
    for var_name in workflow_def.get('global_variables', []):
        if not input_values.get(var_name, '').strip(): # 値が空かスペースのみの場合
            st.error(f"❌ 必須入力変数 '{var_name}' の値が設定されていません。")
            return

    # モデル設定の取得と検証
    selected_model_id = st.session_state.get('selected_model')
    if not selected_model_id: # selected_model がセッションにない場合 (通常は設定タブで設定される)
        st.error("❌ 使用するモデルが選択されていません。設定タブでモデルを選択してください。")
        # フォールバックとしてconfigからデフォルトモデルIDを取得する試みも可能
        # model_config = get_model_config(None) # get_model_configがNoneをデフォルトとして扱う場合
        return
        
    model_config = get_model_config(selected_model_id)
    if not model_config:
        st.error(f"❌ 選択されたモデル '{selected_model_id}' の設定が見つかりません。設定ファイルを確認してください。")
        return

    # 実行エンジンの初期化
    evaluator = GeminiEvaluator(st.session_state.api_key, model_config)
    engine = WorkflowEngine(evaluator) # WorkflowEngine は evaluator を引数に取る

    # UIコンテナの準備
    st.markdown("### 🔄 ワークフロー実行進捗")
    overall_progress_container = st.container()
    steps_display_container = st.container()
    final_result_container = st.container()
    
    st.session_state.current_workflow_steps = [] # 実行のたびにクリア

    try:
        # ワークフロー実行のメインロジック呼び出し
        result_object = _execute_workflow_with_live_display( # Renamed
            engine, workflow_def, input_values,
            overall_progress_container, steps_display_container, options
        )
        
        # 最終結果の表示
        with final_result_container:
            st.markdown("---") # 区切り線
            st.markdown("### 🎯 ワークフロー完了")
            _render_workflow_result(result_object, options.get('debug_mode', False))
            
    except Exception as e_exec_wf: # Renamed for clarity
        st.error(f"❌ ワークフローの実行中に予期せぬメインエラーが発生しました: {str(e_exec_wf)}")
        # デバッグ用にトレースバックを表示することも検討
        # import traceback
        # st.error(traceback.format_exc())

def _execute_workflow_with_live_display(
    engine: WorkflowEngine, workflow_def: Dict, input_values: Dict,
    overall_progress_container: st.container, steps_display_container: st.container, options: Dict
) -> WorkflowExecutionResult:
    """ステップごとのライブ表示と結果カード表示を行いながらワークフローを実行"""
    # WorkflowEngine に _generate_execution_id があることを前提とする
    execution_id = engine._generate_execution_id() if hasattr(engine, '_generate_execution_id') else "temp-exec-id-" + str(time.time())
    start_time = datetime.datetime.now()
    total_steps_count = len(workflow_def.get('steps', []))
    
    # 初期実行状態
    execution_state = {
        'execution_id': execution_id, 
        'workflow_name': workflow_def.get('name', '無名ワークフロー'),
        'status': ExecutionStatus.RUNNING, 
        'current_step': 0, # 0は開始前を示す
        'total_steps': total_steps_count, 
        'start_time': start_time,
        'completed_step_result': None, # 直前に完了したステップの結果 (オプション)
        'error': None # ワークフロー全体のエラーメッセージ
    }

    # 全体進捗表示の更新関数
    def update_overall_progress():
        if options.get('show_progress', True): # オプションで進捗表示を制御
            with overall_progress_container:
                _render_execution_progress(execution_state, workflow_def) # workflow_defも渡す

    update_overall_progress() # 実行開始時の初期進捗表示

    step_results_list: List[StepResult] = [] # 実行されたステップの結果を格納
    context = input_values.copy() # グローバル入力でコンテキストを初期化

    # ステップごとのループ処理
    for step_index, step_config in enumerate(workflow_def.get('steps', [])):
        current_step_number = step_index + 1
        step_start_inner_time = time.time() # ステップ内部処理時間計測用
        step_name_str = step_config.get('name', f'ステップ {current_step_number}') # Renamed

        # 現在のステップ情報を更新して全体進捗を表示
        execution_state.update({
            'current_step': current_step_number, 
            'step_name': step_name_str,
            'completed_step_result': None # 新しいステップ開始前にクリア
        })
        update_overall_progress()

        # ライブステップ表示用のプレースホルダー
        live_step_ui_placeholder: Optional[st.empty] = None
        with steps_display_container:
            live_step_ui_placeholder = render_workflow_live_step(current_step_number, step_name_str, status="running")
        
        current_step_result: StepResult # 型ヒント
        try:
            # WorkflowEngine の _execute_step_with_retry を呼び出す
            # このメソッドはStepResultオブジェクトを返すことを期待
            # また、cache と retry オプションを渡す
            with st.spinner(f"Step {current_step_number}: {step_name_str} を処理中..."): # Streamlitスピナー
                current_step_result = engine._execute_step_with_retry(
                    step_config, context, current_step_number, execution_id, workflow_def.get('name', '無名ワークフロー'),
                    use_cache=options.get('cache_results', True), # キャッシュオプションを渡す
                    auto_retry=options.get('auto_retry', True)    # リトライオプションを渡す
                )
        except Exception as e_step_exec: # _execute_step_with_retry 自体の呼び出しエラー
            prompt_for_error = "プロンプト準備中にエラー発生"
            try: # エラーが発生したステップで使われるはずだったプロンプトを取得試行
                if hasattr(engine, 'variable_processor') and isinstance(engine.variable_processor, VariableProcessor):
                    prompt_for_error = engine.variable_processor.substitute_variables(step_config.get('prompt_template',''), context)
            except: pass # プロンプト取得失敗は無視

            current_step_result = StepResult(
                success=False, step_number=current_step_number, step_name=step_name_str,
                prompt=prompt_for_error, response="", tokens=0, cost=0.0,
                execution_time=(time.time() - step_start_inner_time), # エラーでも時間は記録
                error=f"ステップ実行中の予期せぬエラー: {str(e_step_exec)}"
            )
            # StepResultに必要な他のデフォルト値を設定

        # StepResultに実行時間がない場合は設定 (エンジン側で設定されていれば不要)
        if not hasattr(current_step_result, 'execution_time') or current_step_result.execution_time is None:
            current_step_result.execution_time = time.time() - step_start_inner_time
        
        step_results_list.append(current_step_result)
        st.session_state.current_workflow_steps.append(current_step_result) # セッションにも保存 (オプション)

        # ライブ表示プレースホルダーをクリアし、結果カードを表示
        if live_step_ui_placeholder:
            live_step_ui_placeholder.empty()
        with steps_display_container:
            render_workflow_step_card(current_step_result, current_step_number, show_prompt=options.get('debug_mode', False))
            workflow_execution_id=execution_id

        # ステップが失敗した場合
        if not getattr(current_step_result, 'success', False):
            error_detail_str = getattr(current_step_result, 'error', '不明なステップエラー') # Renamed
            execution_state.update({'status': ExecutionStatus.FAILED, 'error': error_detail_str})
            update_overall_progress()
            # WorkflowEngine に _create_failure_result があることを前提とする
            return engine._create_failure_result(execution_id, workflow_def.get('name', '無名ワークフロー'), start_time, error_detail_str, step_results_list)

        # 次のステップのためにコンテキストを更新
        context[f'step_{current_step_number}_output'] = getattr(current_step_result, 'response', "")
        execution_state['completed_step_result'] = current_step_result # 完了したステップ情報を状態に保存
        
        # Git履歴への記録 (StepResultにgit_recordが含まれている場合)
        if hasattr(current_step_result, 'git_record') and current_step_result.git_record:
            GitManager.add_commit_to_history(current_step_result.git_record)

    # 全てのステップが成功した場合
    execution_state.update({'status': ExecutionStatus.COMPLETED})
    update_overall_progress() # 最終的な進捗表示
    # WorkflowEngine に _create_success_result があることを前提とする
    return engine._create_success_result(execution_id, workflow_def.get('name', '無名ワークフロー'), start_time, step_results_list)

def _render_execution_progress(state: Dict, workflow_def: Dict):
    """ワークフロー全体の実行進捗を表示"""
    status: ExecutionStatus = state.get('status', ExecutionStatus.PENDING)
    current_step_num: int = state.get('current_step', 0)
    total_steps_count: int = state.get('total_steps', len(workflow_def.get('steps', [])))
    progress_value: float = float(current_step_num) / total_steps_count if total_steps_count > 0 else 0.0

    workflow_name_str: str = state.get('workflow_name', workflow_def.get('name', '無名ワークフロー'))

    if status == ExecutionStatus.RUNNING:
        st.progress(progress_value)
        step_name_str: str = state.get('step_name', f'Step {current_step_num}')
        st.caption(f"実行中: {step_name_str} ({current_step_num}/{total_steps_count} ステップ) - {workflow_name_str}")
    elif status == ExecutionStatus.COMPLETED:
        st.progress(1.0)
        st.caption(f"🎉 ワークフロー '{workflow_name_str}' 完了！ ({total_steps_count} ステップ)")
    elif status == ExecutionStatus.FAILED:
        st.progress(progress_value)
        error_msg: str = state.get('error', '不明なエラー')
        st.caption(f"❌ ワークフロー '{workflow_name_str}' 失敗。({current_step_num}/{total_steps_count} で停止) エラー: {error_msg}")
    elif status == ExecutionStatus.PENDING:
        st.caption(f"ワークフロー '{workflow_name_str}' 準備中...")
    # 他のステータス（例: CANCELLED）も必要に応じて追加

def _render_workflow_result(result: WorkflowExecutionResult, debug_mode: bool):
    """改善されたワークフロー結果表示"""
    # render_workflow_execution_summary(result) # サマリーは render_workflow_result_tabs 内で表示される想定
    render_workflow_result_tabs(result, debug_mode) # メインの結果表示

    # Git履歴への記録 (ワークフロー全体の結果として)
    if getattr(result, 'success', False): # 成功した場合のみ記録
        try:
            # コミット用データの作成
            commit_data = {
                'timestamp': getattr(result, 'end_time', getattr(result, 'start_time', datetime.datetime.now())),
                'execution_mode': 'ワークフロー実行', # 実行モード
                'workflow_id': getattr(result, 'execution_id', 'N/A'), # ワークフロー実行ID
                'workflow_name': getattr(result, 'workflow_name', 'N/A'), # ワークフロー名
                'final_prompt': f"ワークフロー: {getattr(result, 'workflow_name', 'N/A')} ({len(getattr(result, 'steps',[]))}ステップ完了)", # 最終プロンプトの代わり
                'response': getattr(result, 'final_output', ""), # 最終出力
                'evaluation': f"ワークフロー正常完了: {len(getattr(result, 'steps',[]))}ステップ, {getattr(result, 'duration_seconds', 0.0):.1f}秒", # 評価の代わり
                'execution_tokens': getattr(result, 'total_tokens', 0), # 総トークン数
                'evaluation_tokens': 0, # ワークフロー自体には評価トークンはない
                'execution_cost': getattr(result, 'total_cost', 0.0), # 総コスト
                'evaluation_cost': 0.0, # ワークフロー自体には評価コストはない
                'total_cost': getattr(result, 'total_cost', 0.0), # 総コスト
                'model_name': 'ワークフロー (複数モデルの可能性あり)', # 使用モデル
                'model_id': 'workflow_execution_summary' # モデルIDの代わり
            }
            commit_message = f"ワークフロー完了: {getattr(result, 'workflow_name', 'N/A')} (ID: {getattr(result, 'execution_id', 'N/A')})"
            
            # GitManager を使ってコミット作成と履歴追加
            workflow_git_record = GitManager.create_commit(commit_data, commit_message)
            GitManager.add_commit_to_history(workflow_git_record)
            
            st.info(f"📝 ワークフロー全体の実行結果をGit履歴に記録しました (Commit: `{workflow_git_record.get('commit_hash', 'N/A')[:7]}`)")
        except Exception as e_git_record: # Renamed
            st.warning(f"⚠️ Git履歴へのワークフロー全体結果の記録中にエラーが発生しました: {str(e_git_record)}")
    else: # ワークフローが失敗した場合
        _render_workflow_error(result) # エラー詳細を表示

def _display_latest_results():
    """単発実行結果の表示（改善版）"""
    if not st.session_state.get('latest_execution_result'): return

    result_data: Dict[str, Any] = st.session_state.latest_execution_result
    initial_exec_res: Dict[str, Any] = result_data.get('execution_result', {})
    eval_res: Dict[str, Any] = result_data.get('evaluation_result', {})

    result_col1, result_col2 = st.columns([2, 1])
    with result_col1:
        render_response_box(initial_exec_res.get('response_text', '応答なし'), "🤖 LLMの回答")
        render_evaluation_box(eval_res.get('response_text', '評価なし'), "⭐ 評価結果")
    with result_col2:
        st.markdown("### 📊 実行・評価情報")
        st.metric("モデル名", initial_exec_res.get('model_name', 'N/A'))
        st.markdown("---")
        st.markdown("**実行結果**")
        cols_exec = st.columns(2) # Renamed for clarity
        with cols_exec[0]:
            st.metric("入力トークン", f"{initial_exec_res.get('input_tokens', 0):,}")
            st.metric("総トークン", f"{initial_exec_res.get('total_tokens', 0):,}")
        with cols_exec[1]:
            st.metric("出力トークン", f"{initial_exec_res.get('output_tokens', 0):,}")
            st.metric("コスト", format_detailed_cost_display(initial_exec_res.get('cost_usd', 0.0)))
        st.markdown("---")
        st.markdown("**評価処理**")
        cols_eval = st.columns(2) # Renamed for clarity
        with cols_eval[0]:
            st.metric("入力トークン", f"{eval_res.get('input_tokens', 0):,}")
            st.metric("総トークン", f"{eval_res.get('total_tokens', 0):,}")
        with cols_eval[1]:
            st.metric("出力トークン", f"{eval_res.get('output_tokens', 0):,}")
            st.metric("コスト", format_detailed_cost_display(eval_res.get('cost_usd', 0.0)))
        st.markdown("---")
        total_combined_cost = initial_exec_res.get('cost_usd', 0.0) + eval_res.get('cost_usd', 0.0)
        st.metric("合計コスト", format_detailed_cost_display(total_combined_cost))

def _render_workflow_error(result: WorkflowExecutionResult):
     """詳細なエラー表示とリカバリー提案"""
     workflow_name_str = getattr(result, 'workflow_name', '無名ワークフロー')
     st.error(f"❌ ワークフロー実行失敗: {workflow_name_str}")
     
     error_handler = WorkflowErrorHandler() # core.workflow_engine からインポート
     error_message_str = str(getattr(result, 'error', "不明なエラー"))
     error_type, description, suggestions = error_handler.categorize_error(error_message_str)
     
     render_error_details(error_type, description, suggestions) # description の方がエラーメッセージとして適切か確認
     
     steps_list = getattr(result, 'steps', [])
     if steps_list:
         st.markdown("### 📋 完了済みステップ (エラー発生前まで)")
         for step_result_item in steps_list:
             if getattr(step_result_item, 'success', False):
                 st.success(f"✅ Step {getattr(step_result_item, 'step_number', '?')}: {getattr(step_result_item, 'step_name', '無名ステップ')}")
             else:
                 # エラーが発生したステップの情報は render_workflow_step_card で表示されているはず
                 # ここで重複して表示するかは設計次第
                 # st.error(f"❌ Step {getattr(step_result_item, 'step_number', '?')}: {getattr(step_result_item, 'step_name', '無名ステップ')} - {str(getattr(step_result_item, 'error', 'エラー詳細不明'))}")
                 break # 最初の失敗ステップでリスト表示を停止

def _render_prompt_section_form(execution_mode: str) -> Tuple[str, str, str]:
    st.markdown("### 📝 プロンプト")
    # セッション状態からデフォルト値を取得
    prompt_template_val = st.session_state.get('prompt_template', "以下のテキストを要約してください：\n\n{user_input}")
    user_input_data_val = st.session_state.get('user_input_data', "")
    single_prompt_val = st.session_state.get('single_prompt', "")

    if execution_mode == "テンプレート + データ入力":
        template_col1, template_col2 = st.columns(2)
        with template_col1:
            st.markdown("**テンプレート**")
            prompt_template_val = st.text_area("", value=prompt_template_val, height=200, placeholder="{user_input}でデータを参照", key="template_area_form_single_exec", label_visibility="collapsed")
        with template_col2:
            st.markdown("**データ**")
            user_input_data_val = st.text_area("", value=user_input_data_val, height=200, placeholder="処理したいデータを入力...", key="data_area_form_single_exec", label_visibility="collapsed")
        
        if prompt_template_val and user_input_data_val and "{user_input}" in prompt_template_val:
            if st.checkbox("🔍 最終プロンプトを確認", key="preview_form_single_exec"):
                final_prompt_preview = prompt_template_val.replace("{user_input}", user_input_data_val)
                display_preview = final_prompt_preview[:500] + ("..." if len(final_prompt_preview) > 500 else "")
                st.code(display_preview, language='text') # language=None or 'text'
        elif prompt_template_val and "{user_input}" not in prompt_template_val and user_input_data_val.strip():
            # データはあるが、テンプレートに{user_input}がない場合
            st.warning("⚠️ データが入力されていますが、プロンプトテンプレートにプレースホルダ {user_input} が見つかりません。データは使用されません。")
        # single_prompt_val はこのモードでは使用されないので、セッションのデフォルト値のまま
    else:  # 単一プロンプトモード
        st.markdown("**プロンプト**")
        single_prompt_val = st.text_area("", value=single_prompt_val, height=200, placeholder="プロンプトを入力してください...", key="single_area_form_single_exec", label_visibility="collapsed")
        # prompt_template_val と user_input_data_val はこのモードでは使用されないので、セッションのデフォルト値のまま
    return prompt_template_val, user_input_data_val, single_prompt_val

def _render_evaluation_section_form() -> str:
    st.markdown("### 📋 評価基準")
    evaluation_criteria_val = st.text_area(
        "", 
        value=st.session_state.get('evaluation_criteria', "1. 正確性（30点）\n2. 網羅性（25点）..."), 
        height=120, 
        key="criteria_area_form_single_exec", 
        label_visibility="collapsed"
    )
    return evaluation_criteria_val

def _execute_prompt_and_evaluation_sequentially(
    execution_memo: str, execution_mode: str,
    prompt_template_val: str, user_input_data_val: str, single_prompt_val: str, evaluation_criteria_val: str,
    placeholder_intermediate_resp: st.empty, placeholder_intermediate_metrics: st.empty, placeholder_final_eval_info: st.empty
):
    # プレースホルダーをクリア
    placeholder_intermediate_resp.empty()
    placeholder_intermediate_metrics.empty()
    placeholder_final_eval_info.empty()
    st.session_state.latest_execution_result = None # 前回の結果をクリア

    # 入力検証
    validation_errors = _validate_inputs_direct(execution_memo, execution_mode, evaluation_criteria_val, prompt_template_val, user_input_data_val, single_prompt_val)
    if validation_errors:
        for err_msg in validation_errors: st.error(err_msg) # Renamed
        return

    # APIキーとモデル設定のチェック
    if not st.session_state.get('api_key'):
        st.error("❌ APIキーが設定されていません。設定タブでAPIキーを設定してください。")
        return
    selected_model_id = st.session_state.get('selected_model')
    if not selected_model_id:
        st.error("❌ 使用するモデルが選択されていません。設定タブでモデルを選択してください。")
        return
    model_config = get_model_config(selected_model_id)
    if not model_config:
        st.error(f"❌ 選択されたモデル '{selected_model_id}' の設定が見つかりません。設定ファイルを確認してください。")
        return

    # 評価器の初期化とプロンプトの準備
    evaluator = GeminiEvaluator(st.session_state.api_key, model_config)
    final_prompt_str: str = ""
    current_prompt_template_str: Optional[str] = None
    current_user_input_str: Optional[str] = None

    if execution_mode == "テンプレート + データ入力":
        final_prompt_str = prompt_template_val.replace("{user_input}", user_input_data_val)
        current_prompt_template_str = prompt_template_val
        current_user_input_str = user_input_data_val
    else: # 単一プロンプトモード
        final_prompt_str = single_prompt_val

    # 一次実行
    initial_exec_res: Optional[Dict[str, Any]] = None
    with st.spinner(f"🔄 {model_config.get('name', '選択モデル')}で一次実行中..."):
        initial_exec_res = evaluator.execute_prompt(final_prompt_str)

    if not initial_exec_res or not initial_exec_res.get('success'):
        with placeholder_final_eval_info.container(): # エラー表示は最終評価情報プレースホルダに
            error_msg_exec = initial_exec_res.get('error', '不明な一次実行エラー') if initial_exec_res else '一次実行結果がありません' # Renamed
            st.error(f"❌ 一次実行エラー: {error_msg_exec}")
        return

    # 一次実行結果の中間表示
    with placeholder_intermediate_resp.container():
        st.markdown("---"); st.subheader("📝 一次実行結果 (評価前)")
        render_response_box(initial_exec_res['response_text'], f"🤖 LLMの回答 ({initial_exec_res.get('model_name', '')})")
    with placeholder_intermediate_metrics.container():
        st.markdown("##### 📊 一次実行メトリクス")
        cols_metrics_interim = st.columns(3) # Renamed
        cols_metrics_interim[0].metric("実行入力トークン", f"{initial_exec_res.get('input_tokens', 0):,}")
        cols_metrics_interim[1].metric("実行出力トークン", f"{initial_exec_res.get('output_tokens', 0):,}")
        cols_metrics_interim[2].metric("実行コスト(USD)", f"${initial_exec_res.get('cost_usd', 0.0):.6f}")
        st.info("評価処理を自動的に開始します...")

    # 評価処理の実行
    eval_res: Optional[Dict[str, Any]] = None
    with st.spinner("📊 評価処理を実行中..."):
        eval_res = evaluator.evaluate_response(
            original_prompt=final_prompt_str,
            llm_response_text=initial_exec_res['response_text'],
            evaluation_criteria=evaluation_criteria_val
        )

    if not eval_res or not eval_res.get('success'):
        with placeholder_final_eval_info.container(): # エラー表示は最終評価情報プレースホルダに
            error_msg_eval = eval_res.get('error', '不明な評価処理エラー') if eval_res else '評価処理結果がありません' # Renamed
            st.error(f"❌ 評価処理エラー: {error_msg_eval}")
            st.warning("一次実行の結果は上記に表示されていますが、評価は失敗しました。記録は保存されません。")
        return

    # 中間表示をクリア
    placeholder_intermediate_resp.empty()
    placeholder_intermediate_metrics.empty()
    placeholder_final_eval_info.empty() # 最終評価情報プレースホルダもクリア（結果はst.session_state経由で再描画）

    # Git履歴への保存
    exec_data_to_save: Dict[str, Any] = {
        'timestamp': datetime.datetime.now(), # 保存時のタイムスタンプ
        'execution_mode': execution_mode,
        'prompt_template': current_prompt_template_str, # テンプレートモード時のみ値が入る
        'user_input': current_user_input_str,       # テンプレートモード時のみ値が入る
        'final_prompt': final_prompt_str,           # 実際にLLMに送られたプロンプト
        'criteria': evaluation_criteria_val,        # 使用した評価基準
        'response': initial_exec_res['response_text'], # LLMの一次回答
        'evaluation': eval_res['response_text'],       # LLMによる評価結果
        'execution_tokens': initial_exec_res.get('total_tokens', 0),
        'evaluation_tokens': eval_res.get('total_tokens', 0),
        'execution_cost': initial_exec_res.get('cost_usd', 0.0),
        'evaluation_cost': eval_res.get('cost_usd', 0.0),
        'total_cost': initial_exec_res.get('cost_usd', 0.0) + eval_res.get('cost_usd', 0.0),
        'model_name': initial_exec_res.get('model_name', 'N/A'), # 一次実行モデル名
        'model_id': initial_exec_res.get('model_id', 'N/A')      # 一次実行モデルID
    }
    exec_record = GitManager.create_commit(exec_data_to_save, execution_memo) # GitManager を使用
    GitManager.add_commit_to_history(exec_record) # GitManager を使用

    # セッション状態に最新結果を保存し、リランして表示を更新
    st.session_state.latest_execution_result = {
        'execution_result': initial_exec_res,
        'evaluation_result': eval_res,
        'execution_record': exec_record # GitManager が返すコミット情報
    }
    st.success(f"✅ 実行と評価が完了し、記録を保存しました。 | コミットID: `{exec_record.get('commit_hash', 'N/A')}`")
    st.rerun()


def _validate_inputs_direct(
    execution_memo: str, execution_mode: str, evaluation_criteria: str,
    prompt_template: str, user_input_data: str, single_prompt: str
) -> List[str]:
    errors: List[str] = []
    if not execution_memo.strip():
        errors.append("❌ 実行メモを入力してください。")
    if execution_mode == "テンプレート + データ入力":
        if not prompt_template.strip():
            errors.append("❌ プロンプトテンプレートを入力してください。")
        # user_input_data は空でも許容するケースがあるため、必須とはしない。
        # ただし、テンプレートが {user_input} を含んでいてデータが空の場合は警告。
        if "{user_input}" in prompt_template and not user_input_data.strip():
            errors.append("⚠️ テンプレートは {user_input} を使用しますが、データが入力されていません。")
        elif "{user_input}" not in prompt_template and user_input_data.strip():
            errors.append("⚠️ データが入力されていますが、テンプレートに {user_input} が含まれていません。このデータは使用されません。")

    elif execution_mode == "単一プロンプト": # モード名を正確に
        if not single_prompt.strip():
            errors.append("❌ プロンプトを入力してください。")
    else: # ありえないモード指定の場合
        errors.append(f"❌ 不明な実行モードです: {execution_mode}")

    if not evaluation_criteria.strip():
        errors.append("❌ 評価基準を入力してください。")
    return errors

def _get_default_prompt_template(step_index: int, available_vars: List[str]) -> str:
    """デフォルトプロンプトテンプレートを生成
    Args:
        step_index: 現在のステップのインデックス (0-based)
        available_vars: このステップで利用可能な変数のリスト
    """
    if step_index == 0: # 最初のステップ
        # 利用可能なグローバル変数のうち最初のものを使用する試み
        first_global_var = next((var for var in available_vars if not var.startswith("step_")), None)
        if first_global_var:
            return f"入力データ (変数名: {first_global_var}) を分析し、主要なポイントをまとめてください。\n\n{{{first_global_var}}}"
        else: # グローバル変数がない場合 (通常はUIで設定を強制するため発生しにくい)
            return "提供された初期データに基づいて分析を開始してください。"
    else: # 2番目以降のステップ
        # 直前のステップの出力を参照
        prev_step_output_var = f"step_{step_index}_output" # step_indexは0-basedなので、step_1の出力はstep_1_output
        if prev_step_output_var in available_vars:
            return f"前のステップ (Step {step_index}) の結果は以下の通りです。\n\n{{{prev_step_output_var}}}\n\nこの結果を踏まえて、さらに詳細な分析や次の指示を実行してください。"
        else: # 直前のステップ出力が見つからない場合 (通常発生しないはず)
            return f"前のステップの結果を利用して、処理を続けてください。(エラー: 変数 {{{prev_step_output_var}}} が見つかりません)"


def _validate_and_save_workflow(name: str, description: str, steps: List[Dict[str,Any]], global_vars: List[str]) -> bool:
    """ワークフローを検証して保存"""
    if not name.strip():
        st.error("❌ ワークフロー名を入力してください。")
        return False
    if not steps: # ステップが空のリストの場合
        st.error("❌ ワークフローには少なくとも1つのステップが必要です。")
        return False
    
    # 個々のステップの基本検証
    for i, step_item in enumerate(steps):
        if not step_item.get('name','').strip():
            st.error(f"❌ ステップ {i+1} の名前が入力されていません。")
            return False
        if not step_item.get('prompt_template','').strip():
            st.error(f"❌ ステップ {i+1} のプロンプトテンプレートが入力されていません。")
            return False

    # WorkflowManager を使った詳細検証
    workflow_definition_to_validate: Dict[str, Any] = { # Renamed
        'name': name, 
        'description': description, 
        'steps': steps, 
        'global_variables': global_vars
    }
    validation_errors = WorkflowManager.validate_workflow(workflow_definition_to_validate) # WorkflowManager を使用
    
    if validation_errors:
        for err_msg_validate in validation_errors: st.error(f"❌ {err_msg_validate}") # Renamed
        return False

    # WorkflowManager を使って保存
    # save_workflow は成功すればIDを、失敗すればNoneを返す想定
    workflow_id_saved = WorkflowManager.save_workflow(workflow_definition_to_validate) # Renamed, WorkflowManager を使用
    
    if workflow_id_saved:
        st.success(f"✅ ワークフロー「{name}」を保存しました（ID: {workflow_id_saved}）。")
        return True
    else:
        st.error("❌ ワークフローの保存に失敗しました。アプリケーションログを確認してください。")
        return False

# --- Test function for execution_tab.py (can be called from Streamlit UI for debugging) ---
def test_execution_tab_workflow_functions():
    """execution_tab.py内のワークフロー関連UI関数をテストするための関数"""
    st.markdown("## Execution Tab Workflow Function Test Area")
    st.caption("このセクションは開発時のデバッグ用です。")

    # モックデータ準備
    mock_workflow_def = {
        "id": "test_wf_001_for_ui_test", # UIテスト用の一意なID
        "name": "UIテスト用 文書分析フロー",
        "description": "UIコンポーネントのテストのため、文書を要約し、キーワードを抽出するフロー。",
        "global_variables": ["document_content", "analysis_focus"],
        "steps": [
            {
                "name": "ステップ1: 要約生成",
                "prompt_template": "以下の文書を、特に '{analysis_focus}' に焦点を当てて100字程度で要約してください。\n\n文書:\n{document_content}\n\n要約:",
            },
            {
                "name": "ステップ2: キーワード抽出",
                "prompt_template": "前のステップの要約から、'{analysis_focus}' に関連する重要なキーワードを5つ抽出してください。\n\n要約:\n{step_1_output}\n\nキーワード:",
            },
            {
                "name": "ステップ3: 感情分析 (失敗する可能性のあるステップ)",
                "prompt_template": "抽出されたキーワードに基づいて、元の文書全体の感情（ポジティブ、ネガティブ、ニュートラル）を分析してください。\n\nキーワードリスト:\n{step_2_output}\n\n感情分析結果:",
            }
        ],
        "created_at": datetime.datetime.now().isoformat()
    }
    mock_input_values = {
        "document_content": "Streamlitは、Pythonだけで迅速にウェブアプリケーションを構築できる人気のフレームワークです。データ可視化やプロトタイピングに優れており、多くの開発者に支持されています。しかし、大規模で複雑なアプリケーションには不向きな側面もあるという意見も聞かれます。",
        "analysis_focus": "フレームワークの利点と欠点"
    }
    mock_options = {'show_progress': True, 'debug_mode': True, 'cache_results': False, 'auto_retry': False}

    st.markdown("### UIコンポーネントテスト")
    if st.button("テスト: _render_workflow_info_panel", key="test_render_info_panel_button"):
        with st.container(border=True):
             _render_workflow_info_panel(mock_workflow_def)

    if st.button("テスト: _render_workflow_input_section", key="test_render_input_section_button"):
        with st.container(border=True):
            inputs = _render_workflow_input_section(mock_workflow_def)
            st.write("入力された値（UIテスト用、実際の値ではない）:", inputs) # 実際の入力はUI操作による

    if st.button("テスト: _render_execution_options", key="test_render_exec_options_button"):
        with st.container(border=True):
            options_ui = _render_execution_options()
            st.write("選択されたオプション:", options_ui)
    
    st.markdown("### 実行フローテスト（一部APIコールを伴う可能性あり）")
    # APIキーと選択モデルがセッションに設定されている場合のみフル実行テストボタンを表示
    api_key_present = st.session_state.get('api_key')
    selected_model_present = st.session_state.get('selected_model')

    if api_key_present and selected_model_present:
        if st.button("テスト: _execute_workflow_with_progress (フル実行)", key="test_exec_full_button"):
            st.info("フル実行テストを開始します。APIコールが発生する可能性があります。")
            with st.container(border=True):
                _execute_workflow_with_progress(mock_workflow_def, mock_input_values, mock_options)
    else:
        missing_configs = []
        if not api_key_present: missing_configs.append("APIキー")
        if not selected_model_present: missing_configs.append("選択モデル")
        st.warning(f"{'と'.join(missing_configs)}が未設定のため、フル実行テストはスキップされます。設定タブで設定してください。")

    st.markdown("### 進捗表示テスト")
    if st.button("テスト: _render_execution_progress", key="test_render_exec_progress_button"):
        mock_state_running = {
            'status': ExecutionStatus.RUNNING, 'current_step': 1, 'total_steps': 3,
            'step_name': 'ステップ1: 要約生成', 'workflow_name': 'UIテストフロー'
        }
        mock_state_completed = {
            'status': ExecutionStatus.COMPLETED, 'current_step': 3, 'total_steps': 3,
             'workflow_name': 'UIテストフロー'
        }
        mock_state_failed = {
            'status': ExecutionStatus.FAILED, 'current_step': 2, 'total_steps': 3,
            'step_name': 'ステップ2: キーワード抽出', 'workflow_name': 'UIテストフロー', 'error': 'テスト用APIエラー'
        }
        with st.container(border=True):
            st.subheader("実行中状態")
            _render_execution_progress(mock_state_running, mock_workflow_def)
            st.subheader("完了状態")
            _render_execution_progress(mock_state_completed, mock_workflow_def)
            st.subheader("失敗状態")
            _render_execution_progress(mock_state_failed, mock_workflow_def)
            
    st.info("注意: 上記テストはUIコンポーネントのレンダリング確認が主目的です。実際のデータ処理やAPI連携の完全なテストは別途行う必要があります。")


# このテスト関数をStreamlitアプリのどこか（例: デバッグ用のサイドバー）から呼び出せるようにする
# if st.sidebar.checkbox("実行タブのUIテスト機能を表示", key="show_exec_tab_test_ui"):
#    test_execution_tab_workflow_functions()