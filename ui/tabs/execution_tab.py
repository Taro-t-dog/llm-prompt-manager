import sys
import os

print(f"DEBUG: __file__ = {os.path.abspath(__file__)}")

# ここを修正: 相対パスを '../../' に変更
calculated_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

print(f"DEBUG: Calculated path to add = {calculated_path}")

sys.path.append(calculated_path)

# デバッグ用: sys.path の内容を出力
print("DEBUG: Current sys.path:")
for p in sys.path:
    print(f"- {p}")
import streamlit as st
import datetime
from config.models import get_model_config
from core import GeminiEvaluator, GitManager # GitManagerとGeminiEvaluatorをインポート
from ui.components import render_response_box, render_evaluation_box # 必要に応じて他のUIコンポーネントもインポート

# セッション状態の初期化 (execution_tab 専用のものは render_execution_tab の中で呼び出す)
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
        'latest_execution_result': None # 実行＋評価の最終結果
    }
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def render_execution_tab():
    """改善された実行タブ（一次実行結果表示後、自動評価）"""
    _initialize_session_state() # 実行タブ固有のセッション状態を初期化

    # プレースホルダーは、それらを使用する関数のスコープ内で定義
    # もし _execute_prompt_and_evaluation_sequentially がこの関数の外にあるなら、引数で渡す
    # ここでは同じファイル内なので、 render_execution_tab スコープで定義し、内部関数に渡すか、
    # _execute_prompt_and_evaluation_sequentially が直接アクセスできるようにする。
    # 簡単のため、_execute_prompt_and_evaluation_sequentially の中で st.empty() を呼び出す形にする。

    exec_col1, exec_col2 = st.columns([3, 1])
    with exec_col1:
        st.markdown("### 新しいプロンプトを実行し自動評価")
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

    # プレースホルダーをフォームの外、かつstreamlitコマンドが初めて実行される前に定義
    # (st.set_page_configより後、実際の表示要素より前)
    # → _execute_prompt_and_evaluation_sequentially の中で呼び出すように変更

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
        placeholder_final_eval_info = st.empty() # 評価失敗時などの情報表示用

        _execute_prompt_and_evaluation_sequentially(
            execution_memo, execution_mode_full,
            prompt_template, user_input_data, single_prompt, evaluation_criteria,
            placeholder_intermediate_resp, placeholder_intermediate_metrics, placeholder_final_eval_info
        )

    if st.session_state.latest_execution_result:
        st.markdown("---")
        st.subheader("✅ 実行・評価完了結果")
        _display_latest_results()

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
        return prompt_template, user_input_data, st.session_state.single_prompt # single_promptも返す
    else:  # 単一プロンプト
        st.markdown("**プロンプト**")
        single_prompt = st.text_area(
            "", value=st.session_state.single_prompt, height=200,
            placeholder="プロンプトを入力してください...", key="single_area_form", label_visibility="collapsed"
        )
        return st.session_state.prompt_template, st.session_state.user_input_data, single_prompt # prompt_template等も返す

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
        # テンプレートモードでもデータが空の場合の扱い (エラーにするか許容するか)
        # if not user_input_data.strip():
        #     errors.append("❌ 処理データを入力してください")
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
    initial_exec_res = result_data['execution_result'] # 'response_text', 'cost_usd' etc.
    eval_res = result_data['evaluation_result']       # 'response_text', 'cost_usd' etc.
    # exec_record = result_data['execution_record'] # 'final_prompt'などを含む保存された記録

    result_col1, result_col2 = st.columns([2, 1])
    with result_col1:
        render_response_box(initial_exec_res['response_text'], "🤖 LLMの回答")
        render_evaluation_box(eval_res['response_text'], "⭐ 評価結果")
    with result_col2:
        st.markdown("### 📊 実行・評価情報")
        st.metric("モデル名", initial_exec_res.get('model_name', 'N/A'))
        st.markdown("---")
        st.markdown("**実行結果**")
        cols_exec_final = st.columns(2) # レイアウト調整例
        with cols_exec_final[0]:
            st.metric("入力トークン", f"{initial_exec_res.get('input_tokens', 0):,}")
            st.metric("総トークン", f"{initial_exec_res.get('total_tokens', 0):,}")
        with cols_exec_final[1]:
            st.metric("出力トークン", f"{initial_exec_res.get('output_tokens', 0):,}")
            st.metric("コスト(USD)", f"${initial_exec_res.get('cost_usd', 0.0):.6f}")
        st.markdown("---")
        st.markdown("**評価処理**")
        cols_eval_final = st.columns(2) # レイアウト調整例
        with cols_eval_final[0]:
            st.metric("入力トークン", f"{eval_res.get('input_tokens', 0):,}") # 評価処理の入力トークン
            st.metric("総トークン", f"{eval_res.get('total_tokens', 0):,}")
        with cols_eval_final[1]:
            st.metric("出力トークン", f"{eval_res.get('output_tokens', 0):,}") # 評価処理の出力トークン
            st.metric("コスト(USD)", f"${eval_res.get('cost_usd', 0.0):.6f}")
        st.markdown("---")
        total_cost_combined = initial_exec_res.get('cost_usd', 0.0) + eval_res.get('cost_usd', 0.0)
        st.metric("合計コスト(USD)", f"${total_cost_combined:.6f}")

        # 詳細なプロンプト等を表示する場合は exec_record を使用
        # if 'execution_record' in result_data and result_data['execution_record']:
        #     final_prompt_disp = result_data['execution_record'].get('final_prompt', '')
        #     with st.expander("📝 実行プロンプトを確認"):
        #         st.code(final_prompt_disp, language=None)