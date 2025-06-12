# ============================================
# ui/styles.py (ワークフロー機能対応拡張版) - 修正版
# ============================================
"""
モダンで洗練されたUIスタイル定義
既存スタイル + ワークフロー機能用の追加スタイル
"""

import streamlit as st


def load_styles():
    """アプリケーションの洗練されたCSSスタイルを読み込む（ワークフロー機能対応）"""
    st.markdown("""
    <style>
        /* === メインカラーパレット === */
        :root {
            --primary-color: #667eea;
            --primary-dark: #5a67d8;
            --secondary-color: #764ba2;
            --accent-color: #f093fb;
            --success-color: #48bb78;
            --warning-color: #ed8936;
            --error-color: #f56565;
            --workflow-color: #38b2ac;  /* 🆕 ワークフロー用カラー */
            --neutral-100: #f7fafc;
            --neutral-200: #edf2f7;
            --neutral-300: #e2e8f0;
            --neutral-600: #718096;
            --neutral-700: #4a5568;
            --neutral-800: #2d3748;
            --neutral-900: #1a202c;
        }

        /* === 全体レイアウト === */
        .main .block-container {
            padding-top: 2rem;
            max-width: 1200px;
        }

        /* === ボタンスタイリング === */
        .stButton > button {
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
            font-size: 0.95rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.2);
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }

        /* === カードコンポーネント === */
        .modern-card {
            background: white;
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 1px solid var(--neutral-200);
            transition: all 0.3s ease;
        }

        .modern-card:hover {
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
            transform: translateY(-2px);
        }
        
        .branch-tag {
            background-color: var(--neutral-200);
            color: var(--neutral-700);
            padding: 0.2em 0.5em;
            border-radius: 0.25rem;
            font-size: 0.8em;
            font-weight: 600;
        }

        .commit-hash {
            font-family: monospace;
            color: var(--neutral-600);
            font-size: 0.9em;
        }

        /* === レスポンス・評価ボックス === */
        .response-box {
            background: linear-gradient(135deg, #f8faff 0%, #f1f5ff 100%);
            color: var(--neutral-800);
            padding: 1.5rem;
            border-radius: 16px;
            border-left: 4px solid var(--primary-color);
            margin: 1rem 0;
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.1);
            position: relative;
            overflow: hidden;
        }

        .evaluation-box {
            background: linear-gradient(135deg, #fff8f8 0%, #fef5f5 100%);
            color: var(--neutral-800);
            padding: 1.5rem;
            border-radius: 16px;
            border-left: 4px solid var(--error-color);
            margin: 1rem 0;
            box-shadow: 0 6px 20px rgba(245, 101, 101, 0.1);
        }
        
        /* === 差分表示の改善 === */
        .diff-container-main {
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            background: var(--neutral-900);
            color: var(--neutral-100);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
            border: 1px solid var(--neutral-700);
            overflow-x: auto;
            white-space: pre-wrap; /* 改行を保持 */
        }

        .diff-line-added {
            background: rgba(72, 187, 120, 0.2);
            color: #9ae6b4;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            margin: 0.1rem 0;
            display: block;
        }

        .diff-line-removed {
            background: rgba(245, 101, 101, 0.2);
            color: #feb2b2;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            margin: 0.1rem 0;
            display: block;
        }

        .diff-char-added {
            background: var(--success-color);
            color: white;
            font-weight: 600;
            padding: 0 0.2rem;
            border-radius: 3px;
        }

        .diff-char-removed {
            background: var(--error-color);
            color: white;
            text-decoration: line-through;
            font-weight: 600;
            padding: 0 0.2rem;
            border-radius: 3px;
        }

        .diff-context-line {
            display: block;
            color: #a0aec0; /* Lighter color for context lines */
        }
    </style>
    """, unsafe_allow_html=True)


def get_response_box_html(content: str, border_color: str = None) -> str:
    import html
    escaped_content = html.escape(content).replace('\n', '<br>')
    return f'<div class="response-box fade-in-up"><p style="line-height: 1.6; margin: 0; font-size: 1rem;">{escaped_content}</p></div>'

def get_evaluation_box_html(content: str) -> str:
    import html
    escaped_content = html.escape(content).replace('\n', '<br>')
    return f'<div class="evaluation-box fade-in-up"><p style="line-height: 1.6; margin: 0; font-size: 1rem;">{escaped_content}</p></div>'

def get_metric_card_html(title: str, value: str, subtitle: str = "") -> str:
    subtitle_html = f'<p style="color: var(--neutral-600); margin: 0.5rem 0 0 0; font-size: 0.85rem;">{subtitle}</p>' if subtitle else ""
    return f'<div class="metric-card"><h4>{title}</h4><h2>{value}</h2>{subtitle_html}</div>'

def format_detailed_cost_display(cost: float) -> str:
    if cost == 0:
        return "$0.000000"
    elif cost < 0.000001 and cost > 0:
        return f"${cost:.8f}"
    else:
        return f"${cost:.6f}"

def format_tokens_display(tokens: int) -> str:
    if tokens < 1000:
        return str(tokens)
    elif tokens < 1000000:
        return f"{tokens / 1000:.1f}K"
    else:
        return f"{tokens / 1000000:.1f}M"

def get_header_html(title: str, stats: dict) -> str: return ""
def get_commit_card_style(): return "commit-card"
def get_branch_tag_html(branch_name: str): return f'<span class="branch-tag">{branch_name}</span>'