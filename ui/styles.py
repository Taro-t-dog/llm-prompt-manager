# ============================================
# ui/styles.py (ワークフロー機能対応拡張版)
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

        /* 🆕 ワークフロー専用ボタン */
        .workflow-button {
            background: linear-gradient(135deg, var(--workflow-color) 0%, #319795 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 1rem 2rem;
            font-weight: 600;
            font-size: 1rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(56, 178, 172, 0.2);
            width: 100%;
            text-align: center;
        }
        
        .workflow-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(56, 178, 172, 0.3);
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

        /* 🆕 ワークフローカード */
        .workflow-card {
            background: linear-gradient(135deg, white 0%, #f0fdfa 100%);
            border: 1px solid rgba(56, 178, 172, 0.2);
            border-radius: 16px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 4px 15px rgba(56, 178, 172, 0.1);
            transition: all 0.3s ease;
            position: relative;
        }

        .workflow-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--workflow-color), #319795);
            border-radius: 16px 16px 0 0;
        }

        .workflow-card:hover {
            box-shadow: 0 8px 25px rgba(56, 178, 172, 0.15);
            transform: translateY(-2px);
            border-color: var(--workflow-color);
        }

        /* 🆕 テンプレートカード */
        .template-card {
            background: linear-gradient(135deg, #f8faff 0%, #f1f5ff 100%);
            border: 1px solid var(--neutral-200);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 0.75rem 0;
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .template-card:hover {
            background: linear-gradient(135deg, #e6f3ff 0%, #ddeeff 100%);
            border-color: var(--primary-color);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.1);
            transform: translateY(-1px);
        }

        .template-card h4 {
            margin: 0 0 0.5rem 0;
            color: var(--neutral-800);
            font-size: 1.1rem;
        }

        .template-card p {
            margin: 0 0 0.75rem 0;
            color: var(--neutral-600);
            font-size: 0.9rem;
            line-height: 1.4;
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

        /* 🆕 ワークフロー進捗カード */
        .progress-card {
            background: linear-gradient(135deg, #f0fdfa 0%, white 100%);
            border: 1px solid rgba(56, 178, 172, 0.3);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 2px 10px rgba(56, 178, 172, 0.1);
        }

        .progress-step {
            display: flex;
            align-items: center;
            padding: 0.75rem;
            margin: 0.5rem 0;
            border-radius: 8px;
            transition: all 0.3s ease;
        }

        .progress-step.completed {
            background: rgba(72, 187, 120, 0.1);
            color: var(--success-color);
        }

        .progress-step.running {
            background: rgba(56, 178, 172, 0.1);
            color: var(--workflow-color);
            animation: pulse 2s infinite;
        }

        .progress-step.pending {
            background: rgba(113, 128, 150, 0.1);
            color: var(--neutral-600);
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
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

        /* 🆕 ワークフロー結果ボックス */
        .workflow-result-box {
            background: linear-gradient(135deg, #f0fdfa 0%, #e6fffa 100%);
            color: var(--neutral-800);
            padding: 2rem;
            border-radius: 16px;
            border-left: 4px solid var(--workflow-color);
            margin: 1rem 0;
            box-shadow: 0 6px 20px rgba(56, 178, 172, 0.1);
            position: relative;
            overflow: hidden;
        }

        .workflow-result-box::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, var(--workflow-color), #319795);
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

        /* 🆕 ワークフロータグ */
        .workflow-tag {
            display: inline-block;
            background: linear-gradient(135deg, var(--workflow-color) 0%, #319795 100%);
            color: white;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-right: 0.5rem;
            box-shadow: 0 2px 8px rgba(56, 178, 172, 0.3);
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

        /* 🆕 変数置換プレビュー */
        .variable-preview {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 1rem;
            margin: 0.5rem 0;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            font-size: 0.9rem;
        }

        .variable-highlight {
            background: rgba(102, 126, 234, 0.1);
            color: var(--primary-color);
            padding: 0.1rem 0.3rem;
            border-radius: 4px;
            font-weight: 600;
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

        /* 🆕 ワークフロータブ専用スタイル */
        .workflow-tab [aria-selected="true"] {
            background: linear-gradient(135deg, var(--workflow-color) 0%, #319795 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(56, 178, 172, 0.3);
        }

        /* === アラートとメッセージ === */
        .stAlert {
            border-radius: 12px;
            border: none;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }

        /* 🆕 ワークフロー成功メッセージ */
        .workflow-success {
            background: linear-gradient(135deg, #f0fff4 0%, #e6fffa 100%);
            border: 1px solid rgba(72, 187, 120, 0.3);
            color: var(--success-color);
            padding: 1rem;
            border-radius: 12px;
            margin: 1rem 0;
        }

        /* 🆕 ワークフローエラーメッセージ */
        .workflow-error {
            background: linear-gradient(135deg, #fff5f5 0%, #fed7d7 100%);
            border: 1px solid rgba(245, 101, 101, 0.3);
            color: var(--error-color);
            padding: 1rem;
            border-radius: 12px;
            margin: 1rem 0;
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

        /* 🆕 エクスパンダーの改善 */
        .streamlit-expanderHeader {
            background: var(--neutral-100);
            border-radius: 8px;
            padding: 0.75rem;
            transition: all 0.3s ease;
        }

        .streamlit-expanderHeader:hover {
            background: var(--neutral-200);
        }

        /* 🆕 プログレスバーの改善 */
        .stProgress > div > div > div {
            background: linear-gradient(90deg, var(--workflow-color), #319795);
            border-radius: 10px;
        }

        /* 🆕 ファイルアップローダーの改善 */
        .stFileUploader {
            border: 2px dashed var(--neutral-300);
            border-radius: 12px;
            padding: 2rem;
            text-align: center;
            transition: all 0.3s ease;
        }

        .stFileUploader:hover {
            border-color: var(--primary-color);
            background: rgba(102, 126, 234, 0.05);
        }

        /* 🆕 コードブロックの改善 */
        .stCode {
            border-radius: 8px;
            border: 1px solid var(--neutral-200);
        }

        /* === レスポンシブデザイン === */
        @media (max-width: 768px) {
            .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
            
            .modern-card, .metric-card, .commit-card, .workflow-card, .template-card {
                margin: 0.5rem 0;
            }
            
            .header-stats {
                flex-direction: column;
                gap: 1rem;
            }
            
            .workflow-button {
                padding: 0.75rem 1rem;
                font-size: 0.9rem;
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

        /* 🆕 ワークフロー専用アニメーション */
        @keyframes slideInFromLeft {
            from {
                opacity: 0;
                transform: translateX(-30px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        .workflow-slide-in {
            animation: slideInFromLeft 0.5s ease-out;
        }

        @keyframes shimmer {
            0% {
                background-position: -200px 0;
            }
            100% {
                background-position: calc(200px + 100%) 0;
            }
        }

        .workflow-loading {
            background: linear-gradient(90deg, #f0f2f5 0px, #e6f3ff 40px, #f0f2f5 80px);
            background-size: 200px;
            animation: shimmer 1.5s infinite;
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

        /* 🆕 ダークモード対応（オプション） */
        @media (prefers-color-scheme: dark) {
            :root {
                --neutral-100: #2d3748;
                --neutral-200: #4a5568;
                --neutral-300: #718096;
                --neutral-600: #e2e8f0;
                --neutral-700: #edf2f7;
                --neutral-800: #f7fafc;
                --neutral-900: #ffffff;
            }
            
            .modern-card, .workflow-card, .template-card {
                background: var(--neutral-100);
                border-color: var(--neutral-200);
            }
            
            .response-box, .evaluation-box, .workflow-result-box {
                color: var(--neutral-800);
            }
        }

        /* 🆕 アクセシビリティ改善 */
        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }

        /* 高コントラストモード対応 */
        @media (prefers-contrast: high) {
            .modern-card, .workflow-card, .template-card {
                border-width: 2px;
            }
            
            .stButton > button, .workflow-button {
                border: 2px solid transparent;
            }
            
            .stButton > button:focus, .workflow-button:focus {
                border-color: var(--neutral-900);
            }
        }

        /* 動作軽減モード対応 */
        @media (prefers-reduced-motion: reduce) {
            * {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
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


def get_workflow_result_box_html(content: str) -> str:
    """🆕 ワークフロー結果ボックスのHTMLを生成"""
    import html
    escaped_content = html.escape(content).replace('\n', '<br>')
    return f"""
    <div class="workflow-result-box fade-in-up">
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


def get_workflow_metric_card_html(title: str, value: str, subtitle: str = "", icon: str = "🔄") -> str:
    """🆕 ワークフロー専用メトリクスカードのHTMLを生成"""
    subtitle_html = f'<p style="color: var(--neutral-600); margin: 0.5rem 0 0 0; font-size: 0.85rem;">{subtitle}</p>' if subtitle else ""
    return f"""
    <div class="metric-card" style="border-left: 4px solid var(--workflow-color);">
        <div style="display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
            <span style="font-size: 1.2rem;">{icon}</span>
            <h4 style="margin: 0;">{title}</h4>
        </div>
        <h2 style="color: var(--workflow-color);">{value}</h2>
        {subtitle_html}
    </div>
    """


def format_cost_display(cost: float) -> str:
    """🆕 コスト表示の統一フォーマット関数"""
    if cost == 0:
        return "$0"
    elif cost < 0.000001:
        return f"${cost:.8f}"  # 非常に小さい値は8桁
    elif cost < 0.0001:
        return f"${cost:.6f}"  # 小さい値は6桁
    elif cost < 0.01:
        return f"${cost:.4f}"  # 中程度の値は4桁
    else:
        return f"${cost:.2f}"  # 大きい値は2桁


def get_header_html(title: str, stats: dict) -> str:
    """メインヘッダーのHTMLを生成（ワークフロー対応）"""
    workflow_stat = ""
    if stats.get('workflow_count', 0) > 0:
        workflow_stat = f"""
        <div class="header-stat">
            <h3>{stats.get('workflow_count', 0)}</h3>
            <p>ワークフロー</p>
        </div>
        """
    
    # 🆕 統一されたコスト表示を使用
    cost_display = format_cost_display(stats.get('total_cost', 0))
    
    return f"""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 2.5rem; font-weight: 800;">{title}</h1>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 1.1rem;">単発処理とワークフロー処理でLLMを最大活用</p>
        <div class="header-stats">
            <div class="header-stat">
                <h3>{stats.get('total_executions', 0)}</h3>
                <p>実行記録</p>
            </div>
            <div class="header-stat">
                <h3>{stats.get('total_branches', 0)}</h3>
                <p>ブランチ</p>
            </div>
            {workflow_stat}
            <div class="header-stat">
                <h3>{cost_display}</h3>
                <p>総コスト</p>
            </div>
        </div>
    </div>
    """


def get_commit_card_style():
    """コミットカードのスタイルクラス名を返す"""
    return "commit-card"


def get_workflow_card_style():
    """🆕 ワークフローカードのスタイルクラス名を返す"""
    return "workflow-card"


def get_branch_tag_html(branch_name: str) -> str:
    """ブランチタグのHTMLを生成"""
    return f'<span class="branch-tag">{branch_name}</span>'


def get_workflow_tag_html(workflow_name: str) -> str:
    """🆕 ワークフロータグのHTMLを生成"""
    return f'<span class="workflow-tag">🔄 {workflow_name}</span>'


def get_progress_step_html(step_name: str, status: str = "pending") -> str:
    """🆕 進捗ステップのHTMLを生成"""
    icons = {
        "completed": "✅",
        "running": "🔄", 
        "pending": "⏸️",
        "failed": "❌"
    }
    
    icon = icons.get(status, "⏸️")
    
    return f"""
    <div class="progress-step {status}">
        <span style="margin-right: 0.5rem; font-size: 1.1rem;">{icon}</span>
        <span>{step_name}</span>
    </div>
    """


def get_variable_preview_html(template: str, variables: dict) -> str:
    """🆕 変数置換プレビューのHTMLを生成"""
    import re
    
    preview_template = template
    for var_name, var_value in variables.items():
        pattern = f"{{{var_name}}}"
        if pattern in preview_template:
            highlighted_var = f'<span class="variable-highlight">{var_value[:50]}...</span>' if len(str(var_value)) > 50 else f'<span class="variable-highlight">{var_value}</span>'
            preview_template = preview_template.replace(pattern, highlighted_var)
    
    return f"""
    <div class="variable-preview">
        {preview_template}
    </div>
    """


def get_error_display_html(error_type: str, error_message: str, suggestions: list) -> str:
    """🆕 エラー表示のHTMLを生成"""
    suggestions_html = ""
    for i, suggestion in enumerate(suggestions, 1):
        suggestions_html += f"<li>{suggestion}</li>"
    
    return f"""
    <div class="workflow-error">
        <h4 style="margin: 0 0 0.5rem 0; color: var(--error-color);">🚨 {error_type}</h4>
        <p style="margin: 0 0 1rem 0; font-family: monospace; font-size: 0.9rem;">{error_message}</p>
        <div>
            <strong>💡 推奨対処法:</strong>
            <ol style="margin: 0.5rem 0 0 1rem; padding: 0;">
                {suggestions_html}
            </ol>
        </div>
    </div>
    """


def get_success_message_html(message: str, details: str = "") -> str:
    """🆕 成功メッセージのHTMLを生成"""
    details_html = f'<p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; opacity: 0.8;">{details}</p>' if details else ""
    
    return f"""
    <div class="workflow-success">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.2rem;">✅</span>
            <strong>{message}</strong>
        </div>
        {details_html}
    </div>
    """