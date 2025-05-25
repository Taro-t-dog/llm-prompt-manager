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
    get_header_html, render_response_box, render_evaluation_box, render_cost_metrics, 
    render_execution_card, render_comparison_metrics, render_comparison_responses, 
    render_comparison_evaluations, render_export_section, render_import_section, 
    render_statistics_summary, render_detailed_statistics, format_timestamp
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
    page_title="LLM Prompt Manager",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"  # サイドバーを最初は閉じる
)

# スタイル読み込み
load_styles()

# セッション状態の初期化
GitManager.initialize_session_state()
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = "gemini-2.0-flash-exp"

def render_streamlined_sidebar():
    """簡潔なサイドバー"""
    st.header("⚙️ 設定")
    
    # API Key
    api_key = st.text_input(
        "🔑 API Key", 
        value=st.session_state.api_key,
        type="password"
    )
    
    if api_key != st.session_state.api_key:
        st.session_state.api_key = api_key
    
    if not api_key:
        st.error("APIキーが必要です")
        st.markdown("[APIキーを取得 →](https://makersuite.google.com/app/apikey)")
        return  # st.stop()の代わりにreturnを使用
    
    # モデル選択
    st.subheader("🤖 モデル")
    
    model_options = get_model_options()
    selected_model_index = model_options.index(st.session_state.selected_model) if st.session_state.selected_model in model_options else 0
    
    selected_model = st.selectbox(
        "モデルを選択",
        model_options,
        format_func=lambda x: MODEL_CONFIGS[x]['name'],
        index=selected_model_index,
        label_visibility="collapsed"
    )
    
    if selected_model != st.session_state.selected_model:
        st.session_state.selected_model = selected_model
    
    current_model = get_model_config(st.session_state.selected_model)
    
    if is_free_model(st.session_state.selected_model):
        st.success("💰 無料")
    else:
        st.info(f"💰 ${current_model['input_cost_per_token'] * 1000000:.2f}/1M tokens")
    
    # 統計情報
    if st.session_state.evaluation_history:
        st.markdown("---")
        st.subheader("📊 統計")
        
        global_stats = GitManager.get_global_stats()
        branch_stats = GitManager.get_branch_stats()
        
        st.metric("実行数", global_stats['total_executions'])
        st.metric("コスト", f"${global_stats['total_cost']:.4f}")
        
        # データ管理
        st.markdown("---")
        st.subheader("💾 データ")
        
        export_col1, export_col2 = st.columns(2)
        
        with export_col1:
            if st.button("📤 JSON", use_container_width=True):
                json_data = DataManager.export_to_json()
                filename = DataManager.get_file_suggestion("json")
                st.download_button(
                    "📥 DL",
                    json_data,
                    filename,
                    "application/json",
                    key="json_dl"
                )
        
        with export_col2:
            if st.button("📊 CSV", use_container_width=True):
                csv_data = DataManager.export_to_csv()
                filename = DataManager.get_file_suggestion("csv")
                st.download_button(
                    "📥 DL",
                    csv_data,
                    filename,
                    "text/csv",
                    key="csv_dl"
                )
        
        # インポート
        uploaded_file = st.file_uploader("📂 インポート", type=["json", "csv"])
        if uploaded_file:
            if st.button("⬆️ インポート"):
                try:
                    if uploaded_file.name.endswith('.json'):
                        data = json.load(uploaded_file)
                        result = DataManager.import_from_json(data)
                    else:
                        df = pd.read_csv(uploaded_file)
                        result = DataManager.import_from_csv(df)
                    
                    if result['success']:
                        st.success(f"✅ {result['imported_count']}件")
                        st.rerun()
                    else:
                        st.error(f"❌ {result['error']}")
                except Exception as e:
                    st.error(f"❌ {str(e)}")

def render_git_controls():
    """メイン画面のGit操作パネル"""
    st.subheader("🌿 ブランチ管理")
    
    git_col1, git_col2 = st.columns(2)
    
    with git_col1:
        st.write("**現在のブランチ**")
        available_branches = GitManager.get_all_branches()
        current_branch = GitManager.get_current_branch()
        current_branch_index = available_branches.index(current_branch) if current_branch in available_branches else 0
        
        selected_branch = st.selectbox(
            "ブランチ",
            available_branches,
            index=current_branch_index,
            label_visibility="collapsed"
        )
        
        if selected_branch != current_branch:
            if GitManager.switch_branch(selected_branch):
                st.rerun()
    
    with git_col2:
        st.write("**新しいブランチ**")
        new_branch_name = st.text_input("ブランチ名", label_visibility="collapsed")
        if st.button("🌱 作成", use_container_width=True):
            if new_branch_name and GitManager.create_branch(new_branch_name):
                if GitManager.switch_branch(new_branch_name):
                    st.success(f"ブランチ '{new_branch_name}' を作成")
                    st.rerun()

def main():
    # ヘッダー
    global_stats = GitManager.get_global_stats()
    st.markdown(get_header_html("🚀 LLM Prompt Manager", global_stats), unsafe_allow_html=True)
    
    # サイドバー
    with st.sidebar:
        render_streamlined_sidebar()
    
    # APIキーチェック
    if not st.session_state.api_key:
        st.warning("⚠️ APIキーを設定してからお使いください")
        return
    
    # Git管理パネル
    if st.session_state.evaluation_history:
        render_git_controls()
        st.markdown("---")
    
    # メインタブ
    tab1, tab2, tab3, tab4 = st.tabs(["🚀 実行", "📋 履歴", "🔍 比較", "📊 分析"])
    
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