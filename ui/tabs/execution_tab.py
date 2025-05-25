"""
改善されたプロンプト実行タブ
"""

import streamlit as st
import datetime
from config import get_model_config
from core import GeminiEvaluator, GitManager
from ui.components import render_response_box, render_evaluation_box, render_cost_metrics


def render_execution_tab():
    """改善された実行タブ"""
    
    # セッションステート初期化
    _initialize_session_state()
    
    # コンパクトなヘッダー
    exec_col1, exec_col2 = st.columns([3, 1])
    
    with exec_col1:
        st.markdown("### 新しいプロンプトを実行")
    
    with exec_col2:
        current_branch = GitManager.get_current_branch()
        st.markdown(f"**ブランチ:** `{current_branch}`")
    
    # フォームを使用して一括処理
    with st.form("execution_form", clear_on_submit=False):
        # 実行メモ
        memo_col1, memo_col2 = st.columns([4, 1])
        
        with memo_col1:
            execution_memo = st.text_input(
                "📝 実行メモ",
                value=st.session_state.execution_memo,
                placeholder="変更内容や実験目的...",
                key="memo_input_form"
            )
        
        with memo_col2:
            execution_mode = st.radio(
                "モード",
                ["テンプレート", "単一"],
                index=0 if st.session_state.execution_mode == "テンプレート + データ入力" else 1,
                horizontal=True,
                key="mode_radio_form"
            )
        
        # モード変換
        execution_mode_full = "テンプレート + データ入力" if execution_mode == "テンプレート" else "単一プロンプト"
        
        # プロンプト設定
        prompt_template, user_input_data, single_prompt = _render_prompt_section_form(execution_mode_full)
        
        # 評価基準
        evaluation_criteria = _render_evaluation_section_form()
        
        # 実行ボタン
        submitted = st.form_submit_button("🚀 実行", type="primary", use_container_width=True)
    
    # フォーム外で実行処理と結果表示
    if submitted:
        # セッションステートを更新
        st.session_state.execution_memo = execution_memo
        st.session_state.execution_mode = execution_mode_full
        st.session_state.evaluation_criteria = evaluation_criteria
        st.session_state.prompt_template = prompt_template
        st.session_state.user_input_data = user_input_data
        st.session_state.single_prompt = single_prompt
        
        # 実行処理
        _execute_prompt_direct(execution_memo, execution_mode_full, evaluation_criteria)
    
    # 最新の実行結果を表示（もしあれば）
    if hasattr(st.session_state, 'latest_execution_result') and st.session_state.latest_execution_result:
        st.markdown("---")
        _display_latest_results()


def _initialize_session_state():
    """セッション状態の初期化"""
    defaults = {
        'execution_memo': "",
        'execution_mode': "テンプレート + データ入力",
        'prompt_template': "以下のテキストを要約してください：\n\n{user_input}",
        'user_input_data': "",
        'single_prompt': "",
        'evaluation_criteria': """1. 正確性（30点）
2. 網羅性（25点）
3. 分かりやすさ（25点）
4. 論理性（20点）"""
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def _render_prompt_section_form(execution_mode):
    """フォーム内でのプロンプト設定セクション"""
    st.markdown("### 📝 プロンプト")
    
    if execution_mode == "テンプレート + データ入力":
        template_col1, template_col2 = st.columns(2)
        
        with template_col1:
            st.markdown("**テンプレート**")
            prompt_template = st.text_area(
                "",
                value=st.session_state.prompt_template,
                height=200,
                placeholder="{user_input}でデータを参照",
                key="template_area_form",
                label_visibility="collapsed"
            )
        
        with template_col2:
            st.markdown("**データ**")
            user_input_data = st.text_area(
                "",
                value=st.session_state.user_input_data,
                height=200,
                placeholder="処理したいデータを入力...",
                key="data_area_form",
                label_visibility="collapsed"
            )
        
        # プレビュー
        if (prompt_template and 
            user_input_data and 
            "{user_input}" in prompt_template):
            
            if st.checkbox("🔍 最終プロンプトを確認", key="preview_form"):
                final_prompt = prompt_template.replace(
                    "{user_input}", user_input_data
                )
                st.code(final_prompt[:500] + "..." if len(final_prompt) > 500 else final_prompt)
        
        elif prompt_template and "{user_input}" not in prompt_template:
            st.warning("⚠️ テンプレートに{user_input}を含めてください")
        
        return prompt_template, user_input_data, ""
    
    else:  # 単一プロンプト
        st.markdown("**プロンプト**")
        single_prompt = st.text_area(
            "",
            value=st.session_state.single_prompt,
            height=200,
            placeholder="プロンプトを入力してください...",
            key="single_area_form",
            label_visibility="collapsed"
        )
        return "", "", single_prompt


def _render_evaluation_section_form():
    """フォーム内での評価基準設定セクション"""
    st.markdown("### 📋 評価基準")
    evaluation_criteria = st.text_area(
        "",
        value=st.session_state.evaluation_criteria,
        height=120,
        key="criteria_area_form",
        label_visibility="collapsed"
    )
    
    return evaluation_criteria


def _execute_prompt_direct(execution_memo, execution_mode, evaluation_criteria):
    """直接実行処理（フォーム用）"""
    # バリデーション
    validation_errors = _validate_inputs_direct(execution_memo, execution_mode, evaluation_criteria)
    if validation_errors:
        for error in validation_errors:
            st.error(error)
        return
    
    # APIキーとモデル設定
    if not st.session_state.api_key:
        st.error("❌ APIキーが設定されていません")
        return
    
    model_config = get_model_config(st.session_state.selected_model)
    evaluator = GeminiEvaluator(st.session_state.api_key, model_config)
    
    # 最終プロンプト作成
    if execution_mode == "テンプレート + データ入力":
        final_prompt = st.session_state.prompt_template.replace(
            "{user_input}", st.session_state.user_input_data
        )
        prompt_template = st.session_state.prompt_template
        user_input = st.session_state.user_input_data
    else:
        final_prompt = st.session_state.single_prompt
        prompt_template = None
        user_input = None
    
    # プロンプト実行
    with st.spinner(f"🔄 {model_config['name']}で実行中..."):
        execution_result = evaluator.execute_prompt(final_prompt)
    
    if not execution_result['success']:
        st.error(f"❌ {execution_result['error']}")
        return
    
    # 評価実行
    with st.spinner("📊 評価中..."):
        evaluation_result = evaluator.evaluate_response(
            final_prompt,
            execution_result['response'],
            evaluation_criteria
        )
    
    if not evaluation_result['success']:
        st.error(f"❌ 評価エラー: {evaluation_result['error']}")
        return
    
    # 記録作成と保存
    execution_data = {
        'timestamp': datetime.datetime.now(),
        'execution_mode': execution_mode,
        'prompt_template': prompt_template,
        'user_input': user_input,
        'final_prompt': final_prompt,
        'criteria': evaluation_criteria,
        'response': execution_result['response'],
        'evaluation': evaluation_result['response'],
        'execution_tokens': execution_result['total_tokens'],
        'evaluation_tokens': evaluation_result['total_tokens'],
        'execution_cost': execution_result['cost_usd'],
        'evaluation_cost': evaluation_result['cost_usd'],
        'total_cost': execution_result['cost_usd'] + evaluation_result['cost_usd'],
        'model_name': execution_result['model_name'],
        'model_id': execution_result['model_id']
    }
    
    execution_record = GitManager.create_commit(execution_data, execution_memo)
    GitManager.add_commit_to_history(execution_record)
    
    # 結果をセッションステートに保存
    st.session_state.latest_execution_result = {
        'execution_result': execution_result,
        'evaluation_result': evaluation_result,
        'execution_record': execution_record
    }
    
    st.success(f"✅ 実行完了 | ID: `{execution_record['commit_hash']}`")


def _display_latest_results():
    """最新の実行結果を表示"""
    if not hasattr(st.session_state, 'latest_execution_result') or not st.session_state.latest_execution_result:
        return
    
    result_data = st.session_state.latest_execution_result
    execution_result = result_data['execution_result']
    evaluation_result = result_data['evaluation_result']
    execution_record = result_data['execution_record']
    
    # 結果表示
    result_col1, result_col2 = st.columns([2, 1])
    
    with result_col1:
        render_response_box(execution_result['response'], "🤖 LLMの回答")
        render_evaluation_box(evaluation_result['response'], "⭐ 評価結果")
    
    with result_col2:
        st.markdown("### 📊 実行情報")
        
        # メトリクス
        st.metric("実行トークン", f"{execution_result['total_tokens']:,}")
        st.metric("評価トークン", f"{evaluation_result['total_tokens']:,}")
        st.metric("実行コスト", f"${execution_result['cost_usd']:.6f}")
        st.metric("評価コスト", f"${evaluation_result['cost_usd']:.6f}")
        st.metric("総コスト", f"${execution_result['cost_usd'] + evaluation_result['cost_usd']:.6f}")
        
        # モデル情報
        st.markdown(f"**モデル:** {execution_result['model_name']}")
        st.markdown(f"**ブランチ:** {execution_record['branch']}")
        
        # プロンプト確認（エクスパンダーを使用）
        with st.expander("📝 実行プロンプトを確認"):
            st.code(execution_record['final_prompt'], language=None)


def _validate_inputs_direct(execution_memo, execution_mode, evaluation_criteria):
    """直接入力検証（フォーム用）"""
    errors = []
    
    if not execution_memo.strip():
        errors.append("❌ 実行メモを入力してください")
    
    if execution_mode == "テンプレート + データ入力":
        if not st.session_state.prompt_template.strip():
            errors.append("❌ プロンプトテンプレートを入力してください")
        elif "{user_input}" not in st.session_state.prompt_template:
            errors.append("❌ テンプレートに{user_input}を含めてください")
        
        if not st.session_state.user_input_data.strip():
            errors.append("❌ 処理データを入力してください")
    else:
        if not st.session_state.single_prompt.strip():
            errors.append("❌ プロンプトを入力してください")
    
    if not evaluation_criteria.strip():
        errors.append("❌ 評価基準を入力してください")
    
    return errors