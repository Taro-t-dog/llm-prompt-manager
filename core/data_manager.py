"""
データ管理クラス
JSON/CSV のインポート・エクスポート、バックアップ・復元機能を提供
"""

import streamlit as st
import pandas as pd
import json
import datetime
from typing import Dict, List, Any, Optional, Union
import hashlib


class DataManager:
    """データの保存・読み込み・管理を担当するクラス"""
    
    @staticmethod
    def export_to_json(include_metadata: bool = True) -> str:
        """
        履歴データをJSON形式でエクスポート
        
        Args:
            include_metadata: メタデータを含めるかどうか
            
        Returns:
            JSON文字列
        """
        history_data = {
            'evaluation_history': st.session_state.evaluation_history,
            'branches': st.session_state.branches,
            'tags': st.session_state.tags,
            'current_branch': st.session_state.current_branch
        }
        
        if include_metadata:
            history_data.update({
                'export_timestamp': datetime.datetime.now().isoformat(),
                'export_version': '1.0',
                'total_records': len(st.session_state.evaluation_history),
                'branch_count': len(st.session_state.branches),
                'tag_count': len(st.session_state.tags)
            })
        
        return json.dumps(history_data, default=str, ensure_ascii=False, indent=2)
    
    @staticmethod
    def import_from_json(json_data: Union[str, dict]) -> Dict[str, Any]:
        """
        JSON形式のデータをインポート
        
        Args:
            json_data: JSON文字列または辞書
            
        Returns:
            インポート結果の詳細
        """
        try:
            if isinstance(json_data, str):
                history_data = json.loads(json_data)
            else:
                history_data = json_data
            
            # データ検証
            required_keys = ['evaluation_history', 'branches', 'tags', 'current_branch']
            missing_keys = [key for key in required_keys if key not in history_data]
            
            if missing_keys:
                return {
                    'success': False,
                    'error': f'必要なキーが不足しています: {missing_keys}',
                    'imported_count': 0
                }
            
            # バックアップの作成
            backup = DataManager._create_backup()
            
            try:
                # データを復元
                st.session_state.evaluation_history = history_data.get('evaluation_history', [])
                st.session_state.branches = history_data.get('branches', {"main": []})
                st.session_state.tags = history_data.get('tags', {})
                st.session_state.current_branch = history_data.get('current_branch', 'main')
                
                # 統計情報を計算
                imported_count = len(st.session_state.evaluation_history)
                branch_count = len(st.session_state.branches)
                tag_count = len(st.session_state.tags)
                
                return {
                    'success': True,
                    'imported_count': imported_count,
                    'branch_count': branch_count,
                    'tag_count': tag_count,
                    'export_timestamp': history_data.get('export_timestamp', 'Unknown'),
                    'backup': backup
                }
                
            except Exception as e:
                # エラーが発生した場合、バックアップから復元
                DataManager._restore_from_backup(backup)
                return {
                    'success': False,
                    'error': f'データ復元中にエラーが発生しました: {str(e)}',
                    'imported_count': 0
                }
                
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f'JSON解析エラー: {str(e)}',
                'imported_count': 0
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'予期しないエラー: {str(e)}',
                'imported_count': 0
            }
    
    @staticmethod
    def export_to_csv() -> str:
        """
        履歴データをCSV形式でエクスポート
        
        Returns:
            CSV文字列
        """
        if not st.session_state.evaluation_history:
            return ""
        
        # DataFrameに変換
        df = pd.DataFrame(st.session_state.evaluation_history)
        
        # タイムスタンプを文字列に変換
        if 'timestamp' in df.columns:
            df['timestamp'] = df['timestamp'].apply(
                lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x)
            )
        
        # CSVとして出力
        return df.to_csv(index=False, encoding='utf-8-sig')
    
    @staticmethod
    def import_from_csv(csv_data: Union[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        CSV形式のデータをインポート
        
        Args:
            csv_data: CSV文字列またはDataFrame
            
        Returns:
            インポート結果の詳細
        """
        try:
            if isinstance(csv_data, str):
                df = pd.read_csv(pd.StringIO(csv_data))
            else:
                df = csv_data
            
            if df.empty:
                return {
                    'success': False,
                    'error': 'CSVファイルが空です',
                    'imported_count': 0
                }
            
            # CSVデータを内部形式に変換
            imported_records = []
            current_branch = st.session_state.current_branch
            
            for _, row in df.iterrows():
                record = DataManager._convert_csv_row_to_record(row, current_branch)
                imported_records.append(record)
            
            # 既存データに追加
            st.session_state.evaluation_history.extend(imported_records)
            
            # ブランチ別に整理
            branch_updates = {}
            for record in imported_records:
                branch_name = record['branch']
                if branch_name not in st.session_state.branches:
                    st.session_state.branches[branch_name] = []
                st.session_state.branches[branch_name].append(record)
                branch_updates[branch_name] = branch_updates.get(branch_name, 0) + 1
            
            return {
                'success': True,
                'imported_count': len(imported_records),
                'branch_updates': branch_updates,
                'columns': list(df.columns)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'CSVインポートエラー: {str(e)}',
                'imported_count': 0
            }
    
    @staticmethod
    def _convert_csv_row_to_record(row: pd.Series, default_branch: str) -> Dict[str, Any]:
        """CSV行を内部記録形式に変換"""
        return {
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
            'commit_hash': row.get('commit_hash', DataManager._generate_commit_hash(str(row.to_dict()))),
            'commit_message': row.get('commit_message', 'CSVインポート'),
            'branch': row.get('branch', default_branch),
            'parent_hash': row.get('parent_hash', None),
            'model_name': row.get('model_name', 'Unknown Model'),
            'model_id': row.get('model_id', 'unknown')
        }
    
    @staticmethod
    def _generate_commit_hash(content: str) -> str:
        """コンテンツからコミットハッシュを生成"""
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    @staticmethod
    def create_backup(backup_name: str = None) -> Dict[str, Any]:
        """
        現在のデータのバックアップを作成
        
        Args:
            backup_name: バックアップ名（指定しない場合は自動生成）
            
        Returns:
            バックアップ情報
        """
        if backup_name is None:
            backup_name = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_data = {
            'name': backup_name,
            'timestamp': datetime.datetime.now().isoformat(),
            'evaluation_history': st.session_state.evaluation_history.copy(),
            'branches': {k: v.copy() for k, v in st.session_state.branches.items()},
            'tags': st.session_state.tags.copy(),
            'current_branch': st.session_state.current_branch,
            'record_count': len(st.session_state.evaluation_history)
        }
        
        return backup_data
    
    @staticmethod
    def _create_backup() -> Dict[str, Any]:
        """内部用バックアップ作成"""
        return {
            'evaluation_history': st.session_state.evaluation_history.copy(),
            'branches': {k: v.copy() for k, v in st.session_state.branches.items()},
            'tags': st.session_state.tags.copy(),
            'current_branch': st.session_state.current_branch
        }
    
    @staticmethod
    def _restore_from_backup(backup_data: Dict[str, Any]):
        """バックアップからデータを復元"""
        st.session_state.evaluation_history = backup_data['evaluation_history']
        st.session_state.branches = backup_data['branches']
        st.session_state.tags = backup_data['tags']
        st.session_state.current_branch = backup_data['current_branch']
    
    @staticmethod
    def get_data_statistics() -> Dict[str, Any]:
        """データ統計情報を取得"""
        if not st.session_state.evaluation_history:
            return {
                'total_records': 0,
                'branches': 0,
                'tags': 0,
                'total_cost': 0.0,
                'date_range': None,
                'models_used': []
            }
        
        total_cost = sum([
            execution.get('execution_cost', 0) 
            for execution in st.session_state.evaluation_history
        ])
        
        # 使用されたモデルの統計
        models_used = {}
        for execution in st.session_state.evaluation_history:
            model = execution.get('model_name', 'Unknown')
            models_used[model] = models_used.get(model, 0) + 1
        
        # 日付範囲の計算
        timestamps = [execution.get('timestamp') for execution in st.session_state.evaluation_history if execution.get('timestamp')]
        date_range = None
        if timestamps:
            try:
                dates = [
                    datetime.datetime.fromisoformat(ts.replace('Z', '+00:00')) if isinstance(ts, str) else ts 
                    for ts in timestamps
                ]
                date_range = {
                    'start': min(dates).isoformat(),
                    'end': max(dates).isoformat()
                }
            except:
                pass
        
        return {
            'total_records': len(st.session_state.evaluation_history),
            'branches': len(st.session_state.branches),
            'tags': len(st.session_state.tags),
            'total_cost': total_cost,
            'date_range': date_range,
            'models_used': models_used
        }
    
    @staticmethod
    def validate_data_integrity() -> Dict[str, Any]:
        """データの整合性をチェック"""
        issues = []
        warnings = []
        
        # 基本的な整合性チェック
        if not isinstance(st.session_state.evaluation_history, list):
            issues.append("evaluation_history がリストではありません")
        
        if not isinstance(st.session_state.branches, dict):
            issues.append("branches が辞書ではありません")
        
        if not isinstance(st.session_state.tags, dict):
            issues.append("tags が辞書ではありません")
        
        # ブランチと履歴の整合性チェック
        total_branch_records = sum(len(executions) for executions in st.session_state.branches.values())
        if total_branch_records != len(st.session_state.evaluation_history):
            warnings.append(f"ブランチ内記録数({total_branch_records})と全履歴数({len(st.session_state.evaluation_history)})が一致しません")
        
        # コミットハッシュの重複チェック
        commit_hashes = [execution.get('commit_hash') for execution in st.session_state.evaluation_history]
        if len(commit_hashes) != len(set(commit_hashes)):
            warnings.append("重複するコミットハッシュが存在します")
        
        # タグの整合性チェック
        invalid_tags = []
        for tag, commit_hash in st.session_state.tags.items():
            if not any(execution.get('commit_hash') == commit_hash for execution in st.session_state.evaluation_history):
                invalid_tags.append(tag)
        
        if invalid_tags:
            warnings.append(f"存在しないコミットを参照するタグ: {invalid_tags}")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'checked_at': datetime.datetime.now().isoformat()
        }
    
    @staticmethod
    def clear_all_data():
        """全データをクリア"""
        st.session_state.evaluation_history = []
        st.session_state.branches = {"main": []}
        st.session_state.tags = {}
        st.session_state.current_branch = "main"
    
    @staticmethod
    def get_file_suggestion(file_type: str = "json") -> str:
        """ファイル名の提案を生成"""
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        record_count = len(st.session_state.evaluation_history)
        
        if file_type.lower() == "json":
            return f"prompt_history_{timestamp}_{record_count}records.json"
        elif file_type.lower() == "csv":
            return f"prompt_execution_history_{timestamp}_{record_count}records.csv"
        else:
            return f"prompt_data_{timestamp}.{file_type}"