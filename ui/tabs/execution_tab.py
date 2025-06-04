# ============================================
# ui/tabs/execution_tab.py (OpenAI対応)
# ============================================
import sys
import os
import streamlit as st
import datetime
import json
import time
from typing import Dict, List, Any, Optional, Tuple, Union # Added Union

# パス解決 (ui/tabs/execution_tab.py から見た相対パス)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root_from_tab = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root_from_tab not in sys.path:
    sys.path.insert(0, project_root_from_tab)

from config import get_model_config # Direct import for model config
from core import GitManager, WorkflowEngine, WorkflowManager
from core.evaluator import GeminiEvaluator # For type hinting
from core.openai_evaluator import OpenAIEvaluator # For type hinting
from core.workflow_engine import StepResult, ExecutionStatus, WorkflowExecutionResult, WorkflowErrorHandler, VariableProcessor

from ui.components import (
    render_response_box, render_evaluation_box, render_workflow_result_tabs,
    render_error_details, render_workflow_step_card, render_workflow_live_step,
    render_workflow_execution_summary
)
from ui.styles import format_detailed_cost_display, format_tokens_display


def _initialize_session_state_exec_tab(): # Renamed to avoid conflict
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
        'current_workflow_execution': None,
        'workflow_execution_progress': {},
        'show_workflow_debug': False,
        'processing_mode': 'single',
        'current_workflow_steps': [],
        'temp_variables': ['input_1'],
        'temp_steps': [{}],
        # OpenAI specific UI states (if any, e.g. for 'instructions' field)
        # 'openai_instructions': "" 
    }
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# Evaluator is now passed as an argument
def render_execution_tab(evaluator: Union[GeminiEvaluator, OpenAIEvaluator]):
    _initialize_session_state_exec_tab()

    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.markdown("### 🚀 プロンプト実行")
    with header_col2:
        current_branch = GitManager.get_current_branch()
        st.markdown(f"**ブランチ:** `{current_branch}`")

    st.markdown("#### 実行モードを選択")
    mode_col1, mode_col2 = st.columns(2)
    with mode_col1:
        if st.button("📝 単発処理", use_container_width=True, help="1つのプロンプトを実行して結果を取得"):
            st.session_state.processing_mode = "single"
    with mode_col2:
        if st.button("🔄 ワークフロー処理", use_container_width=True, help="複数のステップを連鎖実行して最終結果を取得"):
            st.session_state.processing_mode = "workflow"

    if 'processing_mode' not in st.session_state:
        st.session_state.processing_mode = "single"
    st.markdown("---")

    if st.session_state.processing_mode == "single":
        _render_single_execution(evaluator) # Pass evaluator
    else:
        _render_workflow_execution(evaluator) # Pass evaluator

def _render_single_execution(evaluator: Union[GeminiEvaluator, OpenAIEvaluator]):
    st.markdown("### 📝 単発プロンプト実行")
    # ... (rest of the single execution UI, form definition)
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
        
        # TODO: Add OpenAI 'instructions' field if desired
        # openai_instructions_val = ""
        # selected_model_cfg = get_model_config(st.session_state.selected_model)
        # if selected_model_cfg.get('api_provider') == 'openai':
        #    openai_instructions_val = st.text_area("OpenAI Instructions (Optional)", value=st.session_state.get('openai_instructions', ""), height=75, key="openai_instructions_form")

        submitted = st.form_submit_button("🚀 実行 & 自動評価", type="primary", use_container_width=True)

    if submitted:
        st.session_state.execution_memo = execution_memo
        st.session_state.execution_mode = execution_mode_full
        st.session_state.prompt_template = prompt_template_val
        st.session_state.user_input_data = user_input_data_val
        st.session_state.single_prompt = single_prompt_val
        st.session_state.evaluation_criteria = evaluation_criteria_val
        # st.session_state.openai_instructions = openai_instructions_val # If field added

        placeholder_intermediate_resp = st.empty()
        placeholder_intermediate_metrics = st.empty()
        placeholder_final_eval_info = st.empty()

        _execute_prompt_and_evaluation_sequentially(
            evaluator, # Pass evaluator
            execution_memo, execution_mode_full,
            prompt_template_val, user_input_data_val, single_prompt_val, evaluation_criteria_val,
            placeholder_intermediate_resp, placeholder_intermediate_metrics, placeholder_final_eval_info
            # openai_instructions=openai_instructions_val # Pass if field added
        )

    if st.session_state.latest_execution_result:
        st.markdown("---")
        st.subheader("✅ 実行・評価完了結果")
        _display_latest_results()


def _render_workflow_execution(evaluator: Union[GeminiEvaluator, OpenAIEvaluator]):
    st.markdown("### 🔄 多段階ワークフロー実行")
    st.caption("複数のLLM処理ステップを順次実行し、前のステップの結果を次のステップで活用できます")

    workflow_tab1, workflow_tab2, workflow_tab3 = st.tabs([
        "💾 保存済みワークフロー", "🆕 新規ワークフロー作成", "🔧 高度な設定"
    ])

    with workflow_tab1:
        _render_saved_workflow_execution(evaluator) # Pass evaluator
    with workflow_tab2:
        _render_workflow_builder(evaluator) # Pass evaluator
    with workflow_tab3:
        _render_advanced_workflow_settings(evaluator) # Pass evaluator


def _render_saved_workflow_execution(evaluator: Union[GeminiEvaluator, OpenAIEvaluator]):
    saved_workflows = WorkflowManager.get_saved_workflows()
    if not saved_workflows:
        st.info("💡 保存済みワークフローがありません。「新規ワークフロー作成」タブで作成してください。")
        # ... (help text)
        return

    # ... (workflow selection UI) ...
    workflow_col1, workflow_col2 = st.columns([3, 1])
    selected_id: Optional[str] = None
    with workflow_col1:
        workflow_options = {wid: f"{wdef.get('name', '無名ワークフロー')} ({len(wdef.get('steps', []))}ステップ, {wdef.get('created_at', '')[:10] if wdef.get('created_at') else '日付不明'})" for wid, wdef in saved_workflows.items()}
        if workflow_options:
            selected_id = st.selectbox("ワークフロー選択", options=list(workflow_options.keys()), format_func=lambda x: workflow_options[x], index=0, key="saved_wf_select")
    # ... (delete/duplicate buttons)
    with workflow_col2:
        if selected_id: # Only show buttons if a workflow is selected
            if st.button("🗑️ 削除", help="選択したワークフローを削除", key=f"delete_wf_sidebar_{selected_id}"):
                if WorkflowManager.delete_workflow(selected_id):
                    st.success(f"✅ ワークフロー「{saved_workflows.get(selected_id, {}).get('name', selected_id)}」を削除しました")
                    st.rerun()
                else:
                    st.error("ワークフローの削除に失敗しました。")

            if st.button("📋 複製", help="選択したワークフローを複製", key=f"duplicate_wf_sidebar_{selected_id}"):
                original_workflow = WorkflowManager.get_workflow(selected_id)
                if original_workflow:
                    new_name = f"{original_workflow.get('name', '無名ワークフロー')} (コピー)"
                    new_id = WorkflowManager.duplicate_workflow(selected_id, new_name)
                    if new_id:
                        st.success(f"✅ ワークフロー「{new_name}」を作成し、保存しました。")
                        st.rerun()
                    else:
                        st.error("ワークフローの複製に失敗しました。")

    if selected_id:
        workflow_def = WorkflowManager.get_workflow(selected_id)
        if workflow_def:
            _render_workflow_info_panel(workflow_def)
            input_values = _render_workflow_input_section(workflow_def)
            execution_options = _render_execution_options()
            if st.button("🚀 ワークフロー実行", type="primary", use_container_width=True, key=f"run_wf_main_{selected_id}"):
                _execute_workflow_with_progress(evaluator, workflow_def, input_values, execution_options) # Pass evaluator
        else:
             st.error(f"選択されたワークフロー ID '{selected_id}' が見つかりません。")


def _render_workflow_builder(evaluator: Union[GeminiEvaluator, OpenAIEvaluator]): # Pass evaluator for test execution
    st.markdown("### 🆕 新規ワークフロー作成")
    # ... (rest of builder UI)
    with st.expander("📝 Step 1: 基本情報", expanded=True):
        basic_col1, basic_col2 = st.columns(2)
        with basic_col1:
            workflow_name = st.text_input("ワークフロー名", value=st.session_state.get('wf_builder_name_cache', ""), placeholder="例: 文書分析ワークフロー", key="wf_builder_name_input_main")
            st.session_state.wf_builder_name_cache = workflow_name
        with basic_col2:
            description = st.text_input("説明（任意）", value=st.session_state.get('wf_builder_desc_cache', ""), placeholder="例: 文書を分析し要約とレポートを生成", key="wf_builder_desc_input_main")
            st.session_state.wf_builder_desc_cache = description

    # ... (global variables and steps setup) ...
    global_variables: List[str] = []
    input_values_for_test: Dict[str, str] = {}
    with st.expander("📥 Step 2: 入力変数設定", expanded=True):
        st.markdown("このワークフローで使用するグローバル入力変数を定義してください（例: `document_text`, `user_query`）。")
        current_temp_vars = list(st.session_state.temp_variables)
        for i, var_name_in_session in enumerate(current_temp_vars):
            var_col1, var_col2, var_col3 = st.columns([2, 3, 1])
            with var_col1:
                new_var_name = st.text_input(f"変数名 {i+1}", value=var_name_in_session, key=f"var_name_builder_main_{i}", help="英数字とアンダースコアのみ")
                if new_var_name != var_name_in_session:
                    if new_var_name.isidentifier(): st.session_state.temp_variables[i] = new_var_name
                    # ... (validation warnings)
                if new_var_name.isidentifier() and new_var_name not in global_variables: global_variables.append(new_var_name)
            with var_col2:
                if new_var_name and new_var_name.isidentifier():
                     input_values_for_test[new_var_name] = st.text_area(f"「{new_var_name}」のテスト用データ", value=st.session_state.get(f'var_test_builder_data_main_{new_var_name}', ""), key=f"var_test_builder_main_{i}", height=80)
                     st.session_state[f'var_test_builder_data_main_{new_var_name}'] = input_values_for_test[new_var_name]
            with var_col3:
                if len(st.session_state.temp_variables) > 1 and st.button("➖", key=f"remove_var_builder_main_{i}"):
                    st.session_state.temp_variables.pop(i)
                    st.rerun()
        if st.button("➕ 変数を追加", key="add_var_builder_main"):
            st.session_state.temp_variables.append(f"input_{len(st.session_state.temp_variables) + 1}")
            st.rerun()

    steps_config: List[Dict[str, Any]] = []
    with st.expander("🔧 Step 3: ワークフローステップ設定", expanded=True):
        current_temp_steps = list(st.session_state.temp_steps)
        for i, step_data_in_session in enumerate(current_temp_steps):
            st.markdown(f"--- \n#### 📋 ステップ {i+1}")
            step_col1, step_col2 = st.columns([3, 1])
            current_step_name = step_data_in_session.get('name', f"ステップ {i+1}")
            available_vars_for_step = global_variables.copy()
            if i > 0: available_vars_for_step.extend([f"step_{j+1}_output" for j in range(i)])
            current_prompt_template = step_data_in_session.get('template', _get_default_prompt_template(i, available_vars_for_step))

            with step_col1:
                step_name_input = st.text_input("ステップ名", value=current_step_name, key=f"step_name_builder_main_{i}")
            with step_col2:
                if len(st.session_state.temp_steps) > 1 and st.button("🗑️ このステップを削除", key=f"remove_step_builder_main_{i}"):
                    st.session_state.temp_steps.pop(i)
                    st.rerun()
            _render_variable_help(available_vars_for_step)
            prompt_template_input = st.text_area("プロンプトテンプレート", value=current_prompt_template, key=f"step_prompt_builder_main_{i}", height=150)
            if st.checkbox(f"ステップ {i+1} プレビュー表示", key=f"preview_builder_main_{i}"):
                _render_prompt_preview(prompt_template_input, input_values_for_test, i, steps_config) # Pass current steps_config
            
            current_step_config = {'name': step_name_input, 'prompt_template': prompt_template_input}
            steps_config.append(current_step_config)
            st.session_state.temp_steps[i] = current_step_config
        if st.button("➕ ステップを追加", key="add_step_builder_main"):
            st.session_state.temp_steps.append({})
            st.rerun()

    st.markdown("### 🎯 アクション")
    action_col1, action_col2, action_col3 = st.columns(3)
    with action_col1:
        if st.button("💾 保存", use_container_width=True, key="save_wf_builder_main"):
            if _validate_and_save_workflow(workflow_name, description, steps_config, global_variables):
                # Reset builder state
                st.session_state.wf_builder_name_cache = ""
                st.session_state.wf_builder_desc_cache = ""
                st.session_state.temp_variables = ['input_1']
                st.session_state.temp_steps = [{}]
                st.rerun()
    with action_col2:
        if st.button("🧪 テスト実行", use_container_width=True, key="test_wf_builder_main"):
            if workflow_name and steps_config:
                workflow_def_to_test = {'name': workflow_name, 'description': description, 'steps': steps_config, 'global_variables': global_variables}
                test_options = {'show_progress': True, 'debug_mode': True, 'cache_results': False, 'auto_retry': False}
                _execute_workflow_with_progress(evaluator, workflow_def_to_test, input_values_for_test, test_options) # Pass evaluator
            else:
                st.warning("テスト実行には、ワークフロー名と少なくとも1つのステップ定義が必要です。")
    with action_col3:
        if st.button("🔄 リセット", use_container_width=True, key="reset_wf_builder_main"):
            # Reset builder state
            st.session_state.wf_builder_name_cache = ""
            st.session_state.wf_builder_desc_cache = ""
            st.session_state.temp_variables = ['input_1']
            st.session_state.temp_steps = [{}]
            st.rerun()


def _render_advanced_workflow_settings(evaluator: Union[GeminiEvaluator, OpenAIEvaluator]): # Pass evaluator
    st.markdown("### 🔧 高度な設定")
    # ... (cache management)
    st.markdown("#### 💾 キャッシュ管理")
    if st.button("🗑️ エンジンキャッシュクリア", use_container_width=True, key="clear_engine_cache_advanced_main"):
        engine = WorkflowEngine(evaluator) # Initialize with current evaluator
        if hasattr(engine, 'clear_cache') and callable(engine.clear_cache):
            engine.clear_cache()
            st.success("✅ WorkflowEngineの実行キャッシュをクリアしました。")
        else:
            st.info("現在のWorkflowEngineはキャッシュクリア機能を持っていません。")
            
    # ... (debug tools, export/import remains largely the same)
    st.markdown("---")
    st.markdown("#### 🐛 デバッグツール")
    debug_col1, debug_col2 = st.columns(2)
    with debug_col1:
        st.checkbox("詳細ログ出力 (コンソール)", key="debug_verbose_logging_adv_main", value=False)
        debug_show_substitution = st.checkbox("変数置換の詳細表示 (UI)", key="debug_show_substitution_adv_main", value=st.session_state.get('show_workflow_debug', False))
        if debug_show_substitution != st.session_state.get('show_workflow_debug', False):
             st.session_state.show_workflow_debug = debug_show_substitution
             st.rerun()
    with debug_col2:
        debug_measure_time = st.checkbox("実行時間計測の詳細表示 (UI)", key="debug_measure_time_adv_main", value=st.session_state.get('show_workflow_debug', False))
        if debug_measure_time != st.session_state.get('show_workflow_debug', False):
             st.session_state.show_workflow_debug = debug_measure_time
             st.rerun()
        st.checkbox("メモリ使用量の監視 (コンソール)", key="debug_monitor_memory_adv_main", value=False)
    
    st.markdown("---")
    st.markdown("#### 📤 エクスポート・インポート (ワークフロー定義)")
    export_col1, export_col2 = st.columns(2)
    with export_col1:
        st.markdown("**エクスポート**")
        saved_workflows_adv = WorkflowManager.get_saved_workflows()
        if saved_workflows_adv:
            workflow_names_adv = {wid: wdef.get('name', '無名ワークフロー') for wid, wdef in saved_workflows_adv.items()}
            selected_export_id_adv = st.selectbox("エクスポートするワークフロー", options=list(saved_workflows_adv.keys()), format_func=lambda x: workflow_names_adv.get(x,x), key="wf_export_select_adv_main")
            if selected_export_id_adv and st.button("📥 JSONでダウンロード", key="wf_export_button_adv_main"):
                json_data_export_adv = WorkflowManager.export_workflow(selected_export_id_adv)
                if json_data_export_adv:
                    st.download_button("💾 ダウンロード", data=json_data_export_adv, file_name=f"{workflow_names_adv.get(selected_export_id_adv, selected_export_id_adv)}.json", mime="application/json", key="wf_export_download_adv_main")
        else:
            st.caption("エクスポート可能な保存済みワークフローがありません。")
    with export_col2:
        st.markdown("**インポート**")
        uploaded_file_import_adv = st.file_uploader("ワークフロー定義JSONファイルを選択", type=["json"], key="wf_import_uploader_adv_main")
        if uploaded_file_import_adv and st.button("📤 インポート", key="wf_import_button_adv_main"):
            try:
                json_data_str_import_adv = uploaded_file_import_adv.read().decode('utf-8')
                import_result_adv = WorkflowManager.import_workflow(json_data_str_import_adv)
                if import_result_adv.get('success'):
                    st.success(f"✅ ワークフロー「{import_result_adv.get('workflow_name', '')}」をインポートしました (ID: {import_result_adv.get('workflow_id','')})")
                    st.rerun()
                else:
                    for err_item_adv in import_result_adv.get('errors', ['不明なインポートエラー']): st.error(f"❌ {err_item_adv}")
            except Exception as e_import_adv:
                st.error(f"❌ インポート処理中にエラー: {str(e_import_adv)}")


def _execute_prompt_and_evaluation_sequentially(
    evaluator: Union[GeminiEvaluator, OpenAIEvaluator], # Added evaluator
    execution_memo: str, execution_mode: str,
    prompt_template_val: str, user_input_data_val: str, single_prompt_val: str, evaluation_criteria_val: str,
    placeholder_intermediate_resp: st.empty, placeholder_intermediate_metrics: st.empty, placeholder_final_eval_info: st.empty,
    openai_instructions: Optional[str] = None # Optional for OpenAI
):
    placeholder_intermediate_resp.empty()
    placeholder_intermediate_metrics.empty()
    placeholder_final_eval_info.empty()
    st.session_state.latest_execution_result = None

    validation_errors = _validate_inputs_direct(execution_memo, execution_mode, evaluation_criteria_val, prompt_template_val, user_input_data_val, single_prompt_val)
    if validation_errors:
        for err_msg in validation_errors: st.error(err_msg)
        return

    # Evaluator is already initialized and passed, API key and model config are handled there
    
    final_prompt_str: str = ""
    current_prompt_template_str: Optional[str] = None
    current_user_input_str: Optional[str] = None

    if execution_mode == "テンプレート + データ入力":
        final_prompt_str = prompt_template_val.replace("{user_input}", user_input_data_val)
        current_prompt_template_str = prompt_template_val
        current_user_input_str = user_input_data_val
    else:
        final_prompt_str = single_prompt_val

    # Prepare API call parameters
    api_call_params = {"prompt": final_prompt_str}
    # For OpenAI, if instructions are provided and evaluator is OpenAIEvaluator
    if isinstance(evaluator, OpenAIEvaluator) and openai_instructions:
        api_call_params["instructions"] = openai_instructions


    initial_exec_res: Optional[Dict[str, Any]] = None
    with st.spinner(f"🔄 {evaluator.get_model_info()}で一次実行中..."): # Use evaluator.get_model_info()
        initial_exec_res = evaluator.execute_prompt(**api_call_params) # Use prepared params

    if not initial_exec_res or not initial_exec_res.get('success'):
        with placeholder_final_eval_info.container():
            error_msg_exec = initial_exec_res.get('error', '不明な一次実行エラー') if initial_exec_res else '一次実行結果がありません'
            st.error(f"❌ 一次実行エラー: {error_msg_exec}")
        return

    with placeholder_intermediate_resp.container():
        st.markdown("---"); st.subheader("📝 一次実行結果 (評価前)")
        render_response_box(initial_exec_res['response_text'], f"🤖 LLMの回答 ({initial_exec_res.get('model_name', '')})")
    with placeholder_intermediate_metrics.container():
        st.markdown("##### 📊 一次実行メトリクス")
        cols_metrics_interim = st.columns(3)
        cols_metrics_interim[0].metric("実行入力トークン", f"{initial_exec_res.get('input_tokens', 0):,}")
        cols_metrics_interim[1].metric("実行出力トークン", f"{initial_exec_res.get('output_tokens', 0):,}")
        cols_metrics_interim[2].metric("実行コスト(USD)", format_detailed_cost_display(initial_exec_res.get('cost_usd', 0.0)))
        st.info("評価処理を自動的に開始します...")

    eval_res: Optional[Dict[str, Any]] = None
    with st.spinner("📊 評価処理を実行中..."):
        eval_res = evaluator.evaluate_response(
            original_prompt=final_prompt_str,
            llm_response_text=initial_exec_res['response_text'],
            evaluation_criteria=evaluation_criteria_val
        )

    if not eval_res or not eval_res.get('success'):
        with placeholder_final_eval_info.container():
            error_msg_eval = eval_res.get('error', '不明な評価処理エラー') if eval_res else '評価処理結果がありません'
            st.error(f"❌ 評価処理エラー: {error_msg_eval}")
            st.warning("一次実行の結果は上記に表示されていますが、評価は失敗しました。記録は保存されません。")
        return

    placeholder_intermediate_resp.empty()
    placeholder_intermediate_metrics.empty()
    placeholder_final_eval_info.empty()

    exec_data_to_save: Dict[str, Any] = {
        'timestamp': datetime.datetime.now(),
        'execution_mode': execution_mode,
        'prompt_template': current_prompt_template_str,
        'user_input': current_user_input_str,
        'final_prompt': final_prompt_str,
        'criteria': evaluation_criteria_val,
        'response': initial_exec_res['response_text'],
        'evaluation': eval_res['response_text'],
        'execution_tokens': initial_exec_res.get('total_tokens', 0),
        'evaluation_tokens': eval_res.get('total_tokens', 0),
        'execution_cost': initial_exec_res.get('cost_usd', 0.0),
        'evaluation_cost': eval_res.get('cost_usd', 0.0),
        'total_cost': initial_exec_res.get('cost_usd', 0.0) + eval_res.get('cost_usd', 0.0),
        'model_name': initial_exec_res.get('model_name', 'N/A'),
        'model_id': initial_exec_res.get('model_id', 'N/A'),
        'api_provider': initial_exec_res.get('api_provider', 'gemini') # Store provider
    }
    exec_record = GitManager.create_commit(exec_data_to_save, execution_memo)
    GitManager.add_commit_to_history(exec_record)

    st.session_state.latest_execution_result = {
        'execution_result': initial_exec_res,
        'evaluation_result': eval_res,
        'execution_record': exec_record
    }
    st.success(f"✅ 実行と評価が完了し、記録を保存しました。 | コミットID: `{exec_record.get('commit_hash', 'N/A')}`")
    st.rerun()


def _execute_workflow_with_progress(
    evaluator: Union[GeminiEvaluator, OpenAIEvaluator], # Added evaluator
    workflow_def: Dict, input_values: Dict, options: Dict
):
    # API key check is implicitly handled by evaluator initialization in app.py
    # Model config is also handled by evaluator
    
    for var_name in workflow_def.get('global_variables', []):
        if not input_values.get(var_name, '').strip():
            st.error(f"❌ 必須入力変数 '{var_name}' の値が設定されていません。")
            return

    engine = WorkflowEngine(evaluator) # Initialize with the correct evaluator

    st.markdown("### 🔄 ワークフロー実行進捗")
    overall_progress_container = st.container()
    steps_display_container = st.container()
    final_result_container = st.container()
    st.session_state.current_workflow_steps = []

    try:
        result_object = _execute_workflow_with_live_display(
            engine, workflow_def, input_values,
            overall_progress_container, steps_display_container, options
        )
        with final_result_container:
            st.markdown("---")
            st.markdown("### 🎯 ワークフロー完了")
            _render_workflow_result(result_object, options.get('debug_mode', False))
    except Exception as e_exec_wf:
        st.error(f"❌ ワークフローの実行中に予期せぬメインエラーが発生しました: {str(e_exec_wf)}")


# Functions like _render_prompt_section_form, _render_evaluation_section_form,
# _display_latest_results, _render_workflow_info_panel, _render_workflow_input_section,
# _render_execution_options, _render_variable_help, _render_prompt_preview,
# _execute_workflow_with_live_display, _render_execution_progress, _render_workflow_result,
# _render_workflow_error, _validate_inputs_direct, _get_default_prompt_template,
# _validate_and_save_workflow remain largely the same but are called with the correct evaluator context.

# Helper functions (no change needed from original, just ensure they are present)
def _render_variable_help(available_vars: List[str]):
    if available_vars:
        st.markdown("**💡 利用可能な変数:**")
        cols = st.columns(min(len(available_vars), 3) if len(available_vars) > 1 else 1) # Max 3 columns
        
        var_groups = {'グローバル入力': [], '前のステップ結果': []}
        for var in available_vars:
            if var.startswith('step_') and var.endswith('_output'):
                var_groups['前のステップ結果'].append(var)
            else:
                var_groups['グローバル入力'].append(var)

        col_idx = 0
        for group_name, group_vars in var_groups.items():
            if group_vars:
                with cols[col_idx % len(cols)]:
                    st.markdown(f"*{group_name}:*")
                    for var in group_vars:
                        st.code(f"{{{var}}}")
                col_idx += 1

def _render_prompt_preview(template: str, input_values: Dict[str, str], current_step_index: int, previous_steps_config: List[Dict[str, Any]]):
    processor = VariableProcessor()
    context_for_preview = input_values.copy()
    for i, prev_step_conf in enumerate(previous_steps_config): # previous_steps_config is steps_config[:current_step_index]
        actual_prev_step_number = i + 1
        context_for_preview[f'step_{actual_prev_step_number}_output'] = f"[Step {actual_prev_step_number} ({prev_step_conf.get('name', '')}) の模擬出力]"
    try:
        preview_content = processor.substitute_variables(template, context_for_preview)
        st.markdown("**プレビュー:**")
        display_preview = preview_content[:500] + ("..." if len(preview_content) > 500 else "")
        st.text_area("プロンプトプレビュー", value=display_preview, height=150, key=f"preview_text_area_{current_step_index}_{template[:10]}_main", disabled=True)
    except Exception as e:
        st.warning(f"プレビューエラー: {str(e)}")

def _render_prompt_section_form(execution_mode: str) -> Tuple[str, str, str]:
    st.markdown("### 📝 プロンプト")
    prompt_template_val = st.session_state.get('prompt_template', "以下のテキストを要約してください：\n\n{user_input}")
    user_input_data_val = st.session_state.get('user_input_data', "")
    single_prompt_val = st.session_state.get('single_prompt', "")
    if execution_mode == "テンプレート + データ入力":
        template_col1, template_col2 = st.columns(2)
        with template_col1:
            st.markdown("**テンプレート**"); prompt_template_val = st.text_area("", value=prompt_template_val, height=200, key="template_area_form_single_exec_main", label_visibility="collapsed")
        with template_col2:
            st.markdown("**データ**"); user_input_data_val = st.text_area("", value=user_input_data_val, height=200, key="data_area_form_single_exec_main", label_visibility="collapsed")
        if prompt_template_val and user_input_data_val and "{user_input}" in prompt_template_val and st.checkbox("🔍 最終プロンプトを確認", key="preview_form_single_exec_main"):
            final_prompt_preview = prompt_template_val.replace("{user_input}", user_input_data_val)
            st.code(final_prompt_preview[:500] + "..." if len(final_prompt_preview)>500 else final_prompt_preview, language='text')
        elif prompt_template_val and "{user_input}" not in prompt_template_val and user_input_data_val.strip():
            st.warning("⚠️ データが入力されていますが、プロンプトテンプレートにプレースホルダ {user_input} が見つかりません。データは使用されません。")
    else:
        st.markdown("**プロンプト**"); single_prompt_val = st.text_area("", value=single_prompt_val, height=200, key="single_area_form_single_exec_main", label_visibility="collapsed")
    return prompt_template_val, user_input_data_val, single_prompt_val

def _render_evaluation_section_form() -> str:
    st.markdown("### 📋 評価基準")
    return st.text_area("", value=st.session_state.get('evaluation_criteria', "1. 正確性（30点）\n2. 網羅性（25点）..."), height=120, key="criteria_area_form_single_exec_main", label_visibility="collapsed")

def _display_latest_results():
    if not st.session_state.get('latest_execution_result'): return
    result_data = st.session_state.latest_execution_result
    initial_exec_res, eval_res = result_data.get('execution_result', {}), result_data.get('evaluation_result', {})
    result_col1, result_col2 = st.columns([2, 1])
    with result_col1:
        render_response_box(initial_exec_res.get('response_text', '応答なし'), "🤖 LLMの回答")
        render_evaluation_box(eval_res.get('response_text', '評価なし'), "⭐ 評価結果")
    with result_col2:
        st.markdown("### 📊 実行・評価情報"); st.metric("モデル名", initial_exec_res.get('model_name', 'N/A')); st.markdown("---")
        st.markdown("**実行結果**"); exec_cols = st.columns(2)
        exec_cols[0].metric("入力トークン", f"{initial_exec_res.get('input_tokens', 0):,}")
        exec_cols[0].metric("総トークン", f"{initial_exec_res.get('total_tokens', 0):,}")
        exec_cols[1].metric("出力トークン", f"{initial_exec_res.get('output_tokens', 0):,}")
        exec_cols[1].metric("コスト", format_detailed_cost_display(initial_exec_res.get('cost_usd', 0.0)))
        st.markdown("---"); st.markdown("**評価処理**"); eval_cols = st.columns(2)
        eval_cols[0].metric("入力トークン", f"{eval_res.get('input_tokens', 0):,}")
        eval_cols[0].metric("総トークン", f"{eval_res.get('total_tokens', 0):,}")
        eval_cols[1].metric("出力トークン", f"{eval_res.get('output_tokens', 0):,}")
        eval_cols[1].metric("コスト", format_detailed_cost_display(eval_res.get('cost_usd', 0.0)))
        st.markdown("---"); st.metric("合計コスト", format_detailed_cost_display(initial_exec_res.get('cost_usd', 0.0) + eval_res.get('cost_usd', 0.0)))

def _render_workflow_info_panel(workflow_def: Dict):
    st.markdown("#### 📊 ワークフロー詳細情報"); info_col1, info_col2, info_col3 = st.columns(3)
    created_date = (workflow_def.get('created_at', '')[:10] if workflow_def.get('created_at') else '日付不明')
    info_col1.metric("ステップ数", len(workflow_def.get('steps', [])))
    info_col2.metric("必要変数数", len(workflow_def.get('global_variables', [])))
    info_col3.metric("作成日", created_date)
    if workflow_def.get('description'): st.markdown(f"**説明:** {workflow_def['description']}")
    st.markdown("**ワークフロー構造:**")
    for i, step in enumerate(workflow_def.get('steps', [])):
        preview = step.get('prompt_template', '')[:100] + "..." if len(step.get('prompt_template', '')) > 100 else step.get('prompt_template', '')
        st.markdown(f"**Step {i+1}: {step.get('name', '無名ステップ')}**\n```\n{preview}\n```")
        if i < len(workflow_def.get('steps', [])) - 1: st.markdown("⬇️")
    st.markdown("---")

def _render_workflow_input_section(workflow_def: Dict) -> Dict[str, str]:
    input_values: Dict[str, str] = {}; global_vars = workflow_def.get('global_variables')
    if global_vars and isinstance(global_vars, list):
        st.markdown("### 📥 入力データ設定")
        for var_name in global_vars:
            desc = _generate_variable_description(var_name)
            wf_id = workflow_def.get('id', workflow_def.get('name', 'unknown_workflow'))
            input_values[var_name] = st.text_area(f"**{var_name}**", help=desc, placeholder=f"{var_name}の内容を入力...", key=f"workflow_input_main_{wf_id}_{var_name}", height=120)
            if input_values[var_name]: st.caption(f"📝 {len(input_values[var_name]):,} 文字")
    return input_values

def _generate_variable_description(var_name: str) -> str:
    descriptions = {'document': '分析対象の文書', 'data': '処理データ', 'input': '入力情報', 'text': 'テキスト内容', 'requirement': '要件', 'context': '背景情報'}
    for k, v in descriptions.items():
        if k in var_name.lower(): return f"ワークフローで使用する{v}"
    return f"変数 '{var_name}' の値"

def _render_execution_options() -> Dict[str, Any]:
    with st.expander("⚙️ 実行オプション", expanded=False):
        col1, col2 = st.columns(2)
        show_progress = col1.checkbox("進捗表示", value=True, key="wf_opt_show_progress_main")
        cache_results = col1.checkbox("結果キャッシュ利用", value=True, key="wf_opt_cache_main")
        auto_retry = col2.checkbox("自動リトライ", value=True, key="wf_opt_retry_main")
        debug_mode_ui = col2.checkbox("デバッグモード", value=st.session_state.get('show_workflow_debug', False), key="wf_opt_debug_main")
        if debug_mode_ui != st.session_state.get('show_workflow_debug', False):
            st.session_state.show_workflow_debug = debug_mode_ui; st.rerun()
        return {'show_progress': show_progress, 'cache_results': cache_results, 'auto_retry': auto_retry, 'debug_mode': debug_mode_ui}

def _execute_workflow_with_live_display(engine: WorkflowEngine, workflow_def: Dict, input_values: Dict, overall_progress_container: st.container, steps_display_container: st.container, options: Dict) -> WorkflowExecutionResult:
    exec_id = engine._generate_execution_id() if hasattr(engine, '_generate_execution_id') else f"temp-exec-id-{time.time()}"
    start_time_wf = datetime.datetime.now() # Renamed
    total_steps_wf = len(workflow_def.get('steps', [])) # Renamed
    exec_state = {'execution_id': exec_id, 'workflow_name': workflow_def.get('name', '無名'), 'status': ExecutionStatus.RUNNING, 'current_step': 0, 'total_steps': total_steps_wf, 'start_time': start_time_wf, 'completed_step_result': None, 'error': None} # Renamed
    def update_overall_progress_local(): # Renamed
        if options.get('show_progress', True):
            with overall_progress_container: _render_execution_progress(exec_state, workflow_def)
    update_overall_progress_local()
    step_results_list_wf: List[StepResult] = [] # Renamed
    context_wf = input_values.copy() # Renamed
    for step_idx, step_cfg in enumerate(workflow_def.get('steps', [])): # Renamed
        current_step_num_wf = step_idx + 1 # Renamed
        step_start_time_inner = time.time() # Renamed
        step_name_wf = step_cfg.get('name', f'ステップ {current_step_num_wf}') # Renamed
        exec_state.update({'current_step': current_step_num_wf, 'step_name': step_name_wf, 'completed_step_result': None})
        update_overall_progress_local()
        live_step_placeholder_ui: Optional[st.empty] = None # Renamed
        with steps_display_container: live_step_placeholder_ui = render_workflow_live_step(current_step_num_wf, step_name_wf, status="running")
        current_step_res_wf: StepResult # Renamed
        try:
            with st.spinner(f"Step {current_step_num_wf}: {step_name_wf} を処理中..."):
                current_step_res_wf = engine._execute_step_with_retry(step_cfg, context_wf, current_step_num_wf, exec_id, workflow_def.get('name', '無名'), use_cache=options.get('cache_results', True), auto_retry=options.get('auto_retry', True))
        except Exception as e_step_exec_wf: # Renamed
            prompt_err_wf = "プロンプト準備中にエラー" # Renamed
            try:
                if hasattr(engine, 'variable_processor') and isinstance(engine.variable_processor, VariableProcessor):
                    prompt_err_wf = engine.variable_processor.substitute_variables(step_cfg.get('prompt_template',''), context_wf)
            except: pass
            current_step_res_wf = StepResult(success=False, step_number=current_step_num_wf, step_name=step_name_wf, prompt=prompt_err_wf, response="", tokens=0, cost=0.0, execution_time=(time.time() - step_start_time_inner), error=f"ステップ実行中の予期せぬエラー: {str(e_step_exec_wf)}")
        if not hasattr(current_step_res_wf, 'execution_time') or current_step_res_wf.execution_time is None: current_step_res_wf.execution_time = time.time() - step_start_time_inner
        step_results_list_wf.append(current_step_res_wf)
        st.session_state.current_workflow_steps.append(current_step_res_wf)
        if live_step_placeholder_ui: live_step_placeholder_ui.empty()
        with steps_display_container: render_workflow_step_card(current_step_res_wf, current_step_num_wf, show_prompt=options.get('debug_mode', False), workflow_execution_id=exec_id)
        if not getattr(current_step_res_wf, 'success', False):
            err_detail_wf = getattr(current_step_res_wf, 'error', '不明なステップエラー') # Renamed
            exec_state.update({'status': ExecutionStatus.FAILED, 'error': err_detail_wf})
            update_overall_progress_local()
            return engine._create_failure_result(exec_id, workflow_def.get('name', '無名'), start_time_wf, err_detail_wf, step_results_list_wf)
        context_wf[f'step_{current_step_num_wf}_output'] = getattr(current_step_res_wf, 'response', "")
        exec_state['completed_step_result'] = current_step_res_wf
        if hasattr(current_step_res_wf, 'git_record') and current_step_res_wf.git_record: GitManager.add_commit_to_history(current_step_res_wf.git_record)
    exec_state.update({'status': ExecutionStatus.COMPLETED})
    update_overall_progress_local()
    return engine._create_success_result(exec_id, workflow_def.get('name', '無名'), start_time_wf, step_results_list_wf)

def _render_execution_progress(state: Dict, workflow_def: Dict):
    status_wf, current_step_wf, total_steps_count_wf = state.get('status', ExecutionStatus.PENDING), state.get('current_step', 0), state.get('total_steps', len(workflow_def.get('steps', []))) # Renamed vars
    progress_val_wf = float(current_step_wf) / total_steps_count_wf if total_steps_count_wf > 0 else 0.0 # Renamed
    workflow_name_str_wf = state.get('workflow_name', workflow_def.get('name', '無名ワークフロー')) # Renamed
    if status_wf == ExecutionStatus.RUNNING:
        st.progress(progress_val_wf); step_name_str_wf = state.get('step_name', f'Step {current_step_wf}') # Renamed
        st.caption(f"実行中: {step_name_str_wf} ({current_step_wf}/{total_steps_count_wf} ステップ) - {workflow_name_str_wf}")
    elif status_wf == ExecutionStatus.COMPLETED: st.progress(1.0); st.caption(f"🎉 ワークフロー '{workflow_name_str_wf}' 完了！ ({total_steps_count_wf} ステップ)")
    elif status_wf == ExecutionStatus.FAILED: st.progress(progress_val_wf); st.caption(f"❌ ワークフロー '{workflow_name_str_wf}' 失敗。({current_step_wf}/{total_steps_count_wf} で停止) エラー: {state.get('error', '不明')}")
    elif status_wf == ExecutionStatus.PENDING: st.caption(f"ワークフロー '{workflow_name_str_wf}' 準備中...")

def _render_workflow_result(result: WorkflowExecutionResult, debug_mode: bool):
    render_workflow_result_tabs(result, debug_mode)
    if getattr(result, 'success', False):
        try:
            commit_data_wf = { # Renamed
                'timestamp': getattr(result, 'end_time', datetime.datetime.now()), 'execution_mode': 'ワークフロー実行',
                'workflow_id': getattr(result, 'execution_id', 'N/A'), 'workflow_name': getattr(result, 'workflow_name', 'N/A'),
                'final_prompt': f"WF: {getattr(result, 'workflow_name', 'N/A')} ({len(getattr(result, 'steps',[]))}完了)",
                'response': getattr(result, 'final_output', ""),
                'evaluation': f"WF正常完了: {len(getattr(result, 'steps',[]))}ステップ, {getattr(result, 'duration_seconds', 0.0):.1f}秒",
                'execution_tokens': getattr(result, 'total_tokens', 0), 'evaluation_tokens': 0,
                'execution_cost': getattr(result, 'total_cost', 0.0), 'evaluation_cost': 0.0,
                'total_cost': getattr(result, 'total_cost', 0.0),
                'model_name': 'ワークフロー', 'model_id': 'workflow_summary',
                'api_provider': 'workflow' # Generic provider for workflow summary
            }
            commit_msg_wf = f"WF完了: {getattr(result, 'workflow_name', 'N/A')} (ID: {getattr(result, 'execution_id', 'N/A')})" # Renamed
            wf_git_record = GitManager.create_commit(commit_data_wf, commit_msg_wf) # Renamed
            GitManager.add_commit_to_history(wf_git_record)
            st.info(f"📝 WF実行結果をGit履歴に記録 (Commit: `{wf_git_record.get('commit_hash', 'N/A')[:7]}`)")
        except Exception as e_git_wf: st.warning(f"⚠️ Git履歴へのWF結果記録エラー: {str(e_git_wf)}") # Renamed
    else: _render_workflow_error(result)

def _render_workflow_error(result: WorkflowExecutionResult):
     workflow_name_err_wf = getattr(result, 'workflow_name', '無名ワークフロー') # Renamed
     st.error(f"❌ ワークフロー実行失敗: {workflow_name_err_wf}")
     err_handler_wf = WorkflowErrorHandler() # Renamed
     err_msg_str_wf = str(getattr(result, 'error', "不明なエラー")) # Renamed
     err_type_wf, desc_wf, suggestions_wf = err_handler_wf.categorize_error(err_msg_str_wf) # Renamed
     render_error_details(err_type_wf, desc_wf, suggestions_wf)
     steps_list_err_wf = getattr(result, 'steps', []) # Renamed
     if steps_list_err_wf:
         st.markdown("### 📋 完了済みステップ (エラー発生前まで)")
         for step_res_item_wf in steps_list_err_wf: # Renamed
             if getattr(step_res_item_wf, 'success', False): st.success(f"✅ Step {getattr(step_res_item_wf, 'step_number', '?')}: {getattr(step_res_item_wf, 'step_name', '無名')}")
             else: break

def _validate_inputs_direct(execution_memo: str, execution_mode: str, evaluation_criteria: str, prompt_template: str, user_input_data: str, single_prompt: str) -> List[str]:
    errors_val: List[str] = [] # Renamed
    if not execution_memo.strip(): errors_val.append("❌ 実行メモを入力してください。")
    if execution_mode == "テンプレート + データ入力":
        if not prompt_template.strip(): errors_val.append("❌ プロンプトテンプレートを入力してください。")
        if "{user_input}" in prompt_template and not user_input_data.strip(): errors_val.append("⚠️ テンプレートは {user_input} を使用しますが、データが空です。")
        elif "{user_input}" not in prompt_template and user_input_data.strip(): errors_val.append("⚠️ データ入力がありますが、テンプレートに {user_input} がありません。")
    elif execution_mode == "単一プロンプト" and not single_prompt.strip(): errors_val.append("❌ プロンプトを入力してください。")
    elif execution_mode not in ["テンプレート + データ入力", "単一プロンプト"]: errors_val.append(f"❌ 不明な実行モード: {execution_mode}")
    if not evaluation_criteria.strip(): errors_val.append("❌ 評価基準を入力してください。")
    return errors_val

def _get_default_prompt_template(step_index: int, available_vars: List[str]) -> str:
    if step_index == 0:
        first_global = next((v for v in available_vars if not v.startswith("step_")), None)
        return f"入力データ (変数名: {first_global or 'input_data'}) を分析し要点をまとめてください。\n\n{{{first_global or 'input_data'}}}" if first_global else "初期データに基づいて分析を開始してください。"
    else:
        prev_out_var = f"step_{step_index}_output" # step_index is 0-based, so step_1 output is for step_index=0 (next step is step_index=1)
        return f"前のステップ (Step {step_index}) の結果:\n\n{{{prev_out_var}}}\n\nこの結果を踏まえ、次の指示を実行してください。" if prev_out_var in available_vars else f"前のステップ結果を利用して処理を継続。(エラー: 変数 {{{prev_out_var}}} 不明)"

def _validate_and_save_workflow(name: str, description: str, steps: List[Dict[str,Any]], global_vars: List[str]) -> bool:
    if not name.strip(): st.error("❌ ワークフロー名を入力。"); return False
    if not steps: st.error("❌ 少なくとも1ステップ必要。"); return False
    for i, step_item_val in enumerate(steps): # Renamed
        if not step_item_val.get('name','').strip(): st.error(f"❌ ステップ {i+1} の名前未入力。"); return False
        if not step_item_val.get('prompt_template','').strip(): st.error(f"❌ ステップ {i+1} のテンプレート未入力。"); return False
    wf_def_val: Dict[str, Any] = {'name': name, 'description': description, 'steps': steps, 'global_variables': global_vars} # Renamed
    validation_errors_wf = WorkflowManager.validate_workflow(wf_def_val) # Renamed
    if validation_errors_wf:
        for err_msg_val_wf in validation_errors_wf: st.error(f"❌ {err_msg_val_wf}"); return False # Renamed
    wf_id_saved_val = WorkflowManager.save_workflow(wf_def_val) # Renamed
    if wf_id_saved_val: st.success(f"✅ ワークフロー「{name}」保存 (ID: {wf_id_saved_val})。"); return True
    else: st.error("❌ ワークフロー保存失敗。ログ確認。"); return False