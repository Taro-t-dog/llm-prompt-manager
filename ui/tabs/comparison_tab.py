"""
結果比較タブ
2つの実行記録を比較する機能
"""

import streamlit as st
import difflib
import html
from core import GitManager
from ui.components import render_comparison_metrics, render_comparison_responses, render_comparison_evaluations

# --- Helper function for character-level diff highlighting (EXPERIMENTAL) ---
def _highlight_char_diff(old_line: str, new_line: str) -> tuple[str, str]:
    """2つの行の間で文字レベルの差分をハイライトする（実験的）"""
    s = difflib.SequenceMatcher(None, old_line, new_line)
    highlighted_old = []
    highlighted_new = []
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        old_chars = old_line[i1:i2]
        new_chars = new_line[j1:j2]
        escaped_old_chars = html.escape(old_chars)
        escaped_new_chars = html.escape(new_chars)
        if tag == 'replace':
            highlighted_old.append(f'<span class="diff-char-removed">{escaped_old_chars}</span>')
            highlighted_new.append(f'<span class="diff-char-added">{escaped_new_chars}</span>')
        elif tag == 'delete':
            highlighted_old.append(f'<span class="diff-char-removed">{escaped_old_chars}</span>')
        elif tag == 'insert':
            highlighted_new.append(f'<span class="diff-char-added">{escaped_new_chars}</span>')
        elif tag == 'equal':
            highlighted_old.append(escaped_old_chars)
            highlighted_new.append(escaped_new_chars)
    return "".join(highlighted_old), "".join(highlighted_new)
# --- End of helper function ---

def render_comparison_tab():
    """結果比較タブをレンダリング"""
    st.header("🔍 実行結果比較")
    executions_to_show = GitManager.get_branch_executions()
    if len(executions_to_show) < 2:
        st.info("比較するには最低2つの実行記録が必要です。")
        _render_comparison_help()
        return
    exec1, exec2 = _render_execution_selection(executions_to_show)
    if exec1 and exec2 and exec1['commit_hash'] != exec2['commit_hash']:
        st.markdown("---")
        _render_comparison_results(exec1, exec2)
    elif exec1 and exec2 and exec1['commit_hash'] == exec2['commit_hash']:
        st.warning("比較元と比較先で同じ実行記録が選択されています。異なる記録を選択してください。")

def _render_comparison_help():
    """比較機能のヘルプ表示"""
    st.markdown("""
    ### 📖 実行結果比較について
    この機能では、同じブランチ内の2つの実行記録を詳細に比較できます：
    - **📊 メトリクス比較**: コスト、トークン数の変化
    - **📝 プロンプト差分**: プロンプトの変更箇所
    - **🤖 回答比較**: LLMの回答の違い
    - **⭐ 評価比較**: 評価結果の比較
    まずは「新規実行」タブで複数のプロンプトを実行してください。
    """)

def _render_execution_selection(executions_to_show):
    """実行記録選択セクションをレンダリング"""
    st.subheader("📋 比較対象選択")
    comparison_col1, comparison_col2 = st.columns(2)
    execution_options_map = {
        i: f"{execution['commit_hash'][:8]} - {execution.get('commit_message', 'メモなし') or '実行履歴'}"
        for i, execution in enumerate(executions_to_show)
    }
    with comparison_col1:
        st.write("**🔵 比較元実行**")
        exec1_idx = st.selectbox("比較元を選択", options=list(execution_options_map.keys()), format_func=lambda i: execution_options_map[i], key="exec1_selector", help="比較のベースとなる実行記録を選択してください")
        exec1 = executions_to_show[exec1_idx] if exec1_idx is not None else None
        if exec1: _render_execution_summary(exec1, "比較元")
    with comparison_col2:
        st.write("**🔴 比較先実行**")
        exec2_idx = st.selectbox("比較先を選択", options=list(execution_options_map.keys()), format_func=lambda i: execution_options_map[i], key="exec2_selector", help="比較対象となる実行記録を選択してください")
        exec2 = executions_to_show[exec2_idx] if exec2_idx is not None else None
        if exec2: _render_execution_summary(exec2, "比較先")
    return exec1, exec2

def _render_execution_summary(execution, label):
    """実行記録の簡易サマリー表示"""
    with st.expander(f"{label}サマリー ({execution['commit_hash'][:8]})", expanded=False):
        st.markdown(f"""
        - **実行メモ**: {execution.get('commit_message', 'N/A')}
        - **モデル**: {execution.get('model_name', 'Unknown')}
        - **実行コスト**: ${execution.get('execution_cost', 0):.6f}
        - **評価コスト**: ${execution.get('evaluation_cost', 0):.6f} (参考)
        - **総トークン**: {(execution.get('execution_tokens', 0) or 0) + (execution.get('evaluation_tokens', 0) or 0):,}
        - **タイムスタンプ**: {execution.get('timestamp')}
        """)

def _render_comparison_results(exec1, exec2):
    """比較結果をレンダリング"""
    tab_titles = ["📊 メトリクス比較", "📝 プロンプト差分", "🤖 回答比較", "⭐ 評価比較"]
    comp_tab1, comp_tab2, comp_tab3, comp_tab4 = st.tabs(tab_titles)
    with comp_tab1:
        render_comparison_metrics(exec1, exec2)
        _render_detailed_metrics_comparison(exec1, exec2)
    with comp_tab2:
        # _render_prompt_diff は直接 _render_unified_diff (文字差分モード) を呼び出すように変更
        _render_prompt_diff_unified_char_mode(exec1, exec2)
    with comp_tab3:
        render_comparison_responses(exec1, exec2)
        _render_response_analysis(exec1, exec2)
    with comp_tab4:
        render_comparison_evaluations(exec1, exec2)
        _render_evaluation_analysis(exec1, exec2)

def _render_detailed_metrics_comparison(exec1, exec2):
    """詳細メトリクス比較"""
    st.subheader("📈 詳細分析")

    analysis_col1, analysis_col2 = st.columns(2)

    with analysis_col1:
        st.write("**💰 コスト効率分析 (実行コストベース)**")
        cost1 = exec1.get('execution_cost', 0) or 0
        cost2 = exec2.get('execution_cost', 0) or 0

        # cost_diff を先に計算
        cost_diff = cost2 - cost1

        # cost_diff を使って cost_change_pct を計算
        if cost1 > 0:
            cost_change_pct = (cost_diff / cost1) * 100
        elif cost_diff > 0: # cost1 が 0 で cost_diff が正 (0から増加)
            cost_change_pct = float('inf')
        else: # cost1 が 0 で cost_diff が 0 以下 (変化なしまたは0から減少は0%)
            cost_change_pct = 0.0

        if cost_diff > 0:
            st.error(f"コストが ${cost_diff:.6f} ({cost_change_pct:+.1f}%) 増加")
        elif cost_diff < 0:
            st.success(f"コストが ${abs(cost_diff):.6f} ({cost_change_pct:.1f}%) 削減") # cost_change_pctは負なのでそのまま表示
        else:
            st.info("実行コストに変化なし")

    with analysis_col2:
        st.write("**🔢 トークン効率分析 (実行トークンベース)**")
        tokens1 = exec1.get('execution_tokens', 0) or 0
        tokens2 = exec2.get('execution_tokens', 0) or 0

        # token_diff を先に計算
        token_diff = tokens2 - tokens1

        # token_diff を使って token_change_pct を計算
        if tokens1 > 0:
            token_change_pct = (token_diff / tokens1) * 100
        elif token_diff > 0: # tokens1 が 0 で token_diff が正
            token_change_pct = float('inf')
        else: # tokens1 が 0 で token_diff が 0 以下
            token_change_pct = 0.0

        if token_diff > 0:
            st.warning(f"トークン数が {token_diff:,} ({token_change_pct:+.1f}%) 増加")
        elif token_diff < 0:
            st.success(f"トークン数が {abs(token_diff):,} ({token_change_pct:.1f}%) 削減") # token_change_pctは負なのでそのまま表示
        else:
            st.info("実行トークン数に変化なし")

def _render_prompt_diff_unified_char_mode(exec1, exec2): # 関数名を変更し、内容を統合
    """プロンプト差分表示 (統合差分 - 文字レベルハイライトモード固定)"""
    st.subheader("📝 プロンプト差分 (文字レベル強調)")

    # テンプレート差分 (存在すれば)
    if exec1.get('execution_mode') == "テンプレート + データ入力" or \
       exec2.get('execution_mode') == "テンプレート + データ入力":
        st.markdown("**🔧 テンプレート差分**")
        template1 = exec1.get('prompt_template', '') or ""
        template2 = exec2.get('prompt_template', '') or ""
        if template1 or template2: # どちらかにテンプレートがあれば表示
            diff_html_template = _get_diff_html(template1, template2)
            st.markdown(diff_html_template, unsafe_allow_html=True)
        else:
            st.info("比較対象のテンプレートがありません。")
        st.markdown("---")

        st.markdown("**📊 入力データ差分**")
        user_input1 = exec1.get('user_input', '') or ""
        user_input2 = exec2.get('user_input', '') or ""
        if user_input1 or user_input2: # どちらかに入力データがあれば表示
            diff_html_user_input = _get_diff_html(user_input1, user_input2)
            st.markdown(diff_html_user_input, unsafe_allow_html=True)
        else:
            st.info("比較対象の入力データがありません。")
        st.markdown("---")


    st.markdown("**📝 最終プロンプト差分**")
    old_text = exec1.get('final_prompt', '') or ""
    new_text = exec2.get('final_prompt', '') or ""
    diff_html_content = _get_diff_html(old_text, new_text)
    st.markdown(diff_html_content, unsafe_allow_html=True)


def _render_response_analysis(exec1, exec2):
    st.subheader("🔬 回答詳細分析")
    st.info("（回答の詳細分析機能は現在開発中です）")

def _render_evaluation_analysis(exec1, exec2):
    st.subheader("⭐ 評価詳細分析")
    st.info("（評価の詳細分析機能は現在開発中です）")


def _get_diff_html(old_text: str, new_text: str) -> str: # mode パラメータは削除 (常に文字モードを試みるため)
    """2つのテキストの差分をHTMLで表示（文字レベルハイライト試行）"""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    if old_text == new_text:
        return '<p class="diff-no-change">プロンプトに変更はありません。</p>'

    html_output = ['<div class="diff-container-main">']
    s = difflib.SequenceMatcher(None, old_lines, new_lines)
    has_visible_change = False

    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == 'equal':
            for i in range(i1, i2):
                html_output.append(f'<div class="diff-context-line">{html.escape(old_lines[i])}</div>')
        else: # 'replace', 'delete', 'insert'
            has_visible_change = True
            # replace の場合は行ごとに文字レベル差分を試みる
            if tag == 'replace':
                # 行数が少ない方に合わせてペアを作り、残りは単純な追加/削除として扱う
                len_old_chunk = i2 - i1
                len_new_chunk = j2 - j1
                common_len = min(len_old_chunk, len_new_chunk)

                for k in range(common_len):
                    old_l = old_lines[i1 + k]
                    new_l = new_lines[j1 + k]
                    h_old, h_new = _highlight_char_diff(old_l, new_l)
                    # 実際に文字レベルで差分があった行のみを replace として表示
                    if h_old != html.escape(old_l) or h_new != html.escape(new_l):
                        html_output.append(f'<div class="diff-line-removed-char">- {h_old}</div>')
                        html_output.append(f'<div class="diff-line-added-char">+ {h_new}</div>')
                    else: # 文字レベルでは差分なし（行としてはreplaceだが）
                        html_output.append(f'<div class="diff-context-line">{html.escape(new_l)}</div>') # 新しい行を表示

                # 残りの行の処理
                if len_old_chunk > common_len: # 旧テキストに残りがある (削除)
                    for k in range(common_len, len_old_chunk):
                        html_output.append(f'<div class="diff-line-removed-char">- {html.escape(old_lines[i1 + k])}</div>')
                elif len_new_chunk > common_len: # 新テキストに残りがある (追加)
                    for k in range(common_len, len_new_chunk):
                        html_output.append(f'<div class="diff-line-added-char">+ {html.escape(new_lines[j1 + k])}</div>')

            elif tag == 'delete':
                for i in range(i1, i2):
                    html_output.append(f'<div class="diff-line-removed-char">- {html.escape(old_lines[i])}</div>')
            elif tag == 'insert':
                for i in range(j1, j2):
                    html_output.append(f'<div class="diff-line-added-char">+ {html.escape(new_lines[i])}</div>')

    html_output.append('</div>')

    if not has_visible_change and old_text != new_text:
        return f"""
            <p class="diff-subtle-change">表示可能な構造的な差分は検出されませんでしたが、テキストは異なります。</p>
            <div class="diff-container-main">
                <div><strong>比較元プロンプト:</strong><pre>{html.escape(old_text)}</pre></div>
                <div><strong>比較先プロンプト:</strong><pre>{html.escape(new_text)}</pre></div>
            </div>
        """
    return ''.join(html_output)