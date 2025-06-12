# ui/tabs/execution_tab.py (修正後)

# ============================================
# ui/tabs/execution_tab.py (並列実行対応)
# ============================================
import sys
import os
import streamlit as st
import datetime
import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
import yaml

# パス解決
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root_from_tab = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root_from_tab not in sys.path:
    sys.path.insert(0, project_root_from_tab)

from core import GitManager, WorkflowEngine, WorkflowManager
from core.evaluator import GeminiEvaluator
from core.openai_evaluator import OpenAIEvaluator
from core.workflow_engine import StepResult, ExecutionStatus, WorkflowExecutionResult, WorkflowErrorHandler

from ui.components import (
    render_response_box, render_evaluation_box, render_workflow_result_tabs,
    render_error_details, render_workflow_live_step,
    render_workflow_execution_summary
)

def _initialize_session_state_exec_tab():
    defaults = {
        'execution_memo': "", 'execution_mode': "テンプレート + データ入力", 'prompt_template': "以下のテキストを要約してください：\n\n{user_input}",
        'user_input_data': "", 'single_prompt': "", 'evaluation_criteria': "1. 正確性\n2. 網羅性\n3. 明確さ",
        'latest_execution_result': None, 'processing_mode': 'single', 'wf_builder_name': '',
        'wf_builder_desc': '', 'temp_variables': ['input_1'], 
        'temp_steps': [{'name': 'step_1', 'prompt_template': '', 'dependencies': []}], # 👈 [修正] 依存関係キーを追加
        'openai_instructions': "You are a helpful assistant."
    }
    for key, default_value in defaults.items():
        if key not in st.session_state: st.session_state[key] = default_value

def render_execution_tab(evaluator: Union[GeminiEvaluator, OpenAIEvaluator]):
    _initialize_session_state_exec_tab()
    mode = st.radio("実行モードを選択", ["📝 単発処理", "🔄 ワークフロー処理"], horizontal=True, key="processing_mode_selector")
    st.session_state.processing_mode = "single" if mode == "📝 単発処理" else "workflow"
    st.markdown("---")
    if st.session_state.processing_mode == "single":
        _render_single_execution(evaluator)
    else:
        _render_workflow_execution(evaluator)

def _render_single_execution(evaluator: Union[GeminiEvaluator, OpenAIEvaluator]):
    st.markdown("### 📝 単発プロンプト実行")
    with st.form("execution_form", clear_on_submit=False):
        memo = st.text_input("📝 実行メモ", st.session_state.execution_memo, placeholder="変更内容や実験目的...")
        mode_display = st.radio("プロンプト形式", ["テンプレート", "単一"], index=0 if st.session_state.execution_mode == "テンプレート + データ入力" else 1, horizontal=True)
        mode_full = "テンプレート + データ入力" if mode_display == "テンプレート" else "単発実行"
        template, user_input, single_prompt = _render_prompt_section_form(mode_full)
        criteria = _render_evaluation_section_form()
        instructions = ""
        if isinstance(evaluator, OpenAIEvaluator):
           instructions = st.text_area("システムプロンプト (任意)", st.session_state.openai_instructions, height=75, help="モデルの役割や振る舞いを指示します。")
        submitted = st.form_submit_button("🚀 実行 & 自動評価", type="primary", use_container_width=True)

    if submitted:
        st.session_state.update(execution_memo=memo, execution_mode=mode_full, prompt_template=template,
                                user_input_data=user_input, single_prompt=single_prompt, evaluation_criteria=criteria,
                                openai_instructions=instructions if isinstance(evaluator, OpenAIEvaluator) else "")
        asyncio.run(_execute_prompt_and_evaluation(evaluator, memo, mode_full, template, user_input, single_prompt, criteria, instructions))

    if st.session_state.latest_execution_result:
        st.markdown("---"); st.subheader("✅ 直前の実行結果"); _display_latest_results()

def _render_workflow_execution(evaluator: Union[GeminiEvaluator, OpenAIEvaluator]):
    st.markdown("### 🔄 多段階ワークフロー実行")
    st.caption("複数のLLM処理ステップを順次実行し、前のステップの結果を次のステップで活用できます")
    tab1, tab2, tab3 = st.tabs(["💾 保存済みワークフロー", "🆕 新規ワークフロー作成", "🔧 高度な設定"])
    with tab1: _render_saved_workflow_execution(evaluator)
    with tab2: _render_workflow_builder()
    with tab3: _render_advanced_workflow_settings()

def _render_saved_workflow_execution(evaluator: Union[GeminiEvaluator, OpenAIEvaluator]):
    workflows = WorkflowManager.get_saved_workflows()
    if not workflows: st.info("💡 保存済みワークフローがありません。「新規ワークフロー作成」タブで作成してください。"); return
    options = {wid: f"{w.get('name', '無名')} ({len(w.get('source_yaml', {}).get('nodes', {})) or len(w.get('steps',[]))}ステップ)" for wid, w in workflows.items()}
    selected_id = st.selectbox("実行するワークフローを選択", options.keys(), format_func=lambda x: options[x])
    if selected_id:
        workflow_def = WorkflowManager.get_workflow(selected_id)
        if workflow_def:
            with st.expander("ワークフロー詳細", expanded=True):
                _render_workflow_info_panel(workflow_def)
                c1, c2 = st.columns(2)
                if c1.button("🗑️ 削除", key=f"del_{selected_id}", use_container_width=True):
                    if WorkflowManager.delete_workflow(selected_id): st.success("削除しました。"); st.rerun()
                if c2.button("📋 複製", key=f"dup_{selected_id}", use_container_width=True):
                    if WorkflowManager.duplicate_workflow(selected_id, f"{workflow_def.get('name','無名')} (コピー)"):
                        st.success("複製しました。"); st.rerun()
            inputs = _render_workflow_input_section(workflow_def)
            exec_options = _render_execution_options()
            if st.button("🚀 ワークフロー実行", type="primary", use_container_width=True, key=f"run_{selected_id}"):
                asyncio.run(_execute_workflow_with_progress(evaluator, workflow_def, inputs, exec_options))

def _render_workflow_builder():
    st.markdown("#### 🆕 新規ワークフロー作成")
    with st.container(border=True):
        st.markdown("##### 基本情報")
        name = st.text_input("ワークフロー名", st.session_state.wf_builder_name)
        desc = st.text_area("説明（任意）", st.session_state.wf_builder_desc)
        st.session_state.update(wf_builder_name=name, wf_builder_desc=desc)
        
        st.markdown("##### グローバル入力変数")
        st.caption("ワークフロー全体で利用できる変数を定義します。")
        g_vars = _render_variable_editor()
        
        st.markdown("##### ステップ設定")
        st.caption("処理の各ステップを定義します。ステップ名と依存関係を設定して並列実行を制御できます。")
        steps = _render_steps_editor(g_vars)
        
    c1, c2 = st.columns(2)
    if c1.button("💾 保存", use_container_width=True):
        # 👈 [修正] UIビルダーからの保存ロジック
        if _validate_and_save_workflow_from_builder(name, desc, steps, g_vars):
            st.session_state.update(
                wf_builder_name="", wf_builder_desc="", 
                temp_variables=['input_1'], 
                temp_steps=[{'name': 'step_1', 'prompt_template': '', 'dependencies': []}]
            )
            st.rerun()
            
    if c2.button("🔄 リセット", use_container_width=True):
        st.session_state.update(
            wf_builder_name="", wf_builder_desc="", 
            temp_variables=['input_1'], 
            temp_steps=[{'name': 'step_1', 'prompt_template': '', 'dependencies': []}]
        )
        st.rerun()

def _render_advanced_workflow_settings():
    st.markdown("#### 🔧 高度な設定"); st.markdown("**YAMLによるインポート/エクスポート**")
    c1, c2 = st.columns(2)
    with c1:
        yaml_file = st.file_uploader("YAMLからインポート", ["yaml", "yml"])
        st.info("💡 **ヒント:** GitHub Actionsライクな `nodes` 構文で並列実行を定義できます。まずはUIでワークフローを作成し、エクスポートしてフォーマットを確認してください。")
        if yaml_file and st.button("📤 インポート実行", use_container_width=True):
            result = WorkflowManager.import_from_yaml(yaml_file.read().decode('utf-8'))
            if result.get('success'): st.success(f"✅ 「{result.get('workflow_name', '')}」をインポートしました。"); st.rerun()
            else: st.error(f"❌ インポート失敗: {result.get('errors', ['不明'])[0]}")
    with c2:
        workflows = WorkflowManager.get_saved_workflows()
        if workflows:
            options = {wid: w.get('name', '無名') for wid, w in workflows.items()}
            export_id = st.selectbox("エクスポートするワークフロー", options.keys(), format_func=lambda x: options[x])
            if export_id:
                yaml_data = WorkflowManager.export_to_yaml(export_id)
                if yaml_data: st.download_button("📥 YAMLダウンロード", yaml_data, f"{options[export_id].replace(' ','_')}.yaml", "application/x-yaml", use_container_width=True)
        else: st.caption("エクスポート可能なワークフローがありません。")

async def _execute_prompt_and_evaluation(evaluator, memo, mode, template, user_input, single_prompt, criteria, instructions=None):
    # (この関数に変更はありません)
    st.session_state.latest_execution_result = None
    errors = _validate_inputs(memo, mode, criteria, template, user_input, single_prompt)
    if errors:
        for err in errors: st.error(err); return
    final_prompt = template.replace("{user_input}", user_input) if mode == "テンプレート + データ入力" else single_prompt
    
    with st.spinner(f"🔄 {evaluator.get_model_info()}で一次実行中..."):
        exec_res = await evaluator.execute_prompt(prompt=final_prompt, instructions=instructions)
    if not exec_res.get('success'): st.error(f"❌ 一次実行エラー: {exec_res.get('error', '不明')}"); return

    with st.spinner("📊 評価処理を実行中..."):
        eval_res = await evaluator.evaluate_response(final_prompt, exec_res['response_text'], criteria)
    if not eval_res.get('success'): st.error(f"❌ 評価処理エラー: {eval_res.get('error', '不明')}"); st.warning("一次実行は記録されますが、評価は失敗しました。")
    
    record = {'timestamp': datetime.datetime.now(), 'execution_mode': mode, 'prompt_template': template if mode == "テンプレート + データ入力" else None,
              'user_input': user_input if mode == "テンプレート + データ入力" else None, 'final_prompt': final_prompt, 'criteria': criteria,
              'response': exec_res['response_text'], 'evaluation': eval_res.get('response_text', '評価失敗'), 'execution_tokens': exec_res.get('total_tokens', 0),
              'evaluation_tokens': eval_res.get('total_tokens', 0), 'execution_cost': exec_res.get('cost_usd', 0.0), 'evaluation_cost': eval_res.get('cost_usd', 0.0),
              'total_cost': exec_res.get('cost_usd', 0.0) + eval_res.get('cost_usd', 0.0), 'model_name': exec_res.get('model_name', 'N/A'),
              'model_id': exec_res.get('model_id', 'N/A'), 'api_provider': exec_res.get('api_provider', 'unknown')}
    commit_record = GitManager.create_commit(record, memo)
    GitManager.add_commit_to_history(commit_record)
    st.session_state.latest_execution_result = {'execution_result': exec_res, 'evaluation_result': eval_res, 'execution_record': commit_record}
    st.success(f"✅ 実行完了。コミットID: `{commit_record.get('commit_hash', 'N/A')}`"); st.rerun()

async def _execute_workflow_with_progress(evaluator, workflow_def, inputs, options):
    # (この関数に変更はありません)
    for var in workflow_def.get('global_variables', []):
        if not inputs.get(var, '').strip(): st.error(f"❌ 必須入力変数 '{var}' が空です。"); return
    
    engine = WorkflowEngine(evaluator)
    st.markdown("---"); st.markdown("### 🔄 ワークフロー実行進捗")
    progress_container = st.container(border=True)
    placeholders = {}

    def progress_callback(state: Dict[str, Any]):
        with progress_container:
            if 'running_steps' in state: # Parallel execution
                _render_parallel_execution_progress(state, placeholders)
            else: # Linear execution
                _render_linear_execution_progress(state)

    user_wants_parallel = options.get('execution_mode') == 'parallel'
    is_parallel_capable = bool(workflow_def.get('source_yaml', {}).get('nodes'))

    if user_wants_parallel and is_parallel_capable:
        st.info("並列モードで実行します。")
        result = await engine.execute_workflow_parallel(workflow_def, inputs, progress_callback)
    else:
        if user_wants_parallel and not is_parallel_capable:
            st.warning("このワークフローは並列実行に対応していません (YAMLに`nodes`定義なし)。逐次モードで実行します。")
        else:
            st.info("逐次モードで実行します。")
        result = await engine.execute_workflow(workflow_def, inputs, progress_callback)

    st.markdown("---"); st.markdown("### 🎯 ワークフロー完了"); _render_workflow_result(result, options.get('debug_mode', False))


def _render_prompt_section_form(mode):
    # (この関数に変更はありません)
    if mode == "テンプレート + データ入力":
        c1, c2 = st.columns(2); template = c1.text_area("プロンプトテンプレート", st.session_state.prompt_template, height=200); user_input = c2.text_area("入力データ", st.session_state.user_input_data, height=200, help="`{user_input}`に代入されます。"); return template, user_input, ""
    single_prompt = st.text_area("単一プロンプト", st.session_state.single_prompt, height=200); return "", "", single_prompt

def _render_evaluation_section_form(): return st.text_area("評価基準", st.session_state.evaluation_criteria, height=120)

def _display_latest_results():
    # (この関数に変更はありません)
    res = st.session_state.latest_execution_result; exec_res, eval_res = res['execution_result'], res['evaluation_result']
    c1, c2 = st.columns([2, 1])
    with c1: render_response_box(exec_res.get('response_text'), "🤖 LLMの回答"); render_evaluation_box(eval_res.get('response_text'), "⭐ 評価結果")
    with c2:
        st.metric("モデル名", exec_res.get('model_name', 'N/A')); st.metric("総コスト", f"${exec_res.get('cost_usd', 0) + eval_res.get('cost_usd', 0):.6f}")
        with st.expander("コスト詳細"): st.text(f"実行: ${exec_res.get('cost_usd', 0):.6f} ({exec_res.get('total_tokens', 0):,} トークン)"); st.text(f"評価: ${eval_res.get('cost_usd', 0):.6f} ({eval_res.get('total_tokens', 0):,} トークン)")

def _render_workflow_info_panel(wf_def):
    # (この関数に変更はありません)
    step_count = len(wf_def.get('source_yaml', {}).get('nodes', {})) or len(wf_def.get('steps', []))
    c1, c2, c3 = st.columns(3); c1.metric("ステップ数", step_count); c2.metric("必要変数数", len(wf_def.get('global_variables', []))); c3.metric("作成日", wf_def.get('created_at', '不明')[:10])
    if wf_def.get('description'): st.caption(f"説明: {wf_def['description']}")

def _render_workflow_input_section(wf_def):
    # (この関数に変更はありません)
    inputs = {};
    if wf_def.get('global_variables'):
        st.markdown("#### グローバル入力変数");
        for var in wf_def['global_variables']: inputs[var] = st.text_area(f"**{var}**", key=f"wf_input_{wf_def['id']}_{var}")
    return inputs

def _render_execution_options():
    # (この関数に変更はありません)
    st.markdown("#### 実行オプション")
    c1, c2 = st.columns(2)
    with c1:
        execution_mode = st.radio(
            "実行方法",
            options=["並列実行 (推奨)", "逐次実行 (デバッグ用)"],
            horizontal=True,
            key="workflow_execution_mode_radio",
            help="並列実行は依存関係のないステップを同時に処理し高速です。逐次実行はデバッグに役立ちます。"
        )
    with c2:
        debug_mode = st.checkbox("デバッグモード", st.session_state.get('show_workflow_debug', False), key="workflow_debug_mode_check")
    
    return {
        'execution_mode': 'parallel' if '並列' in execution_mode else 'sequential',
        'debug_mode': debug_mode,
    }

def _render_variable_editor():
    # (この関数に変更はありません)
    vars_list = list(st.session_state.temp_variables)
    for i in range(len(vars_list)):
        c1, c2 = st.columns([3, 1]); new_var = c1.text_input(f"変数 {i+1}", vars_list[i], key=f"var_edit_{i}")
        if new_var.isidentifier(): vars_list[i] = new_var
        if c2.button("➖", key=f"rem_var_{i}") and len(vars_list) > 1: vars_list.pop(i); st.session_state.temp_variables = vars_list; st.rerun()
    if st.button("➕ 変数を追加"): vars_list.append(f"input_{len(vars_list)+1}"); st.session_state.temp_variables = vars_list; st.rerun()
    st.session_state.temp_variables = vars_list; return vars_list

def _render_steps_editor(g_vars):
    # 👈 [修正] この関数がメインの変更点
    steps = list(st.session_state.temp_steps)
    step_names = [step.get('name', f'step_{i+1}') for i, step in enumerate(steps)]

    for i in range(len(steps)):
        with st.container(border=True):
            st.markdown(f"###### ステップ {i+1}"); 
            c1, c2 = st.columns([3, 1]); 
            
            # ステップ名の入力と一意性の確保
            current_name = steps[i].get('name', f'step_{i+1}')
            name = c1.text_input("ステップ名", current_name, key=f"step_name_{i}")
            if name != current_name:
                if name.isidentifier() and name not in step_names:
                    steps[i]['name'] = name
                    st.rerun()
                else:
                    c1.warning("ステップ名は英数字とアンダースコアのみ使用でき、一意である必要があります。")
            
            if c2.button("🗑️ ステップ削除", key=f"rem_step_{i}") and len(steps) > 1: 
                steps.pop(i)
                st.session_state.temp_steps = steps
                st.rerun()

            # 依存関係設定のUI
            # このステップより前にある要素（グローバル変数と先行ステップ）を選択肢とする
            available_deps = g_vars + [s.get('name') for j, s in enumerate(steps) if j < i]
            
            dependencies = st.multiselect(
                "実行条件 (依存先)",
                options=available_deps,
                default=steps[i].get('dependencies', []),
                key=f"step_deps_{i}",
                help="このステップを実行する前に完了している必要がある項目を選択します。何も選択しない場合、他のステップと並列に実行されます。"
            )
            steps[i]['dependencies'] = dependencies
            
            # 利用可能な変数のヘルプ表示
            # 依存関係とグローバル変数がプロンプトで使える
            available_vars_for_prompt = dependencies + g_vars
            _render_variable_help(list(set(available_vars_for_prompt)))
            
            template = st.text_area("プロンプトテンプレート", steps[i].get('prompt_template', ''), key=f"step_tmpl_{i}", height=150)
            steps[i]['prompt_template'] = template

    if st.button("➕ ステップを追加"): 
        new_step_name = f'step_{len(steps)+1}'
        steps.append({'name': new_step_name, 'prompt_template': '', 'dependencies': []})
        st.session_state.temp_steps = steps
        st.rerun()

    st.session_state.temp_steps = steps
    return steps


def _render_variable_help(vars):
    # (この関数に変更はありません)
    if vars:
        # 変数名をノード名（ステップ名）として整形
        formatted_vars = [f"{{{v}}}" for v in vars]
        st.info(f"**利用可能な変数:** `{'`, `'.join(formatted_vars)}`")

# (以降の関数には変更はありません)

def _render_linear_execution_progress(state: Dict[str, Any]):
    total = state.get('total_steps', 0)
    current = state.get('current_step', 0)
    progress = current / total if total > 0 else 0
    msg = f"ステータス: {state.get('status', ExecutionStatus.PENDING).value}"
    if state.get('status') == ExecutionStatus.RUNNING:
        msg += f" | 実行中: {state.get('step_name', '')} ({current}/{total})"
    st.progress(progress, text=msg)

def _render_parallel_execution_progress(state: Dict[str, Any], placeholders: Dict[str, st.empty]):
    total = state.get('total_steps', 0)
    completed = state.get('completed_steps', 0)
    running_nodes = state.get('running_steps', set())
    
    if "overall_progress" not in placeholders:
        placeholders["overall_progress"] = st.empty()
    
    progress_val = completed / total if total > 0 else 0
    placeholders["overall_progress"].progress(progress_val, text=f"全体進捗: {completed}/{total} 完了済 | {len(running_nodes)} 実行中")

    active_placeholders = {"overall_progress"}
    for node_id in running_nodes:
        if node_id not in placeholders:
            placeholders[node_id] = st.empty()
        placeholders[node_id].info(f"🔄 実行中: {node_id}")
        active_placeholders.add(node_id)
    
    for node_id in list(placeholders.keys()):
        if node_id not in active_placeholders:
            placeholders[node_id].empty()
            del placeholders[node_id]


def _render_workflow_result(result, debug_mode):
    render_workflow_result_tabs(result, debug_mode)
    if not result.success:
        handler = WorkflowErrorHandler()
        err_type, desc, sugg = handler.categorize_error(str(result.error))
        render_error_details(err_type, desc, sugg)

# ui/tabs/execution_tab.py 内

# ... (他のコードはそのまま)

def _validate_inputs(memo, mode, criteria, template, user_input, single_prompt):
    errors = []
    if not memo.strip(): errors.append("❌ 実行メモは必須です。")
    if mode == "テンプレート + データ入力" and not template.strip(): errors.append("❌ プロンプトテンプレートは必須です。")
    if mode == "単発実行" and not single_prompt.strip(): errors.append("❌ プロンプトは必須です。")
    if not criteria.strip(): errors.append("❌ 評価基準は必須です。")
    return errors

# 👈 [修正] この関数名を変更し、古い関数は削除
def _validate_and_save_workflow_from_builder(name, desc, steps, g_vars):
    if not name.strip(): st.error("❌ ワークフロー名は必須です。"); return False
    if not steps: st.error("❌ 少なくとも1つのステップが必要です。"); return False
    
    # UIから得られた情報を内部定義に変換
    wf_def = WorkflowManager.parse_builder_to_internal(name, desc, steps, g_vars)
    
    errors = WorkflowManager.validate_workflow(wf_def)
    if errors:
        for err in errors: st.error(f"❌ バリデーションエラー: {err}"); 
        return False
        
    if WorkflowManager.save_workflow(wf_def): 
        st.success(f"✅ ワークフロー「{name}」を保存しました。"); 
        return True
        
    return False

# _validate_and_save_workflow 関数はもう不要なので削除しました。

# 👈 [新規] UIビルダーからの保存処理
