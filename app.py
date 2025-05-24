import streamlit as st
import pandas as pd
import json
import datetime
from typing import Dict, List, Any
import re
import hashlib
import html
import difflib

# 新しいモジュールのインポート
from config import MODEL_CONFIGS, get_model_config, get_model_options, get_model_labels, is_free_model
from core import GeminiEvaluator, GitManager, DataManager
from ui import (
    load_styles, get_response_box_html, get_evaluation_box_html, get_metric_card_html,
    render_response_box, render_evaluation_box, render_cost_metrics, render_execution_card,
    render_comparison_metrics, render_comparison_responses, render_comparison_evaluations,
    render_export_section, render_import_section, render_statistics_summary,
    render_detailed_statistics, format_timestamp
)

from ui.tabs import (
    render_execution_tab,
    render_history_tab,
    render_comparison_tab,
    render_visualization_tab

)


# DataManagerの一時的なインポート回避
try:
    from core import DataManager
except ImportError:
    # DataManagerが見つからない場合は、簡易版を定義
    class DataManager:
        @staticmethod
        def export_to_json(include_metadata=True):
            history_data = {
                'evaluation_history': st.session_state.evaluation_history,
                'branches': st.session_state.branches,
                'tags': st.session_state.tags,
                'current_branch': st.session_state.current_branch
            }
            if include_metadata:
                history_data['export_timestamp'] = datetime.datetime.now().isoformat()
            return json.dumps(history_data, default=str, ensure_ascii=False, indent=2)
        
        @staticmethod
        def import_from_json(json_data):
            try:
                if isinstance(json_data, str):
                    history_data = json.loads(json_data)
                else:
                    history_data = json_data
                
                st.session_state.evaluation_history = history_data.get('evaluation_history', [])
                st.session_state.branches = history_data.get('branches', {"main": []})
                st.session_state.tags = history_data.get('tags', {})
                st.session_state.current_branch = history_data.get('current_branch', 'main')
                
                return {
                    'success': True,
                    'imported_count': len(st.session_state.evaluation_history),
                    'export_timestamp': history_data.get('export_timestamp', 'Unknown')
                }
            except Exception as e:
                return {'success': False, 'error': str(e), 'imported_count': 0}
        
        @staticmethod
        def export_to_csv():
            if not st.session_state.evaluation_history:
                return ""
            df = pd.DataFrame(st.session_state.evaluation_history)
            if 'timestamp' in df.columns:
                df['timestamp'] = df['timestamp'].apply(
                    lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x)
                )
            return df.to_csv(index=False, encoding='utf-8-sig')
        
        @staticmethod
        def import_from_csv(df):
            try:
                imported_records = []
                for _, row in df.iterrows():
                    record = {
                        'timestamp': row.get('timestamp', datetime.datetime.now().isoformat()),
                        'execution_mode': row.get('execution_mode', '単一プロンプト'),
                        'final_prompt': row.get('final_prompt', ''),
                        'criteria': row.get('criteria', ''),
                        'response': row.get('response', ''),
                        'evaluation': row.get('evaluation', ''),
                        'execution_tokens': int(row.get('execution_tokens', 0)),
                        'evaluation_tokens': int(row.get('evaluation_tokens', 0)),
                        'execution_cost': float(row.get('execution_cost', 0.0)),
                        'evaluation_cost': float(row.get('evaluation_cost', 0.0)),
                        'total_cost': float(row.get('total_cost', 0.0)),
                        'commit_hash': row.get('commit_hash', hashlib.md5(str(row.to_dict()).encode()).hexdigest()[:8]),
                        'commit_message': row.get('commit_message', 'CSVインポート'),
                        'branch': row.get('branch', st.session_state.current_branch),
                        'model_name': row.get('model_name', 'Unknown Model')
                    }
                    imported_records.append(record)
                
                st.session_state.evaluation_history.extend(imported_records)
                for record in imported_records:
                    branch_name = record['branch']
                    if branch_name not in st.session_state.branches:
                        st.session_state.branches[branch_name] = []
                    st.session_state.branches[branch_name].append(record)
                
                return {'success': True, 'imported_count': len(imported_records)}
            except Exception as e:
                return {'success': False, 'error': str(e), 'imported_count': 0}
        
        @staticmethod
        def get_file_suggestion(file_type="json"):
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            record_count = len(st.session_state.evaluation_history)
            if file_type.lower() == "json":
                return f"prompt_history_{timestamp}_{record_count}records.json"
            elif file_type.lower() == "csv":
                return f"prompt_execution_history_{timestamp}_{record_count}records.csv"
            else:
                return f"prompt_data_{timestamp}.{file_type}"
        
        @staticmethod
        def get_data_statistics():
            if not st.session_state.evaluation_history:
                return {
                    'total_records': 0,
                    'models_used': {},
                    'date_range': None
                }
            
            models_used = {}
            for execution in st.session_state.evaluation_history:
                model = execution.get('model_name', 'Unknown')
                models_used[model] = models_used.get(model, 0) + 1
            
            return {
                'total_records': len(st.session_state.evaluation_history),
                'models_used': models_used,
                'date_range': None
            }
        
        @staticmethod
        def validate_data_integrity():
            return {
                'is_valid': True,
                'issues': [],
                'warnings': []
            }
        
        @staticmethod
        def clear_all_data():
            st.session_state.evaluation_history = []
            st.session_state.branches = {"main": []}
            st.session_state.tags = {}
            st.session_state.current_branch = "main"

# ページ設定
st.set_page_config(
    page_title="LLMプロンプト自動評価システム",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# スタイル読み込み
load_styles()

# セッション状態の初期化
GitManager.initialize_session_state()
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = "gemini-2.0-flash-exp"

def format_timestamp(timestamp):
    """タイムスタンプをフォーマット"""
    if isinstance(timestamp, str):
        if 'T' in timestamp:
            try:
                dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                return timestamp[:19]
        return timestamp
    else:
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')

def get_diff_html(old_text: str, new_text: str) -> str:
    """2つのテキストの差分をHTMLで表示"""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))
    
    if not diff:
        return "変更なし"
    
    html_diff = []
    for line in diff[3:]:
        if line.startswith('+'):
            html_diff.append(f'<div class="diff-added">+ {html.escape(line[1:])}</div>')
        elif line.startswith('-'):
            html_diff.append(f'<div class="diff-removed">- {html.escape(line[1:])}</div>')
        else:
            html_diff.append(f'<div>{html.escape(line)}</div>')
    
    return ''.join(html_diff)

def render_model_selection_sidebar():
    """サイドバーのモデル選択部分をレンダリング"""
    st.subheader("🤖 モデル選択")
    
    model_options = get_model_options()
    selected_model_index = model_options.index(st.session_state.selected_model) if st.session_state.selected_model in model_options else 0
    
    selected_model = st.selectbox(
        "使用するモデル",
        model_options,
        format_func=lambda x: MODEL_CONFIGS[x]['name'],
        index=selected_model_index
    )
    
    if selected_model != st.session_state.selected_model:
        st.session_state.selected_model = selected_model
    
    current_model = get_model_config(st.session_state.selected_model)
    
    st.markdown(f"""
    **📋 モデル詳細:**
    - **名前**: {current_model['name']}
    - **説明**: {current_model['description']}
    - **コンテキスト**: {current_model['context_window']:,} tokens
    - **無料枠**: {'✅ あり' if current_model['free_tier'] else '❌ なし'}
    """)
    
    if is_free_model(st.session_state.selected_model):
        st.success("💰 **完全無料!**")
    else:
        st.markdown(f"""
        **💰 料金:**
        - 入力: ${current_model['input_cost_per_token'] * 1000000:.2f}/1M tokens
        - 出力: ${current_model['output_cost_per_token'] * 1000000:.2f}/1M tokens
        """)

def render_data_management_sidebar():
    """サイドバーのデータ管理部分をレンダリング（componentsを使用）"""
    st.header("💾 データ管理")
    
    if st.session_state.evaluation_history:
        render_export_section(DataManager)
    
    render_import_section(DataManager)
    
    if st.session_state.evaluation_history:
        st.markdown("---")
        st.subheader("🗑️ データ管理")
        
        if st.button("🗑️ 全データクリア", type="secondary"):
            if st.button("⚠️ 本当にクリアしますか？", type="secondary"):
                DataManager.clear_all_data()
                st.success("✅ データをクリアしました")
                st.rerun()

def render_git_operations_sidebar():
    """サイドバーのGit操作部分をレンダリング"""
    st.header("🌿 ブランチ管理")
    
    available_branches = GitManager.get_all_branches()
    current_branch = GitManager.get_current_branch()
    current_branch_index = available_branches.index(current_branch) if current_branch in available_branches else 0
    
    selected_branch = st.selectbox(
        "ブランチを選択",
        available_branches,
        index=current_branch_index
    )
    
    if selected_branch != current_branch:
        if GitManager.switch_branch(selected_branch):
            st.rerun()
    
    new_branch_name = st.text_input("新しいブランチ名")
    if st.button("🌱 ブランチ作成"):
        if new_branch_name:
            if GitManager.create_branch(new_branch_name):
                if GitManager.switch_branch(new_branch_name):
                    st.success(f"ブランチ '{new_branch_name}' を作成し、切り替えました")
                    st.rerun()
            else:
                st.error("同名のブランチが既に存在します")
        else:
            st.warning("ブランチ名を入力してください")

def render_tag_management_sidebar():
    """サイドバーのタグ管理部分をレンダリング"""
    st.header("🏷️ タグ管理")
    
    if st.session_state.evaluation_history:
        execution_options = [f"{execution['commit_hash']} - {execution.get('commit_message', 'メモなし')}" 
                        for execution in st.session_state.evaluation_history]
        
        selected_execution_idx = st.selectbox("タグを付ける実行記録", 
                                         range(len(execution_options)), 
                                         format_func=lambda x: execution_options[x])
        
        tag_name = st.text_input("タグ名")
        if st.button("🏷️ タグ作成"):
            if tag_name:
                exec_hash = st.session_state.evaluation_history[selected_execution_idx]['commit_hash']
                if GitManager.create_tag(tag_name, exec_hash):
                    st.success(f"タグ '{tag_name}' を作成しました")
                else:
                    st.error("同名のタグが既に存在するか、コミットが見つかりません")

def render_statistics_sidebar():
    """サイドバーの統計情報部分をレンダリング"""
    if st.session_state.evaluation_history:
        st.header("📊 統計情報")
        
        branch_stats = GitManager.get_branch_stats()
        
        st.metric("ブランチ内実行数", branch_stats['execution_count'])
        st.metric("ブランチ内実行コスト", f"${branch_stats['total_cost']:.6f}")
        st.metric("ブランチ内総トークン", f"{branch_stats['total_tokens']:,}")
        
        if st.checkbox("🌐 詳細統計を表示"):
            data_stats = DataManager.get_data_statistics()
            global_stats = GitManager.get_global_stats()
            
            st.metric("総実行数", global_stats['total_executions'])
            st.metric("総ブランチ数", global_stats['total_branches'])
            st.metric("総タグ数", global_stats['total_tags'])
            
            if data_stats['models_used']:
                st.write("**使用モデル統計:**")
                for model, count in data_stats['models_used'].items():
                    st.write(f"- {model}: {count}回")


def main():
    st.title("🚀 LLM プロンプト Git 管理システム")
    st.markdown("Git風のバージョン管理でプロンプトの進化を追跡しましょう！")
    
    header_col1, header_col2, header_col3 = st.columns([2, 1, 1])
    with header_col1:
        current_branch = GitManager.get_current_branch()
        st.markdown(f"**📍 現在のブランチ:** `{current_branch}`")
    with header_col2:
        global_stats = GitManager.get_global_stats()
        st.markdown(f"**📝 総実行数:** {global_stats['total_executions']}")
    with header_col3:
        st.markdown(f"**🌿 ブランチ数:** {global_stats['total_branches']}")
    
    st.info("💡 Git風の履歴管理でプロンプトの改善過程を追跡できます。実行メモで変更理由を記録し、ブランチで異なるアプローチを並行テストしましょう。")
    
    st.markdown("---")
    
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
        
        render_model_selection_sidebar()
        
        st.markdown("---")
        
        render_data_management_sidebar()
        
        st.markdown("---")
        
        render_git_operations_sidebar()
        
        st.markdown("---")
        
        render_tag_management_sidebar()
        
        st.markdown("---")
        
        render_statistics_sidebar()
    
    tab1, tab2, tab3, tab4 = st.tabs(["🚀 新規実行", "📋 実行履歴", "🔍 結果比較", "🌿 ブランチ視覚化"])
    
    with tab1:
        render_execution_tab()
    
    with tab2:
        render_history_tab()
    
    with tab3:
        render_comparison_tab()
    
    with tab4:
        render_visualization_tab()

if __name__ == "__main__":
    main()