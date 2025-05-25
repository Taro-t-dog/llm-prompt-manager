"""
モダンで洗練されたUIスタイル定義
"""

import streamlit as st


def load_styles():
    """アプリケーションの洗練されたCSSスタイルを読み込む"""
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

        /* === メトリクスカード === */
        .metric-card {
            background: linear-gradient(135deg, white 0%, var(--neutral-100) 100%);
            padding: 1.5rem;
            border-radius: 16px;
            text-align: center;
            border: 1px solid var(--neutral-200);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
        }

        .metric-card:hover {
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
            transform: translateY(-2px);
        }

        .metric-card h4 {
            color: var(--neutral-600);
            font-size: 0.9rem;
            font-weight: 500;
            margin: 0 0 0.5rem 0;
        }

        .metric-card h2 {
            color: var(--primary-color);
            font-size: 1.8rem;
            font-weight: 700;
            margin: 0;
        }

        /* === レスポンス・評価ボックス === */
        .response-box {
            background: linear-gradient(135deg, #f8faff 0%, #f1f5ff 100%);
            color: var(--neutral-800);
            padding: 2rem;
            border-radius: 16px;
            border-left: 4px solid var(--primary-color);
            margin: 1rem 0;
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.1);
            position: relative;
            overflow: hidden;
        }

        .response-box::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
        }

        .evaluation-box {
            background: linear-gradient(135deg, #fff8f8 0%, #fef5f5 100%);
            color: var(--neutral-800);
            padding: 2rem;
            border-radius: 16px;
            border-left: 4px solid var(--error-color);
            margin: 1rem 0;
            box-shadow: 0 6px 20px rgba(245, 101, 101, 0.1);
            position: relative;
            overflow: hidden;
        }

        .evaluation-box::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, var(--error-color), #fc8181);
        }

        /* === コミットカード === */
        .commit-card {
            background: white;
            border: 1px solid var(--neutral-200);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 0.75rem 0;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            position: relative;
        }

        .commit-card:hover {
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
            transform: translateY(-1px);
        }

        .commit-hash {
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            color: var(--neutral-600);
            font-size: 0.85rem;
            background: var(--neutral-100);
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
        }

        /* === タグとブランチ === */
        .branch-tag {
            display: inline-block;
            background: linear-gradient(135deg, var(--success-color) 0%, #38a169 100%);
            color: white;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-right: 0.5rem;
            box-shadow: 0 2px 8px rgba(72, 187, 120, 0.3);
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
        }

        .diff-line-added {
            background: rgba(72, 187, 120, 0.2);
            color: #9ae6b4;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            margin: 0.1rem 0;
        }

        .diff-line-removed {
            background: rgba(245, 101, 101, 0.2);
            color: #feb2b2;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            margin: 0.1rem 0;
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

        /* === サイドバーの改善 === */
        .css-1d391kg {
            background: linear-gradient(180deg, #f8faff 0%, white 100%);
        }

        /* === セレクトボックスの改善 === */
        .stSelectbox > div > div {
            border-radius: 10px;
            border: 2px solid var(--neutral-200);
            transition: all 0.3s ease;
        }

        .stSelectbox > div > div:focus-within {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        /* === テキストエリアの改善 === */
        .stTextArea > div > div > textarea {
            border-radius: 10px;
            border: 2px solid var(--neutral-200);
            transition: all 0.3s ease;
        }

        .stTextArea > div > div > textarea:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        /* === タブコンテンツの改善 === */
        .stTabs [data-baseweb="tab-panel"] {
            padding-top: 1.5rem;
        }

        /* === タブリストのコンテナ === */
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
            padding: 0 1rem;
            margin-bottom: 1rem;
            background: transparent;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 12px;
            background: var(--neutral-100);
            border: none;
            font-weight: 600;
            font-size: 1rem;
            padding: 0.75rem 1.5rem !important;
            min-width: 120px;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            flex-grow: 1;
            text-align: center;
        }

        .stTabs [data-baseweb="tab"]:hover {
            background: var(--neutral-200);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }

        .stTabs [aria-selected="true"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }

        /* === アラートとメッセージ === */
        .stAlert {
            border-radius: 12px;
            border: none;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }

        /* === ヘッダーの改善 === */
        .main-header {
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            color: white;
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 8px 30px rgba(102, 126, 234, 0.2);
        }

        .header-stats {
            display: flex;
            justify-content: space-around;
            margin-top: 1rem;
        }

        .header-stat {
            text-align: center;
        }

        .header-stat h3 {
            margin: 0;
            font-size: 1.5rem;
            font-weight: 700;
        }

        .header-stat p {
            margin: 0;
            opacity: 0.9;
            font-size: 0.9rem;
        }

        /* === レスポンシブデザイン === */
        @media (max-width: 768px) {
            .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
            
            .modern-card, .metric-card, .commit-card {
                margin: 0.5rem 0;
            }
            
            .header-stats {
                flex-direction: column;
                gap: 1rem;
            }
        }

        /* === アニメーション === */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .fade-in-up {
            animation: fadeInUp 0.6s ease-out;
        }

        /* === ローディング状態 === */
        .stSpinner > div {
            border-color: var(--primary-color) transparent transparent transparent;
        }

        /* === フォーカス状態の改善 === */
        *:focus {
            outline: none;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
        }
    </style>
    """, unsafe_allow_html=True)


def get_response_box_html(content: str, border_color: str = None) -> str:
    """モダンなレスポンスボックスのHTMLを生成"""
    import html
    escaped_content = html.escape(content).replace('\n', '<br>')
    return f"""
    <div class="response-box fade-in-up">
        <p style="line-height: 1.6; margin: 0; font-size: 1rem;">{escaped_content}</p>
    </div>
    """


def get_evaluation_box_html(content: str) -> str:
    """モダンな評価ボックスのHTMLを生成"""
    import html
    escaped_content = html.escape(content).replace('\n', '<br>')
    return f"""
    <div class="evaluation-box fade-in-up">
        <p style="line-height: 1.6; margin: 0; font-size: 1rem;">{escaped_content}</p>
    </div>
    """


def get_metric_card_html(title: str, value: str, subtitle: str = "") -> str:
    """モダンなメトリクスカードのHTMLを生成"""
    subtitle_html = f'<p style="color: var(--neutral-600); margin: 0.5rem 0 0 0; font-size: 0.85rem;">{subtitle}</p>' if subtitle else ""
    return f"""
    <div class="metric-card">
        <h4>{title}</h4>
        <h2>{value}</h2>
        {subtitle_html}
    </div>
    """


def get_header_html(title: str, stats: dict) -> str:
    """メインヘッダーのHTMLを生成"""
    return f"""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 2.5rem; font-weight: 800;">{title}</h1>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 1.1rem;">Git風バージョン管理でプロンプトを進化させよう</p>
        <div class="header-stats">
            <div class="header-stat">
                <h3>{stats.get('total_executions', 0)}</h3>
                <p>実行記録</p>
            </div>
            <div class="header-stat">
                <h3>{stats.get('total_branches', 0)}</h3>
                <p>ブランチ</p>
            </div>
            <div class="header-stat">
                <h3>${stats.get('total_cost', 0):.4f}</h3>
                <p>総コスト</p>
            </div>
        </div>
    </div>
    """


def get_commit_card_style():
    """コミットカードのスタイルクラス名を返す"""
    return "commit-card"


def get_branch_tag_html(branch_name: str) -> str:
    """ブランチタグのHTMLを生成"""
    return f'<span class="branch-tag">{branch_name}</span>'