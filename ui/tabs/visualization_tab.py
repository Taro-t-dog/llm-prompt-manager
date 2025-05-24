# tabs/visualization_tab.py
import streamlit as st
from core import GitManager # GitManagerをcoreからインポート
try:
    from core import DataManager # DataManagerをcoreからインポート
except ImportError:
    # DataManagerが見つからない場合は、app.pyと同様の簡易版を参照することを想定
    # ただし、このファイルで直接定義するよりは、app.pyから渡すか、
    # coreに確実に存在するようにするのが望ましい。
    # ここでは、app.pyで定義されたものが利用可能であることを前提とするか、
    # もし直接利用するなら、app.pyのDataManager定義を共有モジュールに移動することを推奨。
    # 今回は、app.pyでDataManagerが準備されている前提で進めます。
    # ui.pyでDataManagerを引数に取る関数があるので、それを呼び出す際に
    # app.py側でDataManagerインスタンス（またはクラス）を渡す形になります。
    pass 

from ui import (
    format_timestamp, # ui.py にあると仮定
    render_statistics_summary,
    render_detailed_statistics
)

# DataManagerの一時的なインポート回避のための措置 (app.py と同様)
# この部分は、DataManagerが確実にcoreからインポートできるか、
# あるいはapp.pyからこの関数に必要な形で渡されるなら不要です。
# 現状のapp.pyの構成に合わせるため、ここにも記載しておきます。
try:
    from core import DataManager
except ImportError:
    import datetime
    import json
    import pandas as pd
    import hashlib
    # DataManagerが見つからない場合は、簡易版を定義 (app.pyからコピー)
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

def render_visualization_tab():
    """ブランチ視覚化タブをレンダリング"""
    st.header("🌿 ブランチ視覚化")
    
    if not st.session_state.evaluation_history:
        st.info("まだ実行履歴がありません。")
        return
    
    st.subheader("📊 ブランチ構造")
    
    branch_tree = GitManager.get_branch_tree()
    
    for branch_name, executions in branch_tree.items():
        if not executions:
            continue
            
        st.write(f"**🌿 {branch_name}**")
        
        # Tree-like display using markdown and careful formatting
        tree_str_parts = []
        for i, execution in enumerate(executions):
            timestamp_str = format_timestamp(execution['timestamp'])
            # Ensure timestamp_str has enough length before slicing
            timestamp_short = timestamp_str[5:16] if len(timestamp_str) >= 16 else timestamp_str
            exec_hash = execution['commit_hash']
            exec_memo = execution.get('commit_message', 'メモなし')
            
            tags_for_execution = GitManager.get_tags_for_commit(exec_hash)
            
            prefix = "├─"
            if i == len(executions) - 1: # Last item in this branch
                prefix = "└─"

            tree_str_parts.append(f"{prefix} {exec_hash} {exec_memo} ({timestamp_short})")
            if tags_for_execution:
                tree_str_parts.append(f"   {'│' if i < len(executions) - 1 else ' '}  🏷️ Tags: {', '.join(tags_for_execution)}")
        
        # Join with newlines appropriate for markdown code block
        # Need to ensure proper vertical alignment if there are no tags
        # This simplified version might not perfectly align if some entries have tags and others don't
        # For perfect alignment, more complex logic or HTML might be needed.
        
        # Simplified approach for markdown display:
        for i, execution in enumerate(executions):
            timestamp_str = format_timestamp(execution['timestamp'])
            timestamp_short = timestamp_str[5:16] if len(timestamp_str) >= 16 else timestamp_str
            exec_hash = execution['commit_hash']
            exec_memo = execution.get('commit_message', 'メモなし')
            tags_for_execution = GitManager.get_tags_for_commit(exec_hash)

            connector = "│" # Default connector
            if i == 0:
                 # For the first element, it's cleaner without the top part of the connector
                 pass # Using default branch title
            
            if i < len(executions) -1 : # if not the last element
                st.markdown(f"    {connector}") # Vertical line
            
            prefix = "├─"
            if i == len(executions) - 1:
                prefix = "└─"
            
            st.markdown(f"    {prefix} **{exec_hash}** - *{exec_memo}* ({timestamp_short})")
            
            if tags_for_execution:
                tag_prefix_connector = "│" if i < len(executions) - 1 else " "
                st.markdown(f"    {tag_prefix_connector}   🏷️ Tags: {', '.join(tags_for_execution)}")
        
        st.markdown("---") # Separator between branches
    
    st.subheader("📈 全体統計")
    
    global_stats = GitManager.get_global_stats()
    data_stats = DataManager.get_data_statistics() # Uses the DataManager defined/imported above
    
    render_statistics_summary(global_stats, data_stats)
    render_detailed_statistics(data_stats, DataManager) # Pass the DataManager class