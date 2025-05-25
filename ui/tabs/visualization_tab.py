"""
分析タブ
ブランチ構造と統計情報を表示する機能
"""

import streamlit as st
from core import GitManager
try:
    from core import DataManager
except ImportError:
    import datetime
    import json
    import pandas as pd
    import hashlib
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
                'date_range': None # Placeholder, implement if needed
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

from ui import (
    format_timestamp,
    render_statistics_summary,
    render_detailed_statistics
)


def render_visualization_tab():
    """分析タブをレンダリング"""
    st.header("📊 プロジェクト分析")
    
    if not st.session_state.evaluation_history:
        st.info("まだ実行履歴がありません。")
        return
    
    # 分析ダッシュボード
    analysis_col1, analysis_col2 = st.columns([2, 1])
    
    with analysis_col1:
        st.subheader("🌿 ブランチ構造")
        _render_branch_tree()
    
    with analysis_col2:
        st.subheader("📈 統計サマリー")
        global_stats = GitManager.get_global_stats()
        data_stats = DataManager.get_data_statistics()
        render_statistics_summary(global_stats, data_stats)
    
    st.markdown("---")
    
    # 詳細統計
    render_detailed_statistics(data_stats, DataManager)


def _render_branch_tree():
    """ブランチツリーの表示"""
    branch_tree = GitManager.get_branch_tree()
    
    for branch_name, executions in branch_tree.items():
        if not executions:
            continue
        
        # ブランチヘッダー
        branch_col1, branch_col2 = st.columns([3, 1])
        
        with branch_col1:
            st.markdown(f"**🌿 {branch_name}**")
        
        with branch_col2:
            st.markdown(f"*{len(executions)}件の実行*")
        
        # 実行記録をコンパクトに表示
        for i, execution in enumerate(executions[-5:]):  # 最新5件のみ表示
            timestamp_str = format_timestamp(execution['timestamp'])
            timestamp_short = timestamp_str[5:16] if len(timestamp_str) >= 16 else timestamp_str
            exec_hash = execution['commit_hash'][:8]
            exec_memo = execution.get('commit_message', 'メモなし')
            
            # シンプルな表示
            connector = "├─" if i < len(executions[-5:]) - 1 else "└─"
            
            st.markdown(f"""
            <div style="font-family: monospace; color: #666; margin-left: 1rem;">
                {connector} <code>{exec_hash}</code> {exec_memo} <small>({timestamp_short})</small>
            </div>
            """, unsafe_allow_html=True)
        
        if len(executions) > 5:
            st.markdown(f"<div style='margin-left: 1rem; color: #888; font-style: italic;'>... さらに{len(executions) - 5}件</div>", unsafe_allow_html=True)
        
        st.markdown("---")