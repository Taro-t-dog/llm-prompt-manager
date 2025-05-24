"""
新規実行タブ
プロンプトの実行と評価を行う機能
"""

import streamlit as st
import datetime
from config import get_model_config
from core import GeminiEvaluator, GitManager
from ui.components import render_response_box, render_evaluation_box, render_cost_metrics


def render_execution_tab():
    """新規実行タブをレンダリング"""
    st.header("新しいプロンプトを実行")

    # セッションステートで各入力値を保持・管理する
    # これにより、再実行後も値を引き継げる
    if 'execution_memo' not in st.session_state:
        st.session_state.execution_memo = ""
    if 'execution_mode' not in st.session_state:
        st.session_state.execution_mode = "テンプレート + データ入力" # デフォルト値
    if 'prompt_template' not in st.session_state:
        st.session_state.prompt_template = ""
    if 'user_input_data' not in st.session_state: # user_input は組み込み関数と衝突する可能性があるため変更
        st.session_state.user_input_data = ""
    if 'single_prompt' not in st.session_state:
        st.session_state.single_prompt = ""
    if 'evaluation_criteria' not in st.session_state:
        st.session_state.evaluation_criteria = """1. 回答の正確性（30点）
2. 情報の網羅性（25点）
3. 説明の分かりやすさ（25点）
4. 構成の論理性（20点）""" # デフォルト値

    # 実行メモ
    st.session_state.execution_memo = st.text_input(
        "📝 実行メモ",
        value=st.session_state.execution_memo, # セッションステートから値を取得
        placeholder="プロンプトの変更内容や実験の目的を記録してください...",
        help="この実行の目的や変更点を記録します（Git風の履歴管理）",
        key="memo_input" # 実行メモ用のキー
    )

    # 実行モード選択
    st.subheader("📋 実行モード選択")
    # st.radio の index を session_state で管理するか、値を直接 session_state に保存
    # ここでは値を直接保存するアプローチ
    current_execution_mode = st.radio(
        "実行方法を選択してください",
        ["テンプレート + データ入力", "単一プロンプト"],
        index=["テンプレート + データ入力", "単一プロンプト"].index(st.session_state.execution_mode), # 現在の値を反映
        horizontal=True,
        key="mode_radio"
    )
    # radioボタンの値が変更されたらセッションステートも更新
    if current_execution_mode != st.session_state.execution_mode:
        st.session_state.execution_mode = current_execution_mode
        # モード変更時に他の関連する状態をリセットするならここで行う
        # 例えば、テンプレートと単一プロンプトの内容をクリアするなど
        # st.session_state.prompt_template = ""
        # st.session_state.user_input_data = ""
        # st.session_state.single_prompt = ""
        st.rerun() # モード変更を即時反映させるために再実行

    st.markdown("---")

    # プロンプト設定
    # _render_prompt_configuration 内で session_state を使用して値を更新・取得
    _render_prompt_configuration_widgets_no_form(st.session_state.execution_mode)

    st.markdown("---")

    # 評価基準設定
    # _render_evaluation_criteria 内で session_state を使用
    _render_evaluation_criteria_widgets_no_form()

    st.markdown("---")

    # 実行ボタン
    if st.button("🚀 実行 & 履歴に記録", type="primary", key="execute_button"):
        # ボタンクリック時にセッションステートから最新の値を取得して処理
        memo_to_use = st.session_state.execution_memo
        mode_to_use = st.session_state.execution_mode
        criteria_to_use = st.session_state.evaluation_criteria

        final_prompt_to_use = None
        prompt_template_to_use = None
        user_input_to_use = None

        if mode_to_use == "テンプレート + データ入力":
            prompt_template_to_use = st.session_state.prompt_template
            user_input_to_use = st.session_state.user_input_data
            if prompt_template_to_use and user_input_to_use and "{user_input}" in prompt_template_to_use:
                final_prompt_to_use = prompt_template_to_use.replace("{user_input}", user_input_to_use)
            elif prompt_template_to_use and "{user_input}" not in prompt_template_to_use:
                st.warning("⚠️ プロンプトテンプレートに{user_input}を含めてください (実行は中止されます)")
                # final_prompt_to_use は None のまま
            else:
                # final_prompt_to_use は None のまま
                pass
        else: # 単一プロンプト
            final_prompt_to_use = st.session_state.single_prompt
            # prompt_template_to_use, user_input_to_use は None のまま

        _execute_and_record(memo_to_use, final_prompt_to_use, criteria_to_use,
                          mode_to_use, prompt_template_to_use, user_input_to_use)

def _render_prompt_configuration_widgets_no_form(execution_mode):
    """プロンプト設定ウィジェット（フォームなし）。値をセッションステートに保存。"""
    st.subheader("📝 プロンプト設定")

    if execution_mode == "テンプレート + データ入力":
        template_col1, template_col2 = st.columns(2)
        with template_col1:
            st.write("**🔧 プロンプトテンプレート**")
            st.session_state.prompt_template = st.text_area(
                "テンプレートを入力",
                value=st.session_state.prompt_template,
                height=200,
                placeholder="""例：以下のテキストを要約してください：...""",
                help="{user_input}でユーザー入力を参照できます",
                key="template_text_area"
            )
        with template_col2:
            st.write("**📊 処理データ**")
            st.session_state.user_input_data = st.text_area(
                "処理したいデータを入力",
                value=st.session_state.user_input_data,
                height=200,
                placeholder="ここに処理したいデータを入力してください...",
                key="user_data_text_area"
            )

        # プレビュー (リアルタイム)
        # このプレビューはボタンの状態とは独立して表示される
        if st.session_state.prompt_template and st.session_state.user_input_data and \
           "{user_input}" in st.session_state.prompt_template:
            final_prompt_preview = st.session_state.prompt_template.replace("{user_input}", st.session_state.user_input_data)
            if st.checkbox("🔍 最終プロンプトをプレビュー", key="preview_checkbox_template"):
                st.code(final_prompt_preview, language=None)
        elif st.session_state.prompt_template and "{user_input}" not in st.session_state.prompt_template:
            st.warning("⚠️ プロンプトテンプレートに{user_input}を含めてください")


    else: # 単一プロンプトモード
        st.write("**📝 単一プロンプト**")
        st.session_state.single_prompt = st.text_area(
            "プロンプトを入力",
            value=st.session_state.single_prompt,
            height=200,
            placeholder="評価したいプロンプトを入力してください...",
            key="single_prompt_text_area"
        )

def _render_evaluation_criteria_widgets_no_form():
    """評価基準設定ウィジェット（フォームなし）。値をセッションステートに保存。"""
    st.subheader("📋 評価基準設定")
    st.session_state.evaluation_criteria = st.text_area(
        "評価基準を入力",
        value=st.session_state.evaluation_criteria,
        height=150,
        help="LLMの回答をどのような基準で評価するかを記載してください",
        key="criteria_text_area"
    )

# _execute_and_record と _display_execution_results は前回のコードから変更なし
# ただし、_execute_and_record 内のバリデーションとAPIキーチェック、モデル設定取得は重要

def _execute_and_record(execution_memo, final_prompt, evaluation_criteria,
                       execution_mode, prompt_template, user_input):
    """プロンプトを実行し、結果を記録"""

    # バリデーション
    if not execution_memo:
        st.error("❌ 実行メモを入力してください")
        return
    if not final_prompt: # final_promptがNoneや空文字列の場合
        if execution_mode == "テンプレート + データ入力":
            st.error("❌ プロンプトテンプレートと処理データを正しく入力し、{user_input} を含めてください。")
        else:
            st.error("❌ プロンプトを入力してください。")
        return
    if not evaluation_criteria:
        st.error("❌ 評価基準を入力してください")
        return

    # APIキーのチェック
    if 'api_key' not in st.session_state or not st.session_state.api_key:
        st.error("❌ APIキーが設定されていません。サイドバーから設定してください。")
        return

    # モデル設定取得
    if 'selected_model' not in st.session_state:
        st.error("❌ モデルが選択されていません。サイドバーから選択してください。")
        return
    current_model_config = get_model_config(st.session_state.selected_model)
    if not current_model_config:
        st.error(f"❌ 選択されたモデル '{st.session_state.selected_model}' の設定が見つかりません。")
        return
    evaluator = GeminiEvaluator(st.session_state.api_key, current_model_config)

    # プロンプト実行
    with st.spinner(f"🔄 '{current_model_config.get('name', 'Unknown Model')}'でプロンプト実行中..."): # .getで安全にアクセス
        execution_result = evaluator.execute_prompt(final_prompt)

    if not execution_result['success']:
        st.error(f"❌ プロンプト実行エラー: {execution_result.get('error', '不明なエラー')}")
        return

    # 評価実行
    with st.spinner("📊 評価中..."):
        evaluation_result = evaluator.evaluate_response(
            final_prompt,
            execution_result.get('response', ''), # .getで安全にアクセス
            evaluation_criteria
        )

    if not evaluation_result['success']:
        st.error(f"❌ 評価エラー: {evaluation_result.get('error', '不明なエラー')}")
        return

    # 実行記録作成
    execution_data = {
        'timestamp': datetime.datetime.now(),
        'execution_mode': execution_mode,
        'prompt_template': prompt_template,
        'user_input': user_input,
        'final_prompt': final_prompt,
        'criteria': evaluation_criteria,
        'response': execution_result.get('response'),
        'evaluation': evaluation_result.get('response'), # 評価APIのレスポンス
        'execution_tokens': execution_result.get('total_tokens'),
        'evaluation_tokens': evaluation_result.get('total_tokens'), # 評価に使ったトークン
        'execution_cost': execution_result.get('cost_usd'),
        'evaluation_cost': evaluation_result.get('cost_usd'), # 評価のコスト
        'total_cost': (execution_result.get('cost_usd', 0) or 0) + (evaluation_result.get('cost_usd', 0) or 0), # 実行と評価の合計
        'model_name': execution_result.get('model_name'),
        'model_id': execution_result.get('model_id')
    }

    execution_record = GitManager.create_commit(execution_data, execution_memo)
    GitManager.add_commit_to_history(execution_record)

    # 結果表示
    _display_execution_results(execution_result, evaluation_result, execution_data, execution_record)


def _display_execution_results(execution_result, evaluation_result, execution_data, execution_record):
    """実行結果を表示"""
    st.success(f"✅ 実行完了！使用モデル: {execution_result.get('model_name', 'N/A')}")
    st.info(f"🔗 実行ID: `{execution_record.get('commit_hash', 'N/A')}`") # .getで安全にアクセス
    st.markdown("---")

    # 実行に使用した最終プロンプトの表示 (オプション)
    if execution_data.get('final_prompt'):
        if st.checkbox("実行に使用した最終プロンプトを表示", value=False, key="show_executed_prompt_checkbox"):
            st.code(execution_data['final_prompt'], language=None)

    render_response_box(execution_result.get('response', '回答がありません'))
    render_evaluation_box(evaluation_result.get('response', '評価結果がありません')) # 評価APIのレスポンス
    render_cost_metrics(
        execution_cost=execution_data.get('execution_cost', 0.0),
        evaluation_cost=execution_data.get('evaluation_cost', 0.0),
        total_cost=execution_data.get('total_cost', 0.0),
        execution_tokens=execution_data.get('execution_tokens', 0),
        evaluation_tokens=execution_data.get('evaluation_tokens', 0)
    )