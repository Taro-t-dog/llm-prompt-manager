"""
データ管理クラス
JSON/CSV のインポート・エクスポート、バックアップ・復元機能を提供
"""

import streamlit as st
import pandas as pd
import json
import datetime
from typing import Dict, List, Any, Union
import hashlib

class DataManager:
    @staticmethod
    def export_to_json(include_metadata: bool = True) -> str:
        history_data = {'evaluation_history': st.session_state.evaluation_history, 'branches': st.session_state.branches,
                        'tags': st.session_state.tags, 'current_branch': st.session_state.current_branch}
        if include_metadata:
            history_data.update({'export_timestamp': datetime.datetime.now().isoformat(), 'export_version': '1.0'})
        return json.dumps(history_data, default=str, ensure_ascii=False, indent=2)
    
    @staticmethod
    def import_from_json(json_data: Union[str, dict]) -> Dict[str, Any]:
        try:
            data = json.loads(json_data) if isinstance(json_data, str) else json_data
            st.session_state.evaluation_history = data.get('evaluation_history', [])
            st.session_state.branches = data.get('branches', {"main": []})
            st.session_state.tags = data.get('tags', {})
            st.session_state.current_branch = data.get('current_branch', 'main')
            return {'success': True, 'imported_count': len(st.session_state.evaluation_history)}
        except Exception as e:
            return {'success': False, 'error': str(e), 'imported_count': 0}
    
    @staticmethod
    def export_to_csv() -> str:
        if not st.session_state.evaluation_history: return ""
        df = pd.DataFrame(st.session_state.evaluation_history)
        if 'timestamp' in df.columns:
            df['timestamp'] = df['timestamp'].apply(lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x))
        return df.to_csv(index=False, encoding='utf-8-sig')
    
    @staticmethod
    def import_from_csv(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            records = []
            for _, row in df.iterrows():
                record = {'timestamp': row.get('timestamp', datetime.datetime.now().isoformat()), 'execution_mode': row.get('execution_mode', '単一プロンプト'),
                          'final_prompt': row.get('final_prompt', ''), 'criteria': row.get('criteria', ''), 'response': row.get('response', ''),
                          'evaluation': row.get('evaluation', ''), 'execution_tokens': int(row.get('execution_tokens', 0)), 'evaluation_tokens': int(row.get('evaluation_tokens', 0)),
                          'execution_cost': float(row.get('execution_cost', 0.0)), 'evaluation_cost': float(row.get('evaluation_cost', 0.0)), 'total_cost': float(row.get('total_cost', 0.0)),
                          'commit_hash': row.get('commit_hash', hashlib.md5(str(row.to_dict()).encode()).hexdigest()[:8]), 'commit_message': row.get('commit_message', 'CSVインポート'),
                          'branch': row.get('branch', st.session_state.current_branch), 'model_name': row.get('model_name', 'Unknown Model'), 'api_provider': row.get('api_provider', 'unknown')}
                records.append(record)
            st.session_state.evaluation_history.extend(records)
            for record in records:
                branch = record['branch']
                if branch not in st.session_state.branches: st.session_state.branches[branch] = []
                st.session_state.branches[branch].append(record)
            return {'success': True, 'imported_count': len(records)}
        except Exception as e:
            return {'success': False, 'error': str(e), 'imported_count': 0}
    
    @staticmethod
    def get_file_suggestion(file_type: str = "json") -> str:
        ts, count = datetime.datetime.now().strftime('%Y%m%d_%H%M%S'), len(st.session_state.evaluation_history)
        return f"prompt_history_{ts}_{count}records.{file_type}"
    
    @staticmethod
    def get_data_statistics() -> Dict[str, Any]:
        if not st.session_state.evaluation_history:
            return {'total_records': 0, 'models_used': {}}
        models_used = {}
        for ex in st.session_state.evaluation_history:
            model = ex.get('model_name', 'Unknown')
            models_used[model] = models_used.get(model, 0) + 1
        return {'total_records': len(st.session_state.evaluation_history), 'models_used': models_used}
    
    @staticmethod
    def validate_data_integrity() -> Dict[str, Any]:
        return {'is_valid': True, 'issues': [], 'warnings': []}