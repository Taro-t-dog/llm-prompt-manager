"""
UIスタイル定義
"""

import streamlit as st


def load_styles():
    """アプリケーションのCSSスタイルを読み込む"""
    st.markdown("""
    <style>
        .stButton > button {
            width: 100%;
            /* background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); */ /* 標準ボタンのスタイルは維持 */
            /* color: white; */
            /* border: none; */
            /* padding: 0.75rem; */
            /* border-radius: 8px; */
            /* font-weight: bold; */
            /* font-size: 1.1rem; */
        }
        .metric-card {
            background: white; /* ダークテーマでは #333 などに変更検討 */
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
            border: 1px solid #444; /* ダークテーマ用 */
            color: #ccc; /* ダークテーマ用 */
        }
        .metric-card h4 { /* metric-card内のh4の文字色 */
            color: #ddd;
        }
        .metric-card h2 { /* metric-card内のh2の文字色 */
             color: #88aaff; /* 目立つ色 */
        }

        .response-box {
            background: #2b2b2b; /* ダークテーマ用 */
            color: #f0f0f0;     /* ダークテーマ用 */
            padding: 2rem;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            margin: 1rem 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .evaluation-box {
            background: #2b2b2b; /* ダークテーマ用 */
            color: #f0f0f0;     /* ダークテーマ用 */
            padding: 2rem;
            border-radius: 10px;
            border-left: 4px solid #f5576c;
            margin: 1rem 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .commit-card {
            background: #333; /* ダークテーマ用 */
            border: 1px solid #444; /* ダークテーマ用 */
            color: #ccc; /* ダークテーマ用 */
            border-radius: 8px;
            padding: 1rem;
            margin: 0.5rem 0;
        }
        .commit-hash {
            font-family: monospace;
            color: #aaa; /* ダークテーマ用 */
            font-size: 0.9rem;
        }
        .branch-tag {
            display: inline-block;
            background: #28a745;
            color: white;
            padding: 0.2rem 0.5rem;
            border-radius: 12px;
            font-size: 0.8rem;
            margin-right: 0.5rem;
        }
        .tag-label {
            display: inline-block;
            background: #ffc107;
            color: #212529;
            padding: 0.2rem 0.5rem;
            border-radius: 12px;
            font-size: 0.8rem;
            margin-right: 0.5rem;
        }

        
        .diff-added { /* これは元の汎用的な差分スタイル */
            background: #d4edda;
            color: #155724;
            padding: 0.2rem;
        }
        .diff-removed { /* これも元の汎用的な差分スタイル */
            background: #f8d7da;
            color: #721c24;
            padding: 0.2rem;
        } /* ここで .diff-removed の定義を閉じる */

        .diff-container-main { /* メインの差分コンテナ */
            font-family: monospace;
            white-space: pre-wrap;
            line-height: 1.5em;
            font-size: 0.9em;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
            background-color: #1e1e1e;
            color: #d4d4d4;
            margin-bottom: 1em;
        }

        /* 行レベルの差分 (unified_diff風) */
        .diff-line-added {
            background-color: rgba(0, 100, 0, 0.2); /* 暗めの緑背景 */
            color: #90ee90; /* 明るい緑の文字 */
            display: block;
        }
        .diff-line-removed {
            background-color: rgba(100, 0, 0, 0.2); /* 暗めの赤背景 */
            color: #ff7f7f; /* 明るい赤の文字 */
            display: block;
        }
        .diff-context-line { /* 変更のない行 */
            color: #9e9e9e;
            display: block;
        }

        /* 文字レベルの差分ハイライト用 */
        .diff-line-added-char, .diff-line-removed-char { /* 文字差分を含む行の基本スタイル */
             display: block; /* 行として表示 */
        }
        .diff-char-added {
            background-color: darkgreen; /* 文字の背景を濃い緑に */
            color: white;
            font-weight: bold;
            padding: 0 1px; /* 少しパディング */
            border-radius: 2px;
        }
        .diff-char-removed {
            background-color: darkred; /* 文字の背景を濃い赤に */
            color: #ffcccc; /* 文字色を少し明るく */
            text-decoration: line-through;
            font-weight: bold;
            padding: 0 1px;
            border-radius: 2px;
        }

        /* 差分がない場合などのメッセージ用 */
        .diff-no-change { color: #4CAF50; font-style: italic; }
        .diff-subtle-change { color: #FFC107; font-style: italic; }
        .diff-subtle-change pre {
            background-color: #2a2a2a; padding: 5px;
            border: 1px dashed #555; margin-top: 5px; color: #ccc;
        }
    </style>
    """, unsafe_allow_html=True)


def get_response_box_html(content: str, border_color: str = "#667eea") -> str:
    """レスポンスボックスのHTMLを生成"""
    import html
    escaped_content = html.escape(content).replace('\n', '<br>')
    return f"""
    <div style="background: #ffffff; color: #2c3e50; padding: 2rem; border-radius: 10px; border-left: 4px solid {border_color}; margin: 1rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <p style="color: #2c3e50; line-height: 1.6; margin: 0;">{escaped_content}</p>
    </div>
    """


def get_evaluation_box_html(content: str) -> str:
    """評価ボックスのHTMLを生成"""
    return get_response_box_html(content, "#f5576c")


def get_metric_card_html(title: str, value: str, subtitle: str = "") -> str:
    """メトリクスカードのHTMLを生成"""
    subtitle_html = f'<p style="color: #666; margin: 0;">{subtitle}</p>' if subtitle else ""
    return f"""
    <div style="background: #ffffff; color: #2c3e50; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; border: 1px solid #e0e0e0;">
        <h4 style="color: #2c3e50; margin: 0 0 0.5rem 0;">{title}</h4>
        <h2 style="color: #667eea; margin: 0.5rem 0;">{value}</h2>
        {subtitle_html}
    </div>
    """


def get_commit_card_style():
    """コミットカードのスタイルクラス名を返す"""
    return "commit-card"


def get_branch_tag_html(branch_name: str) -> str:
    """ブランチタグのHTMLを生成"""
    return f'<span class="branch-tag">{branch_name}</span>'


def get_tag_label_html(tag_name: str) -> str:
    """タグラベルのHTMLを生成"""
    return f'<span class="tag-label">{tag_name}</span>'