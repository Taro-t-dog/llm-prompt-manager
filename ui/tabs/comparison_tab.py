"""
結果比較タブ
2つの実行記録を比較する機能
"""

import streamlit as st
import difflib
import html
from core import GitManager
from ui.components import render_comparison_metrics, render_comparison_responses, render_comparison_evaluations

def _highlight_char_diff(old_line: str, new_line: str) -> tuple[str, str]:
    s = difflib.SequenceMatcher(None, old_line, new_line)
    h_old, h_new = [], []
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        old_chars = html.escape(old_line[i1:i2])
        new_chars = html.escape(new_line[j1:j2])
        if tag == 'replace':
            h_old.append(f'<span class="diff-char-removed">{old_chars}</span>')
            h_new.append(f'<span class="diff-char-added">{new_chars}</span>')
        elif tag == 'delete':
            h_old.append(f'<span class="diff-char-removed">{old_chars}</span>')
        elif tag == 'insert':
            h_new.append(f'<span class="diff-char-added">{new_chars}</span>')
        elif tag == 'equal':
            h_old.append(old_chars)
            h_new.append(new_chars)
    return "".join(h_old), "".join(h_new)

def render_comparison_tab():
    st.header("🔍 実行結果比較")
    executions = GitManager.get_branch_executions()
    comparable_executions = [ex for ex in executions if ex.get('execution_mode') != 'Workflow Step']

    if len(comparable_executions) < 2:
        st.info("比較するには、現在のブランチに最低2つの実行記録（単発実行またはワークフローサマリー）が必要です。")
        return
        
    exec1, exec2 = _render_execution_selection(comparable_executions)
    if exec1 and exec2 and exec1['commit_hash'] != exec2['commit_hash']:
        st.markdown("---")
        _render_comparison_results(exec1, exec2)
    elif exec1 and exec2 and exec1['commit_hash'] == exec2['commit_hash']:
        st.warning("比較元と比較先で同じ実行記録が選択されています。")

def _render_execution_selection(executions):
    st.subheader("📋 比較対象選択")
    reversed_executions = sorted(executions, key=lambda x: str(x.get('timestamp', '1970-01-01')), reverse=True)
    options = {ex['commit_hash']: f"{ex['commit_hash'][:8]} - {ex.get('commit_message', 'メモなし')}" for ex in reversed_executions}
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**🔵 比較元 (古い方)**")
        default_index1 = 1 if len(options) > 1 else 0
        hash1 = st.selectbox("比較元を選択", options.keys(), format_func=lambda h: options.get(h, h), key="exec1_selector", index=default_index1)
        exec1 = next((ex for ex in executions if ex['commit_hash'] == hash1), None)
    with col2:
        st.write("**🔴 比較先 (新しい方)**")
        hash2 = st.selectbox("比較先を選択", options.keys(), format_func=lambda h: options.get(h, h), key="exec2_selector", index=0)
        exec2 = next((ex for ex in executions if ex['commit_hash'] == hash2), None)
            
    return exec1, exec2

def _render_comparison_results(exec1, exec2):
    tab1, tab2, tab3, tab4 = st.tabs(["📊 メトリクス", "📝 プロンプト", "🤖 回答", "⭐ 評価"])
    with tab1: render_comparison_metrics(exec1, exec2)
    with tab2: _render_prompt_diff(exec1, exec2)
    with tab3:
        render_comparison_responses(exec1, exec2)
        st.markdown("**差分:**"); st.markdown(_get_diff_html(exec1.get('response', ''), exec2.get('response', '')), unsafe_allow_html=True)
    with tab4:
        render_comparison_evaluations(exec1, exec2)
        st.markdown("**差分:**"); st.markdown(_get_diff_html(exec1.get('evaluation', ''), exec2.get('evaluation', '')), unsafe_allow_html=True)

def _render_prompt_diff(exec1, exec2):
    st.subheader("プロンプト差分")
    old_text = exec1.get('final_prompt', ''); new_text = exec2.get('final_prompt', '')
    st.markdown(_get_diff_html(old_text, new_text), unsafe_allow_html=True)

def _get_diff_html(old_text: str, new_text: str) -> str:
    old_text = old_text or ""; new_text = new_text or ""
    old_lines, new_lines = old_text.splitlines(), new_text.splitlines()
    if old_text == new_text: return f'<div class="diff-container-main"><div class="diff-context-line">{html.escape(old_text)}</div></div>'
    html_output = ['<div class="diff-container-main">']
    differ = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in differ.get_opcodes():
        if tag == 'replace':
            len_old, len_new = i2 - i1, j2 - j1; common = min(len_old, len_new)
            for k in range(common):
                h_old, h_new = _highlight_char_diff(old_lines[i1 + k], new_lines[j1 + k])
                html_output.append(f'<div class="diff-line-removed">- {h_old}</div>'); html_output.append(f'<div class="diff-line-added">+ {h_new}</div>')
            if len_old > common:
                for k in range(common, len_old): html_output.append(f'<div class="diff-line-removed">- {html.escape(old_lines[i1 + k])}</div>')
            elif len_new > common:
                for k in range(common, len_new): html_output.append(f'<div class="diff-line-added">+ {html.escape(new_lines[j1 + k])}</div>')
        elif tag == 'delete':
            for line in old_lines[i1:i2]: html_output.append(f'<div class="diff-line-removed">- {html.escape(line)}</div>')
        elif tag == 'insert':
            for line in new_lines[j1:j2]: html_output.append(f'<div class="diff-line-added">+ {html.escape(line)}</div>')
        elif tag == 'equal':
            for line in old_lines[i1:i2]: html_output.append(f'<div class="diff-context-line">{html.escape(line)}</div>')
    html_output.append('</div>'); return ''.join(html_output)