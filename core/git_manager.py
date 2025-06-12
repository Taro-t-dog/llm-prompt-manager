"""
Git風操作管理
ブランチ、コミット、タグの操作を管理する
"""

import streamlit as st
import hashlib
import datetime
from typing import Dict, List, Any, Optional


class GitManager:
    """Git風のバージョン管理機能を提供するクラス"""
    
    @staticmethod
    def initialize_session_state():
        """セッション状態を初期化"""
        if 'evaluation_history' not in st.session_state:
            st.session_state.evaluation_history = []
        if 'current_branch' not in st.session_state:
            st.session_state.current_branch = "main"
        if 'branches' not in st.session_state:
            st.session_state.branches = {"main": []}
        if 'tags' not in st.session_state:
            st.session_state.tags = {}
    
    @staticmethod
    def generate_commit_hash(content: str) -> str:
        """
        コンテンツからコミットハッシュを生成
        
        Args:
            content: ハッシュ化するコンテンツ
            
        Returns:
            8文字のコミットハッシュ
        """
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    @staticmethod
    def create_commit(data: Dict[str, Any], commit_message: str) -> Dict[str, Any]:
        """
        新しいコミット（実行記録）を作成
        
        Args:
            data: 実行データ
            commit_message: コミットメッセージ
            
        Returns:
            完成したコミット記録
        """
        commit_hash = GitManager.generate_commit_hash(str(data))
        
        execution_record = {
            **data,
            'commit_hash': commit_hash,
            'commit_message': commit_message,
            'branch': st.session_state.current_branch,
            'parent_hash': None
        }
        
        # 親コミットのハッシュを設定
        current_branch_executions = st.session_state.branches[st.session_state.current_branch]
        if current_branch_executions:
            execution_record['parent_hash'] = current_branch_executions[-1]['commit_hash']
        
        return execution_record
    
    @staticmethod
    def add_commit_to_history(execution_record: Dict[str, Any]):
        """
        コミットを履歴とブランチに追加
        
        Args:
            execution_record: 実行記録
        """
        # 全履歴に追加
        st.session_state.evaluation_history.append(execution_record)
        
        # 現在のブランチに追加
        st.session_state.branches[st.session_state.current_branch].append(execution_record)
    
    @staticmethod
    def get_current_branch() -> str:
        """現在のブランチ名を取得"""
        return st.session_state.current_branch
    
    @staticmethod
    def get_all_branches() -> List[str]:
        """全ブランチ名のリストを取得"""
        return list(st.session_state.branches.keys())
    
    @staticmethod
    def switch_branch(branch_name: str) -> bool:
        """
        ブランチを切り替え
        
        Args:
            branch_name: 切り替え先のブランチ名
            
        Returns:
            切り替えが成功したかどうか
        """
        if branch_name in st.session_state.branches:
            st.session_state.current_branch = branch_name
            return True
        return False
    
    @staticmethod
    def create_branch(branch_name: str, copy_from_current: bool = True) -> bool:
        """
        新しいブランチを作成
        
        Args:
            branch_name: 新しいブランチ名
            copy_from_current: 現在のブランチからコピーするかどうか
            
        Returns:
            作成が成功したかどうか
        """
        if branch_name in st.session_state.branches:
            return False
        
        if copy_from_current:
            # 現在のブランチからコピー
            st.session_state.branches[branch_name] = st.session_state.branches[st.session_state.current_branch].copy()
        else:
            # 空のブランチを作成
            st.session_state.branches[branch_name] = []
        
        return True
    
    @staticmethod
    def delete_branch(branch_name: str) -> bool:
        """
        ブランチを削除
        
        Args:
            branch_name: 削除するブランチ名
            
        Returns:
            削除が成功したかどうか
        """
        # mainブランチは削除できない
        if branch_name == "main":
            return False
        
        # 現在のブランチは削除できない
        if branch_name == st.session_state.current_branch:
            return False
        
        if branch_name in st.session_state.branches:
            del st.session_state.branches[branch_name]
            return True
        
        return False
    
    @staticmethod
    def get_branch_executions(branch_name: str = None) -> List[Dict[str, Any]]:
        """
        指定されたブランチの実行記録を取得
        
        Args:
            branch_name: ブランチ名（None の場合は現在のブランチ）
            
        Returns:
            実行記録のリスト
        """
        if branch_name is None:
            branch_name = st.session_state.current_branch
        
        return st.session_state.branches.get(branch_name, [])
    
    @staticmethod
    def get_branch_stats(branch_name: str = None) -> Dict[str, Any]:
        """
        ブランチの統計情報を取得
        
        Args:
            branch_name: ブランチ名（None の場合は現在のブランチ）
            
        Returns:
            統計情報の辞書
        """
        if branch_name is None:
            branch_name = st.session_state.current_branch
        
        executions = GitManager.get_branch_executions(branch_name)
        
        if not executions:
            return {
                'execution_count': 0,
                'total_cost': 0.0,
                'total_tokens': 0,
                'avg_cost': 0.0,
                'latest_commit': None
            }
        
        total_cost = sum([execution.get('total_cost', 0) for execution in executions])
        total_tokens = sum([
            execution.get('execution_tokens', 0) + execution.get('evaluation_tokens', 0) 
            for execution in executions
        ])
        
        return {
            'execution_count': len(executions),
            'total_cost': total_cost,
            'total_tokens': total_tokens,
            'avg_cost': total_cost / len(executions) if executions else 0,
            'latest_commit': executions[-1]['commit_hash'] if executions else None
        }
    
    @staticmethod
    def create_tag(tag_name: str, commit_hash: str) -> bool:
        """
        タグを作成
        
        Args:
            tag_name: タグ名
            commit_hash: 対象のコミットハッシュ
            
        Returns:
            作成が成功したかどうか
        """
        if tag_name in st.session_state.tags:
            return False
        
        # コミットハッシュが存在するかチェック
        if not GitManager.commit_exists(commit_hash):
            return False
        
        st.session_state.tags[tag_name] = commit_hash
        return True
    
    @staticmethod
    def delete_tag(tag_name: str) -> bool:
        """
        タグを削除
        
        Args:
            tag_name: 削除するタグ名
            
        Returns:
            削除が成功したかどうか
        """
        if tag_name in st.session_state.tags:
            del st.session_state.tags[tag_name]
            return True
        return False
    
    @staticmethod
    def get_all_tags() -> Dict[str, str]:
        """全タグの辞書を取得"""
        return st.session_state.tags.copy()
    
    @staticmethod
    def get_tags_for_commit(commit_hash: str) -> List[str]:
        """
        指定されたコミットのタグリストを取得
        
        Args:
            commit_hash: コミットハッシュ
            
        Returns:
            タグ名のリスト
        """
        return [tag for tag, hash_val in st.session_state.tags.items() if hash_val == commit_hash]
    
    @staticmethod
    def commit_exists(commit_hash: str) -> bool:
        """
        コミットが存在するかチェック
        
        Args:
            commit_hash: チェックするコミットハッシュ
            
        Returns:
            存在するかどうか
        """
        return any(
            execution['commit_hash'] == commit_hash 
            for execution in st.session_state.evaluation_history
        )
    
    @staticmethod
    def get_commit_by_hash(commit_hash: str) -> Optional[Dict[str, Any]]:
        """
        コミットハッシュで実行記録を取得
        
        Args:
            commit_hash: コミットハッシュ
            
        Returns:
            実行記録（見つからない場合はNone）
        """
        for execution in st.session_state.evaluation_history:
            if execution['commit_hash'] == commit_hash:
                return execution
        return None
    
    @staticmethod
    def get_branch_tree() -> Dict[str, List[Dict[str, Any]]]:
        """
        ブランチツリー構造を取得
        
        Returns:
            ブランチ名をキーとする実行記録リストの辞書
        """
        return st.session_state.branches.copy()
    
    @staticmethod
    def get_global_stats() -> Dict[str, Any]:
        """
        全体の統計情報を取得
        
        Returns:
            グローバル統計情報
        """
        total_executions = len(st.session_state.evaluation_history)
        total_branches = len(st.session_state.branches)
        total_tags = len(st.session_state.tags)
        
        total_cost = sum([
            execution.get('total_cost', 0) 
            for execution in st.session_state.evaluation_history
        ])
        
        return {
            'total_executions': total_executions,
            'total_branches': total_branches,
            'total_tags': total_tags,
            'total_cost': total_cost,
            'active_branches': len([
                branch for branch, executions in st.session_state.branches.items() 
                if executions
            ])
        }
    
    @staticmethod
    def clear_all_data():
        """全データをクリア"""
        st.session_state.evaluation_history = []
        st.session_state.branches = {"main": []}
        st.session_state.tags = {}
        st.session_state.current_branch = "main"
    
    @staticmethod
    def format_commit_message(commit_hash: str, message: str, timestamp: str, max_length: int = 50) -> str:
        """
        コミットメッセージをフォーマット
        
        Args:
            commit_hash: コミットハッシュ
            message: コミットメッセージ
            timestamp: タイムスタンプ
            max_length: メッセージの最大長
            
        Returns:
            フォーマットされたコミットメッセージ
        """
        if len(message) > max_length:
            message = message[:max_length-3] + "..."
        
        return f"{commit_hash} - {message} ({timestamp})"