# ============================================
# ui/tabs/execution_tab.py (大幅拡張)
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
from typing import Dict, List, Any, Optional
from config.models import get_model_config
from core import GeminiEvaluator, GitManager, WorkflowEngine, WorkflowManager
from ui.components import render_response_box, render_evaluation_box

# セッション状態の初期化
def _initialize_session_state():
    """execution_tabで使われるセッション状態のキーを初期化"""
    defaults = {
        'execution_memo': "",
        'execution_mode': "テンプレート + データ入力",  # 既存の単発処理用
        'prompt_template': "以下のテキストを要約してください：\n\n{user_input}",
        'user_input_data': "",
        'single_prompt': "",
        'evaluation_criteria': """1. 正確性（30点）
2. 網羅性（25点）
3. 分かりやすさ（25点）
4. 論理性（20点）""",
        'latest_execution_result': None,
        # 🆕 ワークフロー用の新規セッション状態
        'user_workflows': {},
        'current_workflow_execution': None,
        'workflow_execution_progress': {},
        'show_workflow_debug': False
    }
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def render_execution_tab():
    """実行タブメイン（単発処理 + ワークフロー処理）"""
    _initialize_session_state()
    
    # ヘッダー
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.markdown("### 🚀 プロンプト実行")
    with header_col2:
        current_branch = GitManager.get_current_branch()
        st.markdown(f"**ブランチ:** `{current_branch}`")
    
    # 🆕 実行モード選択（分かりやすいUI）
    st.markdown("#### 実行モードを選択")
    mode_col1, mode_col2 = st.columns(2)
    
    with mode_col1:
        if st.button("📝 単発処理", use_container_width=True, 
                    help="1つのプロンプトを実行して結果を取得"):
            st.session_state.processing_mode = "single"
    
    with mode_col2:
        if st.button("🔄 ワークフロー処理", use_container_width=True,
                    help="複数のステップを連鎖実行して最終結果を取得"):
            st.session_state.processing_mode = "workflow"
    
    # デフォルト設定
    if 'processing_mode' not in st.session_state:
        st.session_state.processing_mode = "single"
    
    st.markdown("---")
    
    # 選択されたモードに応じて表示
    if st.session_state.processing_mode == "single":
        _render_single_execution()
    else:
        _render_workflow_execution()

def _render_single_execution():
    """既存の単発実行機能（既存コードを維持）"""
    st.markdown("### 📝 単発プロンプト実行")
    
    # 👇 既存のコードをそのまま使用（execution_tab.pyから）
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

        prompt_template, user_input_data, single_prompt = _render_prompt_section_form(execution_mode_full)
        evaluation_criteria = _render_evaluation_section_form()
        submitted = st.form_submit_button("🚀 実行 & 自動評価", type="primary", use_container_width=True)

    if submitted:
        st.session_state.execution_memo = execution_memo
        st.session_state.execution_mode = execution_mode_full
        st.session_state.prompt_template = prompt_template
        st.session_state.user_input_data = user_input_data
        st.session_state.single_prompt = single_prompt
        st.session_state.evaluation_criteria = evaluation_criteria

        # プレースホルダーをここで作成し、関数に渡す
        placeholder_intermediate_resp = st.empty()
        placeholder_intermediate_metrics = st.empty()
        placeholder_final_eval_info = st.empty()

        _execute_prompt_and_evaluation_sequentially(
            execution_memo, execution_mode_full,
            prompt_template, user_input_data, single_prompt, evaluation_criteria,
            placeholder_intermediate_resp, placeholder_intermediate_metrics, placeholder_final_eval_info
        )

    if st.session_state.latest_execution_result:
        st.markdown("---")
        st.subheader("✅ 実行・評価完了結果")
        _display_latest_results()

def _render_workflow_execution():
    """🆕 ワークフロー実行UI（高度な機能を実装）"""
    st.markdown("### 🔄 多段階ワークフロー実行")
    st.caption("複数のLLM処理ステップを順次実行し、前のステップの結果を次のステップで活用できます")
    
    # タブによる機能分離
    workflow_tab1, workflow_tab2, workflow_tab3 = st.tabs([
        "💾 保存済みワークフロー", 
        "🆕 新規ワークフロー作成",
        "🔧 高度な設定"
    ])
    
    with workflow_tab1:
        _render_saved_workflow_execution()
    
    with workflow_tab2:
        _render_workflow_builder()
    
    with workflow_tab3:
        _render_advanced_workflow_settings()

def _render_saved_workflow_execution():
    """保存済みワークフロー実行（最適化された UI）"""
    saved_workflows = WorkflowManager.get_saved_workflows()
    
    if not saved_workflows:
        st.info("💡 保存済みワークフローがありません。「新規ワークフロー作成」タブで作成してください。")
        
        # 🆕 サンプルワークフローの提案
        with st.expander("📝 ワークフロー作成のヒント"):
            st.markdown("""
            **よく使われるワークフローパターン:**
            
            📄 **文書分析フロー**
            1. 文書構造分析 → 2. 重要ポイント抽出 → 3. 要約・レポート生成
            
            🔍 **調査研究フロー**  
            1. 情報収集・整理 → 2. 比較分析 → 3. 考察・提案
            
            💼 **ビジネス分析フロー**
            1. 現状分析 → 2. 課題特定 → 3. 解決策提案
            
            各ステップで前のステップの結果を `{step_1_output}`, `{step_2_output}` として参照できます。
            """)
        return
    
    # ワークフロー選択UI
    workflow_col1, workflow_col2 = st.columns([3, 1])
    
    with workflow_col1:
        workflow_options = {}
        for wid, wdef in saved_workflows.items():
            created_date = wdef.get('created_at', '')[:10] if wdef.get('created_at') else ''
            step_count = len(wdef.get('steps', []))
            display_name = f"{wdef['name']} ({step_count}ステップ, {created_date})"
            workflow_options[wid] = display_name
        
        selected_id = st.selectbox(
            "ワークフロー選択",
            options=list(workflow_options.keys()),
            format_func=lambda x: workflow_options[x],
            help="実行したいワークフローを選択してください"
        )
    
    with workflow_col2:
        if selected_id:
            if st.button("🗑️ 削除", help="選択したワークフローを削除"):
                if WorkflowManager.delete_workflow(selected_id):
                    st.success("✅ ワークフローを削除しました")
                    st.rerun()
            
            if st.button("📋 複製", help="選択したワークフローを複製"):
                original_name = WorkflowManager.get_workflow(selected_id)['name']
                new_name = f"{original_name} (コピー)"
                new_id = WorkflowManager.duplicate_workflow(selected_id, new_name)
                if new_id:
                    st.success(f"✅ ワークフロー「{new_name}」を作成しました")
                    st.rerun()
    
    if selected_id:
        workflow_def = WorkflowManager.get_workflow(selected_id)
        
        # 🆕 ワークフロー詳細情報表示
        _render_workflow_info_panel(workflow_def)
        
        # 🆕 入力変数設定（改善されたUI）
        input_values = _render_workflow_input_section(workflow_def)
        
        # 🆕 実行オプション
        execution_options = _render_execution_options()
        
        # 実行ボタン
        if st.button("🚀 ワークフロー実行", type="primary", use_container_width=True):
            _execute_workflow_with_progress(workflow_def, input_values, execution_options)

def _render_workflow_info_panel(workflow_def: Dict):
    """ワークフロー情報パネル（分かりやすい表示）"""
    st.markdown("#### 📊 ワークフロー詳細情報")
    
    info_col1, info_col2, info_col3 = st.columns(3)
    
    info_col1.metric("ステップ数", len(workflow_def['steps']))
    info_col2.metric("必要変数数", len(workflow_def.get('global_variables', [])))
    
    created_date = workflow_def.get('created_at', 'Unknown')[:10]
    info_col3.metric("作成日", created_date)
    
    if workflow_def.get('description'):
        st.markdown(f"**説明:** {workflow_def['description']}")
    
    # ワークフロー構造の表示（常に表示）
    st.markdown("**ワークフロー構造:**")
    for i, step in enumerate(workflow_def['steps']):
        step_preview = step['prompt_template'][:100] + "..." if len(step['prompt_template']) > 100 else step['prompt_template']
        
        st.markdown(f"""
        **Step {i+1}: {step['name']}**
        ```
        {step_preview}
        ```
        """)
        
        if i < len(workflow_def['steps']) - 1:
            st.markdown("⬇️")
    
    st.markdown("---")

def _render_workflow_input_section(workflow_def: Dict) -> Dict[str, str]:
    """🆕 改善された入力変数設定UI"""
    input_values = {}
    
    if workflow_def.get('global_variables'):
        st.markdown("### 📥 入力データ設定")
        
        for var_name in workflow_def['global_variables']:
            # 🆕 変数名の説明を自動生成
            var_description = _generate_variable_description(var_name)
            
            input_values[var_name] = st.text_area(
                f"**{var_name}**",
                help=f"{var_description}",
                placeholder=f"{var_name}の内容を入力してください...",
                key=f"workflow_input_{var_name}",
                height=120
            )
            
            # 🆕 文字数カウンター
            if input_values[var_name]:
                char_count = len(input_values[var_name])
                st.caption(f"📝 {char_count:,} 文字")
    
    return input_values

def _generate_variable_description(var_name: str) -> str:
    """変数名から説明を自動生成"""
    descriptions = {
        'document': '分析対象の文書やテキスト',
        'data': '処理するデータ',
        'input': '入力情報',
        'text': 'テキスト内容',
        'content': 'コンテンツ',
        'source': 'ソース情報',
        'requirement': '要件や条件',
        'context': '背景情報や文脈'
    }
    
    for key, desc in descriptions.items():
        if key in var_name.lower():
            return f"ワークフローで使用される{desc}"
    
    return f"ワークフローで使用される変数 '{var_name}' の値"

def _render_execution_options() -> Dict[str, Any]:
    """🆕 実行オプション設定"""
    with st.expander("⚙️ 実行オプション", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            show_progress = st.checkbox("進捗表示", value=True, help="実行中の詳細な進捗を表示")
            cache_results = st.checkbox("結果キャッシュ", value=True, help="同じプロンプトの結果を再利用")
        
        with col2:
            auto_retry = st.checkbox("自動リトライ", value=True, help="エラー時の自動再試行")
            debug_mode = st.checkbox("デバッグモード", value=False, help="詳細なデバッグ情報を表示")
        
        return {
            'show_progress': show_progress,
            'cache_results': cache_results,
            'auto_retry': auto_retry,
            'debug_mode': debug_mode
        }

def _render_workflow_builder():
    """🆕 改善されたワークフロービルダー（直感的なUI）"""
    st.markdown("### 🆕 新規ワークフロー作成")
    
    # ステップ1: 基本設定
    with st.expander("📝 Step 1: 基本情報", expanded=True):
        basic_col1, basic_col2 = st.columns(2)
        
        with basic_col1:
            workflow_name = st.text_input(
                "ワークフロー名", 
                placeholder="例: 文書分析ワークフロー",
                help="わかりやすい名前をつけてください"
            )
        
        with basic_col2:
            description = st.text_input(
                "説明（任意）", 
                placeholder="例: 文書を分析し要約とレポートを生成",
                help="このワークフローの目的や内容"
            )
    
    # ステップ2: 入力変数設定
    with st.expander("📥 Step 2: 入力変数設定", expanded=True):
        st.markdown("このワークフローで使用する入力変数を定義してください")
        
        # 🆕 動的な変数追加UI
        if 'temp_variables' not in st.session_state:
            st.session_state.temp_variables = ['input_1']
        
        global_variables = []
        input_values = {}
        
        for i, var_name in enumerate(st.session_state.temp_variables):
            var_col1, var_col2, var_col3 = st.columns([2, 3, 1])
            
            with var_col1:
                new_var_name = st.text_input(
                    f"変数名 {i+1}",
                    value=var_name,
                    key=f"var_name_{i}",
                    help="英数字とアンダースコアのみ使用可能"
                )
                if new_var_name and new_var_name not in global_variables:
                    global_variables.append(new_var_name)
                    st.session_state.temp_variables[i] = new_var_name
            
            with var_col2:
                if new_var_name:
                    input_values[new_var_name] = st.text_area(
                        f"テスト用データ",
                        key=f"var_test_{i}",
                        height=80,
                        help="ワークフローのテスト実行用"
                    )
            
            with var_col3:
                if len(st.session_state.temp_variables) > 1:
                    if st.button("❌", key=f"remove_var_{i}", help="この変数を削除"):
                        st.session_state.temp_variables.pop(i)
                        st.rerun()
        
        if st.button("➕ 変数を追加"):
            st.session_state.temp_variables.append(f"input_{len(st.session_state.temp_variables) + 1}")
            st.rerun()
    
    # ステップ3: ワークフローステップ設定
    with st.expander("🔧 Step 3: ワークフローステップ設定", expanded=True):
        # 🆕 動的なステップ追加UI
        if 'temp_steps' not in st.session_state:
            st.session_state.temp_steps = [{}]
        
        steps = []
        
        for i, step_data in enumerate(st.session_state.temp_steps):
            st.markdown(f"#### 📋 ステップ {i+1}")
            
            step_col1, step_col2 = st.columns([3, 1])
            
            with step_col1:
                step_name = st.text_input(
                    "ステップ名",
                    value=step_data.get('name', f"Step {i+1}"),
                    key=f"step_name_{i}",
                    help="このステップで何を行うかの説明"
                )
            
            with step_col2:
                if len(st.session_state.temp_steps) > 1:
                    if st.button("🗑️ 削除", key=f"remove_step_{i}"):
                        st.session_state.temp_steps.pop(i)
                        st.rerun()
            
            # 利用可能変数の表示
            available_vars = global_variables.copy()
            if i > 0:
                available_vars.extend([f"step_{j+1}_output" for j in range(i)])
            
            # 🆕 変数ヘルプの表示
            _render_variable_help(available_vars)
            
            # 🆕 プロンプトテンプレート（リアルタイムプレビュー付き）
            prompt_template = st.text_area(
                "プロンプトテンプレート",
                value=step_data.get('template', _get_default_prompt_template(i, available_vars)),
                key=f"step_prompt_{i}",
                height=150,
                help="このステップで実行するプロンプト。{変数名}で他の変数を参照できます"
            )
            
            # 🆕 リアルタイムプレビュー
            if st.checkbox(f"プレビュー表示", key=f"preview_{i}"):
                _render_prompt_preview(prompt_template, input_values, i)
            
            steps.append({
                'name': step_name,
                'prompt_template': prompt_template,
                'input_variables': available_vars
            })
            
            # 更新
            st.session_state.temp_steps[i] = {
                'name': step_name,
                'template': prompt_template
            }
            
            if i < len(st.session_state.temp_steps) - 1:
                st.markdown("⬇️")
        
        if st.button("➕ ステップを追加"):
            st.session_state.temp_steps.append({})
            st.rerun()
    
    # ステップ4: アクション
    st.markdown("### 🎯 アクション")
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("💾 保存", use_container_width=True):
            if _validate_and_save_workflow(workflow_name, description, steps, global_variables):
                st.session_state.temp_variables = ['input_1']
                st.session_state.temp_steps = [{}]
                st.rerun()
    
    with action_col2:
        if st.button("🧪 テスト実行", use_container_width=True):
            if workflow_name and steps:
                workflow_def = {
                    'name': workflow_name,
                    'description': description,
                    'steps': steps,
                    'global_variables': global_variables
                }
                _execute_workflow_with_progress(workflow_def, input_values, {'debug_mode': True})
    
    with action_col3:
        if st.button("🔄 リセット", use_container_width=True):
            st.session_state.temp_variables = ['input_1']
            st.session_state.temp_steps = [{}]
            st.rerun()

def _render_variable_help(available_vars: List[str]):
    """🆕 利用可能変数のヘルプ表示"""
    if available_vars:
        st.markdown("**💡 利用可能な変数:**")
        cols = st.columns(2)
        
        input_vars = [var for var in available_vars if not var.startswith('step_')]
        step_vars = [var for var in available_vars if var.startswith('step_')]
        
        with cols[0]:
            if input_vars:
                st.markdown("*入力変数:*")
                for var in input_vars:
                    st.code(f"{{{var}}}")
        
        with cols[1]:
            if step_vars:
                st.markdown("*前のステップ結果:*")
                for var in step_vars:
                    st.code(f"{{{var}}}")

def _render_prompt_preview(template: str, input_values: Dict[str, str], step_index: int):
    """🆕 プロンプトのリアルタイムプレビュー"""
    from core.workflow_engine import VariableProcessor
    
    processor = VariableProcessor()
    
    # テストコンテキストを作成
    context = input_values.copy()
    for i in range(step_index):
        context[f'step_{i+1}_output'] = f"[Step {i+1} の実行結果がここに表示されます]"
    
    try:
        preview = processor.substitute_variables(template, context)
        st.markdown("**プレビュー:**")
        preview_text = preview[:300] + "..." if len(preview) > 300 else preview
        st.text_area("", value=preview_text, height=120, key=f"preview_text_{step_index}", disabled=True)
    except Exception as e:
        st.warning(f"プレビューエラー: {str(e)}")

def _render_advanced_workflow_settings():
    """🆕 高度なワークフロー設定"""
    st.markdown("### 🔧 高度な設定")
    
    # キャッシュ管理
    st.markdown("#### 💾 キャッシュ管理")
    st.caption("実行結果のキャッシュを管理できます")
    
    cache_col1, cache_col2 = st.columns(2)
    
    with cache_col1:
        if st.button("🗑️ キャッシュクリア", use_container_width=True):
            # WorkflowEngineのキャッシュクリア
            if not st.session_state.api_key:
                st.warning("APIキーが設定されていません")
            else:
                from config.models import get_model_config
                model_config = get_model_config(st.session_state.selected_model)
                evaluator = GeminiEvaluator(st.session_state.api_key, model_config)
                engine = WorkflowEngine(evaluator)
                engine.clear_cache()
                st.success("✅ キャッシュをクリアしました")
    
    with cache_col2:
        st.info("キャッシュ統計: 実装予定")
    
    st.markdown("---")
    
    # デバッグツール
    st.markdown("#### 🐛 デバッグツール")
    st.caption("ワークフロー開発とトラブルシューティング用のツール")
    
    debug_col1, debug_col2 = st.columns(2)
    
    with debug_col1:
        st.checkbox("詳細ログ出力", key="debug_verbose_logging")
        st.checkbox("変数置換の表示", key="debug_show_substitution")
    
    with debug_col2:
        st.checkbox("実行時間の測定", key="debug_measure_time")
        st.checkbox("メモリ使用量の監視", key="debug_monitor_memory")
    
    st.markdown("---")
    
    # エクスポート・インポート
    st.markdown("#### 📤 エクスポート・インポート")
    
    export_col1, export_col2 = st.columns(2)
    
    with export_col1:
        st.markdown("**エクスポート**")
        workflows = WorkflowManager.get_saved_workflows()
        if workflows:
            selected_export = st.selectbox(
                "エクスポートするワークフロー",
                options=list(workflows.keys()),
                format_func=lambda x: workflows[x]['name']
            )
            
            if st.button("📥 JSONでダウンロード"):
                json_data = WorkflowManager.export_workflow(selected_export)
                if json_data:
                    st.download_button(
                        "💾 ダウンロード",
                        json_data,
                        f"{workflows[selected_export]['name']}.json",
                        "application/json"
                    )
    
    with export_col2:
        st.markdown("**インポート**")
        uploaded_file = st.file_uploader("JSONファイルを選択", type=["json"])
        
        if uploaded_file and st.button("📤 インポート"):
            try:
                json_data = uploaded_file.read().decode('utf-8')
                result = WorkflowManager.import_workflow(json_data)
                
                if result['success']:
                    st.success(f"✅ ワークフロー「{result['workflow_name']}」をインポートしました")
                    st.rerun()
                else:
                    for error in result['errors']:
                        st.error(f"❌ {error}")
            except Exception as e:
                st.error(f"❌ インポートエラー: {str(e)}")

def _execute_workflow_with_progress(workflow_def: Dict, input_values: Dict, options: Dict):
    """🆕 進捗表示付きワークフロー実行"""
    from core.workflow_engine import WorkflowEngine
    from config.models import get_model_config
    
    # 入力検証
    if not st.session_state.api_key:
        st.error("❌ APIキーが設定されていません")
        return
    
    for var_name in workflow_def.get('global_variables', []):
        if not input_values.get(var_name, '').strip():
            st.error(f"❌ 変数 '{var_name}' を入力してください")
            return
    
    # エンジン初期化
    model_config = get_model_config(st.session_state.selected_model)
    evaluator = GeminiEvaluator(st.session_state.api_key, model_config)
    engine = WorkflowEngine(evaluator)
    
    # 🆕 進捗表示コンテナ
    progress_container = st.container()
    result_container = st.container()
    
    # 進捗コールバック関数
    def progress_callback(state):
        with progress_container:
            _render_execution_progress(state, workflow_def)
    
    try:
        with st.spinner("🔄 ワークフロー実行中..."):
            result = engine.execute_workflow(
                workflow_def, 
                input_values,
                progress_callback if options.get('show_progress', True) else None
            )
        
        # 結果表示
        with result_container:
            _render_workflow_result(result, options.get('debug_mode', False))
            
    except Exception as e:
        st.error(f"❌ 実行エラー: {str(e)}")

def _render_execution_progress(state: Dict, workflow_def: Dict):
    """🆕 実行進捗の表示"""
    if state.get('status') == 'running':
        # プログレスバー
        current_step = state.get('current_step', 0)
        total_steps = len(workflow_def['steps'])
        progress = current_step / total_steps if total_steps > 0 else 0
        
        st.progress(progress)
        
        # ステップ状況
        step_col1, step_col2 = st.columns([2, 1])
        
        with step_col1:
            if current_step > 0:
                current_step_name = state.get('step_name', f'Step {current_step}')
                st.markdown(f"**実行中:** {current_step_name}")
        
        with step_col2:
            st.markdown(f"**{current_step}/{total_steps}** ステップ")
        
        # 各ステップの状態表示
        for i, step in enumerate(workflow_def['steps']):
            if i + 1 < current_step:
                st.success(f"✅ Step {i+1}: {step['name']}")
            elif i + 1 == current_step:
                st.info(f"🔄 Step {i+1}: {step['name']} (実行中)")
            else:
                st.markdown(f"⏸️ Step {i+1}: {step['name']} (待機中)")

def _render_workflow_result(result, debug_mode: bool = False):
    """🆕 改善されたワークフロー結果表示"""
    if result.success:
        st.success(f"✅ ワークフロー完了: {result.workflow_name}")
        
        # サマリーメトリクス
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        metric_col1.metric("実行時間", f"{result.duration_seconds:.1f}秒")
        metric_col2.metric("ステップ数", len(result.steps))
        metric_col3.metric("総コスト", f"${result.total_cost:.4f}")
        metric_col4.metric("総トークン", f"{result.total_tokens:,}")
        
        # 🆕 タブによる結果表示
        result_tab1, result_tab2, result_tab3 = st.tabs([
            "🎯 最終結果", 
            "📋 ステップ詳細", 
            "🐛 デバッグ情報" if debug_mode else "📊 統計情報"
        ])
        
        with result_tab1:
            st.markdown("### 🎯 最終出力")
            st.text_area("", value=result.final_output, height=400, key="final_result_display")
            
            # コピーボタン
            if st.button("📋 結果をコピー"):
                st.code(result.final_output)
        
        with result_tab2:
            st.markdown("### 📋 各ステップの詳細結果")
            for step_result in result.steps:
                with st.expander(f"Step {step_result.step_number}: {step_result.step_name}"):
                    detail_col1, detail_col2 = st.columns([3, 1])
                    
                    with detail_col1:
                        st.markdown("**出力:**")
                        st.text_area("", value=step_result.response, height=200, 
                                   key=f"step_detail_{step_result.step_number}")
                    
                    with detail_col2:
                        st.metric("実行時間", f"{step_result.execution_time:.1f}秒")
                        st.metric("トークン", step_result.tokens)
                        st.metric("コスト", f"${step_result.cost:.4f}")
                        
                        if debug_mode and st.button("🔍 プロンプト確認", key=f"show_prompt_{step_result.step_number}"):
                            st.code(step_result.prompt)
        
        with result_tab3:
            if debug_mode:
                st.markdown("### 🐛 デバッグ情報")
                st.json({
                    'execution_id': result.execution_id,
                    'status': result.status.value,
                    'metadata': result.metadata or {}
                })
            else:
                st.markdown("### 📊 実行統計")
                # ステップ別コスト分析
                if result.steps:
                    import pandas as pd
                    
                    step_data = []
                    for step in result.steps:
                        step_data.append({
                            'ステップ': f"Step {step.step_number}",
                            '名前': step.step_name,
                            'コスト': step.cost,
                            'トークン': step.tokens,
                            '実行時間': step.execution_time
                        })
                    
                    df = pd.DataFrame(step_data)
                    st.dataframe(df, use_container_width=True)
    
    else:
        # 🆕 エラー詳細表示
        _render_workflow_error(result)

def _render_workflow_error(result):
    """🆕 詳細なエラー表示とリカバリー提案"""
    from core.workflow_engine import WorkflowErrorHandler
    
    st.error(f"❌ ワークフロー実行エラー: {result.workflow_name}")
    
    # エラー分析
    error_handler = WorkflowErrorHandler()
    error_type, description, suggestions = error_handler.categorize_error(result.error or "Unknown error")
    
    error_col1, error_col2 = st.columns([2, 1])
    
    with error_col1:
        st.markdown("### 🚨 エラー詳細")
        st.markdown(f"**エラータイプ:** {description}")
        st.markdown(f"**詳細メッセージ:** {result.error}")
        
        if result.steps:
            st.markdown("### 📋 完了済みステップ")
            for step_result in result.steps:
                st.success(f"✅ Step {step_result.step_number}: {step_result.step_name}")
    
    with error_col2:
        st.markdown("### 💡 対処法")
        for i, suggestion in enumerate(suggestions, 1):
            st.markdown(f"{i}. {suggestion}")
        
        # 🆕 リトライオプション
        if error_handler.should_retry(error_type, 1):
            if st.button("🔄 再実行", type="primary"):
                st.rerun()

# 🆕 以下は既存の単発実行用関数（既存コードを維持）
def _render_prompt_section_form(execution_mode):
    st.markdown("### 📝 プロンプト")
    if execution_mode == "テンプレート + データ入力":
        template_col1, template_col2 = st.columns(2)
        with template_col1:
            st.markdown("**テンプレート**")
            prompt_template = st.text_area(
                "", value=st.session_state.prompt_template, height=200,
                placeholder="{user_input}でデータを参照", key="template_area_form", label_visibility="collapsed"
            )
        with template_col2:
            st.markdown("**データ**")
            user_input_data = st.text_area(
                "", value=st.session_state.user_input_data, height=200,
                placeholder="処理したいデータを入力...", key="data_area_form", label_visibility="collapsed"
            )
        if prompt_template and user_input_data and "{user_input}" in prompt_template:
            if st.checkbox("🔍 最終プロンプトを確認", key="preview_form"):
                final_prompt_preview = prompt_template.replace("{user_input}", user_input_data)
                st.code(final_prompt_preview[:500] + "..." if len(final_prompt_preview) > 500 else final_prompt_preview)
        elif prompt_template and "{user_input}" not in prompt_template:
            st.warning("⚠️ テンプレートに{user_input}を含めてください")
        return prompt_template, user_input_data, st.session_state.single_prompt 
    else:  # 単一プロンプト
        st.markdown("**プロンプト**")
        single_prompt = st.text_area(
            "", value=st.session_state.single_prompt, height=200,
            placeholder="プロンプトを入力してください...", key="single_area_form", label_visibility="collapsed"
        )
        return st.session_state.prompt_template, st.session_state.user_input_data, single_prompt 

def _render_evaluation_section_form():
    st.markdown("### 📋 評価基準")
    evaluation_criteria = st.text_area(
        "", value=st.session_state.evaluation_criteria, height=120,
        key="criteria_area_form", label_visibility="collapsed"
    )
    return evaluation_criteria

def _execute_prompt_and_evaluation_sequentially(
    execution_memo, execution_mode, prompt_template_val, user_input_data_val, single_prompt_val, evaluation_criteria_val,
    placeholder_intermediate_resp, placeholder_intermediate_metrics, placeholder_final_eval_info):

    placeholder_intermediate_resp.empty()
    placeholder_intermediate_metrics.empty()
    placeholder_final_eval_info.empty()
    st.session_state.latest_execution_result = None

    validation_errors = _validate_inputs_direct(execution_memo, execution_mode, evaluation_criteria_val, prompt_template_val, user_input_data_val, single_prompt_val)
    if validation_errors:
        for error in validation_errors:
            st.error(error)
        return

    if not st.session_state.api_key:
        st.error("❌ APIキーが設定されていません")
        return

    model_config = get_model_config(st.session_state.selected_model)
    evaluator = GeminiEvaluator(st.session_state.api_key, model_config)

    final_prompt = ""
    current_prompt_template = None
    current_user_input = None
    if execution_mode == "テンプレート + データ入力":
        final_prompt = prompt_template_val.replace("{user_input}", user_input_data_val)
        current_prompt_template = prompt_template_val
        current_user_input = user_input_data_val
    else:
        final_prompt = single_prompt_val

    initial_execution_result = None
    with st.spinner(f"🔄 {model_config['name']}で一次実行中..."):
        initial_execution_result = evaluator.execute_prompt(final_prompt)

    if not initial_execution_result or not initial_execution_result['success']:
        st.error(f"❌ 一次実行エラー: {initial_execution_result.get('error', '不明なエラー')}")
        return

    with placeholder_intermediate_resp.container():
        st.markdown("---")
        st.subheader("📝 一次実行結果 (評価前)")
        exec_res_disp = initial_execution_result
        render_response_box(exec_res_disp['response_text'], f"🤖 LLMの回答 ({exec_res_disp.get('model_name', '')})")

    with placeholder_intermediate_metrics.container():
        st.markdown("##### 📊 一次実行メトリクス")
        cols_metrics = st.columns(3)
        cols_metrics[0].metric("実行入力トークン", f"{initial_execution_result.get('input_tokens', 0):,}")
        cols_metrics[1].metric("実行出力トークン", f"{initial_execution_result.get('output_tokens', 0):,}")
        cols_metrics[2].metric("実行コスト(USD)", f"${initial_execution_result.get('cost_usd', 0.0):.6f}")
        st.info("評価処理を自動的に開始します...")

    evaluation_result = None
    with st.spinner("📊 評価処理を実行中..."):
        evaluation_result = evaluator.evaluate_response(
            original_prompt=final_prompt,
            llm_response_text=initial_execution_result['response_text'],
            evaluation_criteria=evaluation_criteria_val
        )

    if not evaluation_result or not evaluation_result['success']:
        with placeholder_final_eval_info.container():
            st.error(f"❌ 評価処理エラー: {evaluation_result.get('error', '不明なエラー')}")
            st.warning("一次実行の結果は上記に表示されていますが、評価は失敗しました。記録は保存されません。")
        return

    placeholder_intermediate_resp.empty()
    placeholder_intermediate_metrics.empty()
    placeholder_final_eval_info.empty()

    execution_data_to_save = {
        'timestamp': datetime.datetime.now(),
        'execution_mode': execution_mode,
        'prompt_template': current_prompt_template,
        'user_input': current_user_input,
        'final_prompt': final_prompt,
        'criteria': evaluation_criteria_val,
        'response': initial_execution_result['response_text'],
        'evaluation': evaluation_result['response_text'],
        'execution_tokens': initial_execution_result['total_tokens'],
        'evaluation_tokens': evaluation_result['total_tokens'],
        'execution_cost': initial_execution_result['cost_usd'],
        'evaluation_cost': evaluation_result['cost_usd'],
        'total_cost': initial_execution_result['cost_usd'] + evaluation_result['cost_usd'],
        'model_name': initial_execution_result['model_name'],
        'model_id': initial_execution_result['model_id']
    }
    execution_record = GitManager.create_commit(execution_data_to_save, execution_memo)
    GitManager.add_commit_to_history(execution_record)

    st.session_state.latest_execution_result = {
        'execution_result': initial_execution_result,
        'evaluation_result': evaluation_result,
        'execution_record': execution_record
    }
    st.success(f"✅ 実行と評価が完了し、記録を保存しました。 | ID: `{execution_record['commit_hash']}`")
    st.rerun()

def _validate_inputs_direct(execution_memo, execution_mode, evaluation_criteria, prompt_template, user_input_data, single_prompt):
    errors = []
    if not execution_memo.strip():
        errors.append("❌ 実行メモを入力してください")
    if execution_mode == "テンプレート + データ入力":
        if not prompt_template.strip():
            errors.append("❌ プロンプトテンプレートを入力してください")
        elif "{user_input}" not in prompt_template:
            errors.append("❌ テンプレートに{user_input}を含めてください")
    else:
        if not single_prompt.strip():
            errors.append("❌ プロンプトを入力してください")
    if not evaluation_criteria.strip():
        errors.append("❌ 評価基準を入力してください")
    return errors

def _display_latest_results():
    if not st.session_state.latest_execution_result:
        return

    result_data = st.session_state.latest_execution_result
    initial_exec_res = result_data['execution_result']
    eval_res = result_data['evaluation_result'] 

    result_col1, result_col2 = st.columns([2, 1])
    with result_col1:
        render_response_box(initial_exec_res['response_text'], "🤖 LLMの回答")
        render_evaluation_box(eval_res['response_text'], "⭐ 評価結果")
    with result_col2:
        st.markdown("### 📊 実行・評価情報")
        st.metric("モデル名", initial_exec_res.get('model_name', 'N/A'))
        st.markdown("---")
        st.markdown("**実行結果**")
        cols_exec_final = st.columns(2)
        with cols_exec_final[0]:
            st.metric("入力トークン", f"{initial_exec_res.get('input_tokens', 0):,}")
            st.metric("総トークン", f"{initial_exec_res.get('total_tokens', 0):,}")
        with cols_exec_final[1]:
            st.metric("出力トークン", f"{initial_exec_res.get('output_tokens', 0):,}")
            st.metric("コスト(USD)", f"${initial_exec_res.get('cost_usd', 0.0):.6f}")
        st.markdown("---")
        st.markdown("**評価処理**")
        cols_eval_final = st.columns(2)
        with cols_eval_final[0]:
            st.metric("入力トークン", f"{eval_res.get('input_tokens', 0):,}")
            st.metric("総トークン", f"{eval_res.get('total_tokens', 0):,}")
        with cols_eval_final[1]:
            st.metric("出力トークン", f"{eval_res.get('output_tokens', 0):,}")
            st.metric("コスト(USD)", f"${eval_res.get('cost_usd', 0.0):.6f}")
        st.markdown("---")
        total_cost_combined = initial_exec_res.get('cost_usd', 0.0) + eval_res.get('cost_usd', 0.0)
        st.metric("合計コスト(USD)", f"${total_cost_combined:.6f}")

def _get_default_prompt_template(step_index: int, available_vars: List[str]) -> str:
    """デフォルトプロンプトテンプレートを生成"""
    if step_index == 0:
        if available_vars:
            return f"以下を分析してください：\n\n{{{available_vars[0]}}}\n\n詳細な分析結果を提供してください："
        else:
            return "分析を実行してください："
    else:
        prev_step_var = f"step_{step_index}_output"
        return f"前のステップの分析結果：\n\n{{{prev_step_var}}}\n\nさらなる考察を提供してください："

def _validate_and_save_workflow(name: str, description: str, steps: List[Dict], global_vars: List[str]) -> bool:
    """ワークフローを検証して保存"""
    
    # 基本検証
    if not name.strip():
        st.error("❌ ワークフロー名を入力してください")
        return False
    
    if not steps:
        st.error("❌ 少なくとも1つのステップが必要です")
        return False
    
    for i, step in enumerate(steps):
        if not step['name'].strip():
            st.error(f"❌ ステップ {i+1} の名前を入力してください")
            return False
        if not step['prompt_template'].strip():
            st.error(f"❌ ステップ {i+1} のプロンプトを入力してください")
            return False
    
    # 🆕 詳細検証
    validation_errors = WorkflowManager.validate_workflow({
        'name': name,
        'description': description,
        'steps': steps,
        'global_variables': global_vars
    })
    
    if validation_errors:
        for error in validation_errors:
            st.error(f"❌ {error}")
        return False
    
    # 保存
    workflow_def = {
        'name': name,
        'description': description,
        'steps': steps,
        'global_variables': global_vars
    }
    
    workflow_id = WorkflowManager.save_workflow(workflow_def)
    st.success(f"✅ ワークフロー「{name}」を保存しました（ID: {workflow_id}）")
    return True