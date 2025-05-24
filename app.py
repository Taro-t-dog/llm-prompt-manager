import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import datetime
from typing import Dict, List, Any
import re
import hashlib
import html
import difflib

# ページ設定
st.set_page_config(
    page_title="LLMプロンプト自動評価システム",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem;
        border-radius: 8px;
        font-weight: bold;
        font-size: 1.1rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        border: 1px solid #e0e0e0;
    }
    .response-box {
        background: #ffffff;
        color: #2c3e50;
        padding: 2rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .evaluation-box {
        background: #ffffff;
        color: #2c3e50;
        padding: 2rem;
        border-radius: 10px;
        border-left: 4px solid #f5576c;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .commit-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .commit-hash {
        font-family: monospace;
        color: #6c757d;
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
    .diff-added {
        background: #d4edda;
        color: #155724;
        padding: 0.2rem;
    }
    .diff-removed {
        background: #f8d7da;
        color: #721c24;
        padding: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)

# セッション状態の初期化
if 'evaluation_history' not in st.session_state:
    st.session_state.evaluation_history = []
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'current_branch' not in st.session_state:
    st.session_state.current_branch = "main"
if 'branches' not in st.session_state:
    st.session_state.branches = {"main": []}
if 'tags' not in st.session_state:
    st.session_state.tags = {}
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = "gemini-2.0-flash-exp"

# モデル設定辞書
MODEL_CONFIGS = {
    "gemini-2.0-flash-exp": {
        "name": "Gemini 2.0 Flash",
        "model_id": "gemini-2.0-flash-exp",
        "input_cost_per_token": 0.0000001,  # $0.10 per 1M tokens
        "output_cost_per_token": 0.0000004,  # $0.40 per 1M tokens
        "description": "Fast, cost-efficient model with 1M context window",
        "context_window": 1000000,
        "free_tier": True
    },
    "gemini-1.5-flash": {
        "name": "Gemini 1.5 Flash",
        "model_id": "gemini-1.5-flash",
        "input_cost_per_token": 0.0,  # Free
        "output_cost_per_token": 0.0,  # Free
        "description": "Free model with generous rate limits",
        "context_window": 1000000,
        "free_tier": True
    },
    "gemini-1.5-pro": {
        "name": "Gemini 1.5 Pro",
        "model_id": "gemini-1.5-pro",
        "input_cost_per_token": 0.00000125,  # $1.25 per 1M tokens
        "output_cost_per_token": 0.000005,    # $5.00 per 1M tokens
        "description": "High-performance model for complex tasks",
        "context_window": 2000000,
        "free_tier": True
    },
    "gemini-2.5-pro": {
        "name": "Gemini 2.5 Pro",
        "model_id": "gemini-2.5-pro",
        "input_cost_per_token": 0.00000125,  # $1.25 per 1M tokens (up to 200K)
        "output_cost_per_token": 0.00001,     # $10.00 per 1M tokens
        "description": "Most advanced reasoning model",
        "context_window": 2000000,
        "free_tier": False
    }
}

class GeminiEvaluator:
    def __init__(self, api_key: str, model_config: dict):
        self.api_key = api_key
        self.model_config = model_config
        self.token_cache = {}  # トークン数キャッシュ
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_config['model_id'])
        
        # count_tokens API利用可能性をチェック
        try:
            # テスト呼び出し（正しい引数形式）
            test_result = self.model.count_tokens(["test"])
            self.use_accurate_counting = True
            st.success("✅ 正確なトークン数算出APIが利用可能です！")
        except Exception as e:
            self.use_accurate_counting = False
            error_message = str(e)
            
            # エラータイプ別の対応メッセージ
            if "API_KEY_INVALID" in error_message or "API key expired" in error_message:
                st.error("🔑 **APIキーが無効または期限切れです**")
                st.markdown("""
                **対処方法:**
                1. [Google AI Studio](https://makersuite.google.com/app/apikey) でAPIキーを更新
                2. 新しいAPIキーをサイドバーで入力
                3. ページを再読み込み
                """)
            elif "PERMISSION_DENIED" in error_message:
                st.error("🚫 **APIアクセス権限がありません**")
                st.info("Google AI Studioでアカウント設定を確認してください")
            elif "QUOTA_EXCEEDED" in error_message:
                st.error("📊 **API使用量上限に達しました**")
                st.info("Google AI Studioで使用量を確認するか、時間をおいて再試行してください")
            else:
                st.warning(f"⚠️ 正確なトークン数算出APIが利用できません。改良された概算モードで動作します。")
                st.info(f"詳細エラー: {error_message}")
    
    def count_tokens_accurate(self, text: str) -> int:
        """公式APIを使用した正確なトークン数算出"""
        if not self.use_accurate_counting:
            return self.count_tokens_improved(text)
        
        # キャッシュチェック
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        cache_key = f"{self.model_config['model_id']}:{text_hash}"
        
        if cache_key in self.token_cache:
            return self.token_cache[cache_key]
        
        try:
            # 正しい構文：リスト形式で渡す
            result = self.model.count_tokens([text])
            token_count = result.total_tokens
            
            # キャッシュに保存（メモリ節約のため最新100件のみ）
            if len(self.token_cache) > 100:
                # 古いエントリを削除
                oldest_key = next(iter(self.token_cache))
                del self.token_cache[oldest_key]
            
            self.token_cache[cache_key] = token_count
            return token_count
            
        except Exception as e:
            # 実行時エラーは警告のみ（初期化時ほど重要ではない）
            if not hasattr(self, '_runtime_warning_shown'):
                st.warning(f"正確なトークン数取得に失敗。改良された概算値を使用します。")
                self._runtime_warning_shown = True
            return self.count_tokens_improved(text)
    
    def count_tokens_improved(self, text: str) -> int:
        """改良された概算方式（実際のトークナイザーに近い精度）"""
        
        # キャッシュチェック
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        cache_key = f"improved:{text_hash}"
        
        if cache_key in self.token_cache:
            return self.token_cache[cache_key]
        
        # Gemini公式の近似式: 1トークン ≈ 4文字
        # しかし言語や内容によって調整が必要
        
        char_count = len(text)
        
        # 言語別調整
        japanese_chars = len(re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text))
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        punctuation = len(re.findall(r'[^\w\s]', text))
        
        # 改良された計算式
        if japanese_chars > char_count * 0.3:  # 日本語中心
            # 日本語：1文字 ≈ 0.8-1.2トークン
            base_tokens = japanese_chars * 1.0
            base_tokens += english_words * 1.2  # 英単語
            base_tokens += punctuation * 0.5    # 記号
        else:  # 英語中心
            # 英語：1単語 ≈ 1.3トークン、1文字 ≈ 0.25トークン
            base_tokens = english_words * 1.3
            base_tokens += (char_count - english_words * 5) * 0.25  # 残りの文字
            base_tokens += punctuation * 0.5
        
        # 最小値保証とキャッシュ
        token_count = max(1, int(base_tokens))
        
        # キャッシュ管理
        if len(self.token_cache) > 100:
            oldest_key = next(iter(self.token_cache))
            del self.token_cache[oldest_key]
        
        self.token_cache[cache_key] = token_count
        return token_count
    
    def count_tokens_fallback(self, text: str) -> int:
        """従来の簡易計算（フォールバック用）"""
        return len(text.split()) + len(re.findall(r'[^\w\s]', text))
    
    def count_tokens(self, text: str) -> int:
        """テキストのトークン数を算出（メイン関数）"""
        return self.count_tokens_accurate(text)
    
    def execute_prompt(self, prompt: str) -> Dict[str, Any]:
        """プロンプトを実行し、結果とコスト情報を返す"""
        try:
            # 正確なトークン数算出
            input_tokens = self.count_tokens(prompt)
            
            response = self.model.generate_content(prompt)
            
            # 出力トークン数も正確に算出
            output_tokens = self.count_tokens(response.text)
            
            # 動的料金計算
            input_cost = input_tokens * self.model_config['input_cost_per_token']
            output_cost = output_tokens * self.model_config['output_cost_per_token']
            total_cost = input_cost + output_cost
            
            return {
                'response': response.text,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens,
                'cost_usd': total_cost,
                'model_name': self.model_config['name'],
                'model_id': self.model_config['model_id'],
                'token_accuracy': 'API-正確' if self.use_accurate_counting else '概算',
                'success': True,
                'error': None
            }
        except Exception as e:
            return {
                'response': None,
                'input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0,
                'cost_usd': 0,
                'model_name': self.model_config['name'],
                'model_id': self.model_config['model_id'],
                'token_accuracy': 'エラー',
                'success': False,
                'error': str(e)
            }
    
    def evaluate_response(self, original_prompt: str, response: str, evaluation_criteria: str) -> Dict[str, Any]:
        """レスポンスを評価基準に基づいて評価"""
        evaluation_prompt = f"""
以下の内容を評価してください：

【元のプロンプト】
{original_prompt}

【LLMの回答】
{response}

【評価基準】
{evaluation_criteria}

【評価指示】
上記の評価基準に基づいて、LLMの回答を詳細に評価してください。
以下の形式で回答してください：

1. 総合評価: [1-10点の数値評価]
2. 各項目の評価: [評価基準の各項目について詳細評価]
3. 良い点: [具体的な良い点]
4. 改善点: [具体的な改善すべき点]
5. 総合コメント: [全体的な評価コメント]
"""
        
        return self.execute_prompt(evaluation_prompt)

def format_timestamp(timestamp):
    """タイムスタンプをフォーマット（文字列・datetime両対応）"""
    if isinstance(timestamp, str):
        # 文字列の場合はそのまま返す（JSONから読み込んだ場合）
        if 'T' in timestamp:
            # ISO形式の場合は見やすく変換
            try:
                dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                return timestamp[:19]  # 最初の19文字を取得
        return timestamp
    else:
        # datetime オブジェクトの場合
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')

def generate_commit_hash(content: str) -> str:
    """コンテンツからコミットハッシュを生成"""
    return hashlib.md5(content.encode()).hexdigest()[:8]

def get_diff_html(old_text: str, new_text: str) -> str:
    """2つのテキストの差分をHTMLで表示"""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))
    
    if not diff:
        return "変更なし"
    
    html_diff = []
    for line in diff[3:]:  # ヘッダー行をスキップ
        if line.startswith('+'):
            html_diff.append(f'<div class="diff-added">+ {html.escape(line[1:])}</div>')
        elif line.startswith('-'):
            html_diff.append(f'<div class="diff-removed">- {html.escape(line[1:])}</div>')
        else:
            html_diff.append(f'<div>{html.escape(line)}</div>')
    
    return ''.join(html_diff)

def create_commit(data: Dict[str, Any], execution_memo: str) -> Dict[str, Any]:
    """新しい実行記録を作成"""
    commit_hash = generate_commit_hash(str(data))
    
    execution_record = {
        **data,
        'commit_hash': commit_hash,
        'commit_message': execution_memo,
        'branch': st.session_state.current_branch,
        'parent_hash': None
    }
    
    # 親記録のハッシュを設定
    current_branch_executions = st.session_state.branches[st.session_state.current_branch]
    if current_branch_executions:
        execution_record['parent_hash'] = current_branch_executions[-1]['commit_hash']
    
    return execution_record

def main():
    # メインタイトル
    st.title("🚀 LLM プロンプト Git 管理システム")
    st.markdown("Git風のバージョン管理でプロンプトの進化を追跡しましょう！")
    
    # Git情報表示
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"**📍 現在のブランチ:** `{st.session_state.current_branch}`")
    with col2:
        total_executions = len(st.session_state.evaluation_history)
        st.markdown(f"**📝 総実行数:** {total_executions}")
    with col3:
        total_branches = len(st.session_state.branches)
        st.markdown(f"**🌿 ブランチ数:** {total_branches}")
    
    # Git情報表示の下に説明を追加
    st.info("💡 Git風の履歴管理でプロンプトの改善過程を追跡できます。実行メモで変更理由を記録し、ブランチで異なるアプローチを並行テストしましょう。")
    
    st.markdown("---")
    
    # サイドバー
    with st.sidebar:
        st.header("⚙️ 設定")
        
        api_key = st.text_input(
            "🔑 Gemini API Key", 
            value=st.session_state.api_key,
            type="password",
            help="Google AI StudioでAPIキーを取得してください"
        )
        
        if api_key != st.session_state.api_key:
            st.session_state.api_key = api_key
        
        if not api_key:
            st.error("⚠️ APIキーを入力してください")
            st.stop()
        
        # モデル選択
        st.subheader("🤖 モデル選択")
        
        model_options = list(MODEL_CONFIGS.keys())
        
        selected_model_index = model_options.index(st.session_state.selected_model) if st.session_state.selected_model in model_options else 0
        
        selected_model = st.selectbox(
            "使用するモデル",
            model_options,
            format_func=lambda x: MODEL_CONFIGS[x]['name'],
            index=selected_model_index
        )
        
        if selected_model != st.session_state.selected_model:
            st.session_state.selected_model = selected_model
        
        # 選択されたモデルの詳細情報
        current_model = MODEL_CONFIGS[st.session_state.selected_model]
        
        st.markdown(f"""
        **📋 モデル詳細:**
        - **名前**: {current_model['name']}
        - **説明**: {current_model['description']}
        - **コンテキスト**: {current_model['context_window']:,} tokens
        - **無料枠**: {'✅ あり' if current_model['free_tier'] else '❌ なし'}
        """)
        
        # 料金情報
        if current_model['input_cost_per_token'] == 0 and current_model['output_cost_per_token'] == 0:
            st.success("💰 **完全無料!**")
        else:
            st.markdown(f"""
            **💰 料金:**
            - 入力: ${current_model['input_cost_per_token'] * 1000000:.2f}/1M tokens
            - 出力: ${current_model['output_cost_per_token'] * 1000000:.2f}/1M tokens
            """)
        
        st.markdown("---")
        
        # データ管理
        st.header("💾 データ管理")
        
        # 履歴保存
        if st.session_state.evaluation_history:
            history_data = {
                'evaluation_history': st.session_state.evaluation_history,
                'branches': st.session_state.branches,
                'tags': st.session_state.tags,
                'current_branch': st.session_state.current_branch,
                'export_timestamp': datetime.datetime.now().isoformat()
            }
            
            history_json = json.dumps(history_data, default=str, ensure_ascii=False, indent=2)
            
            st.download_button(
                label="💾 履歴をローカル保存",
                data=history_json,
                file_name=f"prompt_history_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                help="実行履歴をJSONファイルとしてローカルに保存します"
            )
        
        # 履歴読み込み
        st.subheader("📂 履歴読み込み")
        
        uploaded_file = st.file_uploader(
            "履歴ファイルを選択",
            type=["json", "csv"],
            help="JSONファイル（完全復元）またはCSVファイル（基本データのみ）を読み込みます"
        )
        
        if uploaded_file is not None:
            file_extension = uploaded_file.name.split('.')[-1].lower()
            
            try:
                if file_extension == 'json':
                    # JSON読み込み
                    history_data = json.load(uploaded_file)
                    
                    if st.button("📥 JSON履歴を復元"):
                        # データを復元（タイムスタンプはそのまま文字列として保持）
                        st.session_state.evaluation_history = history_data.get('evaluation_history', [])
                        st.session_state.branches = history_data.get('branches', {"main": []})
                        st.session_state.tags = history_data.get('tags', {})
                        st.session_state.current_branch = history_data.get('current_branch', 'main')
                        
                        st.success("✅ JSON履歴を復元しました！")
                        st.rerun()
                    
                    # プレビュー情報
                    total_records = len(history_data.get('evaluation_history', []))
                    export_time = history_data.get('export_timestamp', 'Unknown')
                    if 'T' in str(export_time):
                        export_time = format_timestamp(export_time)
                    st.info(f"📊 {total_records}件の記録\n📅 {export_time}")
                
                elif file_extension == 'csv':
                    # CSV読み込み
                    df = pd.read_csv(uploaded_file)
                    
                    if st.button("📥 CSV履歴をインポート"):
                        # CSVデータを内部形式に変換
                        imported_records = []
                        current_branch = st.session_state.current_branch
                        
                        for _, row in df.iterrows():
                            record = {
                                'timestamp': row.get('timestamp', datetime.datetime.now().isoformat()),
                                'execution_mode': row.get('execution_mode', '単一プロンプト'),
                                'prompt_template': row.get('prompt_template', None),
                                'user_input': row.get('user_input', None),
                                'final_prompt': row.get('final_prompt', ''),
                                'criteria': row.get('criteria', ''),
                                'response': row.get('response', ''),
                                'evaluation': row.get('evaluation', ''),
                                'execution_tokens': int(row.get('execution_tokens', 0)),
                                'evaluation_tokens': int(row.get('evaluation_tokens', 0)),
                                'execution_cost': float(row.get('execution_cost', 0.0)),
                                'evaluation_cost': float(row.get('evaluation_cost', 0.0)),
                                'total_cost': float(row.get('total_cost', 0.0)),
                                'commit_hash': row.get('commit_hash', generate_commit_hash(str(row.to_dict()))),
                                'commit_message': row.get('commit_message', 'CSVインポート'),
                                'branch': row.get('branch', current_branch),
                                'parent_hash': row.get('parent_hash', None)
                            }
                            imported_records.append(record)
                        
                        # 既存データに追加
                        st.session_state.evaluation_history.extend(imported_records)
                        
                        # ブランチ別に整理
                        for record in imported_records:
                            branch_name = record['branch']
                            if branch_name not in st.session_state.branches:
                                st.session_state.branches[branch_name] = []
                            st.session_state.branches[branch_name].append(record)
                        
                        st.success(f"✅ CSV履歴をインポートしました！（{len(imported_records)}件）")
                        st.rerun()
                    
                    # CSVプレビュー情報
                    st.info(f"📊 {len(df)}件の記録\n📋 列数: {len(df.columns)}")
                    
                    # データプレビュー
                    if st.checkbox("🔍 CSVデータをプレビュー"):
                        st.dataframe(df.head(), use_container_width=True)
                
            except Exception as e:
                st.error(f"❌ ファイル読み込みエラー: {str(e)}")
        
        # データクリア
        if st.session_state.evaluation_history:
            st.markdown("---")
            if st.button("🗑️ 全データクリア", type="secondary"):
                if st.button("⚠️ 本当にクリアしますか？", type="secondary"):
                    st.session_state.evaluation_history = []
                    st.session_state.branches = {"main": []}
                    st.session_state.tags = {}
                    st.session_state.current_branch = "main"
                    st.success("✅ データをクリアしました")
                    st.rerun()
        
        st.markdown("---")
        
        # Git操作
        st.header("🌿 ブランチ管理")
        
        # 現在のブランチ選択
        available_branches = list(st.session_state.branches.keys())
        current_branch_index = available_branches.index(st.session_state.current_branch)
        
        selected_branch = st.selectbox(
            "ブランチを選択",
            available_branches,
            index=current_branch_index
        )
        
        if selected_branch != st.session_state.current_branch:
            st.session_state.current_branch = selected_branch
            st.rerun()
        
        # 新しいブランチ作成
        new_branch_name = st.text_input("新しいブランチ名")
        if st.button("🌱 ブランチ作成"):
            if new_branch_name and new_branch_name not in st.session_state.branches:
                # 現在のブランチからコピー
                st.session_state.branches[new_branch_name] = st.session_state.branches[st.session_state.current_branch].copy()
                st.session_state.current_branch = new_branch_name  # 新しいブランチに自動切り替え
                st.success(f"ブランチ '{new_branch_name}' を作成し、切り替えました")
                st.rerun()  # 画面を更新
            elif new_branch_name in st.session_state.branches:
                st.error("同名のブランチが既に存在します")
            elif not new_branch_name:
                st.warning("ブランチ名を入力してください")
        
        st.markdown("---")
        
        # タグ管理
        st.header("🏷️ タグ管理")
        
        if st.session_state.evaluation_history:
            execution_options = [f"{execution['commit_hash']} - {execution.get('commit_message', 'メモなし')}" 
                            for execution in st.session_state.evaluation_history]
            
            selected_execution_idx = st.selectbox("タグを付ける実行記録", 
                                             range(len(execution_options)), 
                                             format_func=lambda x: execution_options[x])
            
            tag_name = st.text_input("タグ名")
            if st.button("🏷️ タグ作成"):
                if tag_name and tag_name not in st.session_state.tags:
                    exec_hash = st.session_state.evaluation_history[selected_execution_idx]['commit_hash']
                    st.session_state.tags[tag_name] = exec_hash
                    st.success(f"タグ '{tag_name}' を作成しました")
                elif tag_name in st.session_state.tags:
                    st.error("同名のタグが既に存在します")
        
        st.markdown("---")
        
        # 統計情報
        if st.session_state.evaluation_history:
            st.header("📊 統計情報")
            
            branch_executions = st.session_state.branches[st.session_state.current_branch]
            total_cost = sum([execution['execution_cost'] for execution in branch_executions])  # 実行コストのみ
            total_tokens = sum([execution['execution_tokens'] + execution['evaluation_tokens'] 
                              for execution in branch_executions])
            
            st.metric("ブランチ内実行数", len(branch_executions))
            st.metric("ブランチ内実行コスト", f"${total_cost:.6f}")
            st.metric("ブランチ内総トークン", f"{total_tokens:,}")
    
    # メインコンテンツ
    tab1, tab2, tab3, tab4 = st.tabs(["🚀 新規実行", "📋 実行履歴", "🔍 結果比較", "🌿 ブランチ視覚化"])
    
    with tab1:
        st.header("新しいプロンプトを実行")
        
        # 実行メモ
        execution_memo = st.text_input(
            "📝 実行メモ",
            placeholder="プロンプトの変更内容や実験の目的を記録してください...",
            help="この実行の目的や変更点を記録します（Git風の履歴管理）"
        )
        
        # 実行モード選択
        st.subheader("📋 実行モード選択")
        execution_mode = st.radio(
            "実行方法を選択してください",
            ["テンプレート + データ入力", "単一プロンプト"],
            horizontal=True
        )
        
        st.markdown("---")
        
        # プロンプト設定
        st.subheader("📝 プロンプト設定")
        
        if execution_mode == "テンプレート + データ入力":
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**🔧 プロンプトテンプレート**")
                prompt_template = st.text_area(
                    "テンプレートを入力",
                    height=200,
                    placeholder="""例：以下のテキストを要約してください：

{user_input}

要約は3つの要点にまとめてください。""",
                    help="{user_input}でユーザー入力を参照できます",
                    key="template"
                )
            
            with col2:
                st.write("**📊 処理データ**")
                user_input = st.text_area(
                    "処理したいデータを入力",
                    height=200,
                    placeholder="ここに処理したいデータを入力してください...",
                    key="user_data"
                )
            
            # プレビュー
            if prompt_template and user_input and "{user_input}" in prompt_template:
                final_prompt = prompt_template.replace("{user_input}", user_input)
                st.success("✅ プロンプトが正常に結合されました")
                
                if st.checkbox("🔍 最終プロンプトをプレビュー"):
                    st.code(final_prompt, language=None)
                    
            elif prompt_template and "{user_input}" not in prompt_template:
                st.warning("⚠️ プロンプトテンプレートに{user_input}を含めてください")
                final_prompt = None
            else:
                final_prompt = None
                
        else:
            st.write("**📝 単一プロンプト**")
            final_prompt = st.text_area(
                "プロンプトを入力",
                height=200,
                placeholder="評価したいプロンプトを入力してください...",
                key="single_prompt"
            )
            prompt_template = None
            user_input = None
        
        st.markdown("---")
        
        # 評価基準
        st.subheader("📋 評価基準設定")
        evaluation_criteria = st.text_area(
            "評価基準を入力",
            height=150,
            value="""1. 回答の正確性（30点）
2. 情報の網羅性（25点）
3. 説明の分かりやすさ（25点）
4. 構成の論理性（20点）""",
            help="LLMの回答をどのような基準で評価するかを記載してください",
            key="criteria"
        )
        
        st.markdown("---")
        
        # 実行ボタン
        if st.button("🚀 実行 & 履歴に記録", type="primary"):
            if not execution_memo:
                st.error("❌ 実行メモを入力してください")
                return
            
            if not final_prompt:
                st.error("❌ プロンプトを正しく設定してください")
                return
            
            if not evaluation_criteria:
                st.error("❌ 評価基準を入力してください")
                return
            
            # 実行
            current_model_config = MODEL_CONFIGS[st.session_state.selected_model]
            evaluator = GeminiEvaluator(st.session_state.api_key, current_model_config)
            
            # プロンプト実行
            with st.spinner(f"🔄 {current_model_config['name']}でプロンプト実行中..."):
                execution_result = evaluator.execute_prompt(final_prompt)
            
            if not execution_result['success']:
                st.error(f"❌ プロンプト実行エラー: {execution_result['error']}")
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
            
            # 実行記録作成
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
                'total_cost': execution_result['cost_usd'],  # 実行コストのみ
                'model_name': execution_result['model_name'],
                'model_id': execution_result['model_id'],
                'token_accuracy': execution_result.get('token_accuracy', '不明')
            }
            
            execution_record = create_commit(execution_data, execution_memo)
            
            # 履歴とブランチに追加
            st.session_state.evaluation_history.append(execution_record)
            st.session_state.branches[st.session_state.current_branch].append(execution_record)
            
            # 結果表示
            accuracy_icon = "✅" if execution_result.get('token_accuracy') == 'API-正確' else "⚠️"
            st.success(f"✅ 実行完了！使用モデル: {execution_result['model_name']}")
            st.info(f"🔗 実行ID: `{execution_record['commit_hash']}` | {accuracy_icon} トークン精度: {execution_result.get('token_accuracy', '不明')}")
            st.markdown("---")
            
            # 1. LLMの回答（最優先表示）
            st.subheader("🤖 LLMの回答")
            st.markdown(f"""
            <div style="background: #ffffff; color: #2c3e50; padding: 2rem; border-radius: 10px; border-left: 4px solid #667eea; margin: 1rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <p style="color: #2c3e50; line-height: 1.6; margin: 0;">{html.escape(execution_result['response']).replace(chr(10), '<br>')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 2. 評価結果
            st.subheader("⭐ 評価結果")
            st.markdown(f"""
            <div style="background: #ffffff; color: #2c3e50; padding: 2rem; border-radius: 10px; border-left: 4px solid #f5576c; margin: 1rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <p style="color: #2c3e50; line-height: 1.6; margin: 0;">{html.escape(evaluation_result['response']).replace(chr(10), '<br>')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 3. コスト情報
            st.subheader("💰 コスト情報")
            
            cost_col1, cost_col2, cost_col3 = st.columns(3)
            
            with cost_col1:
                st.markdown(f"""
                <div style="background: #ffffff; color: #2c3e50; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; border: 1px solid #e0e0e0;">
                    <h4 style="color: #2c3e50; margin: 0 0 0.5rem 0;">実行コスト</h4>
                    <h2 style="color: #667eea; margin: 0.5rem 0;">${execution_result['cost_usd']:.6f}</h2>
                    <p style="color: #666; margin: 0;">トークン: {execution_result['total_tokens']:,}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with cost_col2:
                st.markdown(f"""
                <div style="background: #ffffff; color: #2c3e50; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; border: 1px solid #e0e0e0;">
                    <h4 style="color: #2c3e50; margin: 0 0 0.5rem 0;">評価コスト（参考）</h4>
                    <h2 style="color: #f5576c; margin: 0.5rem 0;">${evaluation_result['cost_usd']:.6f}</h2>
                    <p style="color: #666; margin: 0;">トークン: {evaluation_result['total_tokens']:,}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with cost_col3:
                st.markdown(f"""
                <div style="background: #ffffff; color: #2c3e50; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; border: 1px solid #e0e0e0;">
                    <h4 style="color: #2c3e50; margin: 0 0 0.5rem 0;">総コスト（実行のみ）</h4>
                    <h2 style="color: #4caf50; margin: 0.5rem 0;">${execution_data['total_cost']:.6f}</h2>
                    <p style="color: #666; margin: 0;">実行トークン: {execution_data['execution_tokens']:,}</p>
                </div>
                """, unsafe_allow_html=True)
    
    with tab2:
        st.header("📋 実行履歴")
        
        # ブランチフィルター
        col1, col2 = st.columns([3, 1])
        with col1:
            show_all_branches = st.checkbox("全ブランチ表示", value=False)
        with col2:
            if st.button("📥 履歴エクスポート"):
                df = pd.DataFrame(st.session_state.evaluation_history)
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="CSV ダウンロード",
                    data=csv,
                    file_name=f"prompt_execution_history_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        # 表示する実行記録を選択
        if show_all_branches:
            executions_to_show = st.session_state.evaluation_history
        else:
            executions_to_show = st.session_state.branches[st.session_state.current_branch]
        
        if not executions_to_show:
            st.info("まだ実行履歴がありません。「新規実行」タブでプロンプトを実行してください。")
            return
        
        st.markdown("---")
        
        # 実行履歴表示
        for i, execution in enumerate(reversed(executions_to_show)):
            timestamp = format_timestamp(execution['timestamp'])
            exec_hash = execution['commit_hash']
            exec_memo = execution.get('commit_message', 'メモなし')
            branch = execution.get('branch', 'unknown')
            model_name = execution.get('model_name', 'Unknown Model')
            token_accuracy = execution.get('token_accuracy', '不明')
            
            # 精度アイコン
            accuracy_icon = "✅" if token_accuracy == 'API-正確' else "⚠️" if token_accuracy == '概算' else "❓"
            
            # タグチェック
            tags_for_execution = [tag for tag, hash_val in st.session_state.tags.items() if hash_val == exec_hash]
            
            # 実行カード
            st.markdown(f"""
            <div class="commit-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <div>
                        <span class="branch-tag">{branch}</span>
                        {' '.join([f'<span class="tag-label">{tag}</span>' for tag in tags_for_execution])}
                        <strong>{exec_memo}</strong>
                        <br><small>🤖 {model_name} | {accuracy_icon} {token_accuracy}</small>
                    </div>
                    <span class="commit-hash">{exec_hash}</span>
                </div>
                <div style="color: #6c757d; font-size: 0.9rem;">
                    📅 {timestamp} | 💰 ${execution['execution_cost']:.6f} | 🔢 {execution['execution_tokens'] + execution['evaluation_tokens']:,} tokens
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 実行詳細
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # LLMの回答（最優先表示）
                st.write("**🤖 LLMの回答**")
                st.markdown(f"""
                <div style="background: #ffffff; color: #2c3e50; padding: 2rem; border-radius: 10px; border-left: 4px solid #667eea; margin: 1rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <p style="color: #2c3e50; line-height: 1.6; margin: 0;">{html.escape(execution['response']).replace(chr(10), '<br>')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 評価結果
                st.write("**⭐ 評価結果**")
                st.markdown(f"""
                <div style="background: #ffffff; color: #2c3e50; padding: 2rem; border-radius: 10px; border-left: 4px solid #f5576c; margin: 1rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <p style="color: #2c3e50; line-height: 1.6; margin: 0;">{html.escape(execution['evaluation']).replace(chr(10), '<br>')}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # メトリクス
                st.metric("実行トークン", f"{execution['execution_tokens']:,}")
                st.metric("評価トークン", f"{execution['evaluation_tokens']:,}")
                st.metric("実行コスト", f"${execution['execution_cost']:.6f}")
                st.metric("評価コスト（参考）", f"${execution['evaluation_cost']:.6f}")
            
            # 詳細情報
            st.write("**📋 詳細情報**")
            
            detail_col1, detail_col2 = st.columns(2)
            
            with detail_col1:
                if execution.get('execution_mode') == "テンプレート + データ入力":
                    st.write("**🔧 プロンプトテンプレート**")
                    st.code(execution.get('prompt_template', ''), language=None)
                    st.write("**📊 入力データ**")
                    st.code(execution.get('user_input', ''), language=None)
                
                st.write("**📝 最終プロンプト**")
                st.code(execution.get('final_prompt', ''), language=None)
            
            with detail_col2:
                st.write("**📋 評価基準**")
                st.code(execution['criteria'], language=None)
            
            st.markdown("---")
    
    with tab3:
        st.header("🔍 実行結果比較")
        
        executions_to_show = st.session_state.branches[st.session_state.current_branch]
        
        if len(executions_to_show) < 2:
            st.info("比較するには最低2つの実行記録が必要です。")
            return
        
        # 実行記録選択
        col1, col2 = st.columns(2)
        
        execution_options = [f"{execution['commit_hash']} - {execution.get('commit_message', 'メモなし')}" 
                         for execution in executions_to_show]
        
        with col1:
            st.write("**比較元実行**")
            exec1_idx = st.selectbox("比較元を選択", 
                                      range(len(execution_options)), 
                                      format_func=lambda x: execution_options[x],
                                      key="exec1")
        
        with col2:
            st.write("**比較先実行**")
            exec2_idx = st.selectbox("比較先を選択", 
                                      range(len(execution_options)), 
                                      format_func=lambda x: execution_options[x],
                                      key="exec2")
        
        if exec1_idx != exec2_idx:
            exec1 = executions_to_show[exec1_idx]
            exec2 = executions_to_show[exec2_idx]
            
            st.markdown("---")
            
            # 比較結果表示
            st.subheader("📊 比較結果")
            
            # メトリクス比較
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                cost_diff = exec2['execution_cost'] - exec1['execution_cost']  # 実行コストのみ
                st.metric("実行コスト", f"${exec2['execution_cost']:.6f}", f"{cost_diff:+.6f}")
            
            with col2:
                token_diff = (exec2['execution_tokens'] + exec2['evaluation_tokens']) - (exec1['execution_tokens'] + exec1['evaluation_tokens'])
                st.metric("総トークン", f"{exec2['execution_tokens'] + exec2['evaluation_tokens']:,}", f"{token_diff:+,}")
            
            with col3:
                exec_token_diff = exec2['execution_tokens'] - exec1['execution_tokens']
                st.metric("実行トークン", f"{exec2['execution_tokens']:,}", f"{exec_token_diff:+,}")
            
            with col4:
                eval_token_diff = exec2['evaluation_tokens'] - exec1['evaluation_tokens']
                st.metric("評価トークン", f"{exec2['evaluation_tokens']:,}", f"{eval_token_diff:+,}")
            
            # プロンプト差分
            st.subheader("📝 プロンプト差分")
            diff_html = get_diff_html(exec1.get('final_prompt', ''), exec2.get('final_prompt', ''))
            st.markdown(diff_html, unsafe_allow_html=True)
            
            # 回答比較
            st.subheader("🤖 LLMの回答比較")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**比較元 ({exec1['commit_hash']})**")
                st.markdown(f"""
                <div style="background: #ffffff; color: #2c3e50; padding: 2rem; border-radius: 10px; border-left: 4px solid #667eea; margin: 1rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <p style="color: #2c3e50; line-height: 1.6; margin: 0;">{html.escape(exec1['response']).replace(chr(10), '<br>')}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.write(f"**比較先 ({exec2['commit_hash']})**")
                st.markdown(f"""
                <div style="background: #ffffff; color: #2c3e50; padding: 2rem; border-radius: 10px; border-left: 4px solid #f5576c; margin: 1rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <p style="color: #2c3e50; line-height: 1.6; margin: 0;">{html.escape(exec2['response']).replace(chr(10), '<br>')}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # 評価結果比較
            st.subheader("⭐ 評価結果比較")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**比較元 ({exec1['commit_hash']})**")
                st.markdown(f"""
                <div style="background: #ffffff; color: #2c3e50; padding: 2rem; border-radius: 10px; border-left: 4px solid #667eea; margin: 1rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <p style="color: #2c3e50; line-height: 1.6; margin: 0;">{html.escape(exec1['evaluation']).replace(chr(10), '<br>')}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.write(f"**比較先 ({exec2['commit_hash']})**")
                st.markdown(f"""
                <div style="background: #ffffff; color: #2c3e50; padding: 2rem; border-radius: 10px; border-left: 4px solid #f5576c; margin: 1rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <p style="color: #2c3e50; line-height: 1.6; margin: 0;">{html.escape(exec2['evaluation']).replace(chr(10), '<br>')}</p>
                </div>
                """, unsafe_allow_html=True)
    
    with tab4:
        st.header("🌿 ブランチ視覚化")
        
        if not st.session_state.evaluation_history:
            st.info("まだ実行履歴がありません。")
            return
        
        # ブランチ構造表示
        st.subheader("📊 ブランチ構造")
        
        for branch_name, executions in st.session_state.branches.items():
            if not executions:
                continue
                
            st.write(f"**🌿 {branch_name}**")
            
            for i, execution in enumerate(executions):
                timestamp = format_timestamp(execution['timestamp'])
                timestamp_short = timestamp[5:16] if len(timestamp) >= 16 else timestamp  # MM-DD HH:MM形式
                exec_hash = execution['commit_hash']
                exec_memo = execution.get('commit_message', 'メモなし')
                
                # タグチェック
                tags_for_execution = [tag for tag, hash_val in st.session_state.tags.items() if hash_val == exec_hash]
                
                # 実行ライン表示
                if i == 0:
                    st.markdown(f"```\n│\n├─ {exec_hash} {exec_memo} ({timestamp_short})")
                elif i == len(executions) - 1:
                    st.markdown(f"│\n└─ {exec_hash} {exec_memo} ({timestamp_short})")
                else:
                    st.markdown(f"│\n├─ {exec_hash} {exec_memo} ({timestamp_short})")
                
                if tags_for_execution:
                    st.markdown(f"   🏷️ Tags: {', '.join(tags_for_execution)}")
            
            st.markdown("```")
            st.markdown("---")
        
        # 統計サマリー
        st.subheader("📈 全体統計")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("総ブランチ数", len(st.session_state.branches))
        
        with col2:
            st.metric("総実行数", len(st.session_state.evaluation_history))
        
        with col3:
            st.metric("総タグ数", len(st.session_state.tags))
        
        with col4:
            total_cost = sum([execution['execution_cost'] for execution in st.session_state.evaluation_history])  # 実行コストのみ
            st.metric("総実行コスト", f"${total_cost:.6f}")

if __name__ == "__main__":
    main()