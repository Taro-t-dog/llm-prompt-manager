# core/workflow_manager.py (修正後)

import streamlit as st
import uuid
import datetime
import json
from typing import Dict, List, Any, Optional
import yaml
from .workflow_engine import VariableProcessor
from collections import deque
import re

class WorkflowManager:
    """ワークフローの保存、読み込み、検証、インポート/エクスポートを管理するクラス"""

    @staticmethod
    def save_workflow(workflow_definition: Dict) -> str:
        """ワークフロー定義をセッションステートに保存する"""
        workflow_id = str(uuid.uuid4())[:12]
        workflow_definition['id'] = workflow_id
        workflow_definition['created_at'] = datetime.datetime.now().isoformat()
        workflow_definition['version'] = '1.1' # Version up
        if 'user_workflows' not in st.session_state:
            st.session_state.user_workflows = {}
        st.session_state.user_workflows[workflow_id] = workflow_definition
        return workflow_id

    @staticmethod
    def get_saved_workflows() -> Dict[str, Dict]:
        """保存されている全てのワークフローを取得する"""
        return st.session_state.get('user_workflows', {})

    @staticmethod
    def get_workflow(workflow_id: str) -> Optional[Dict]:
        """IDで特定のワークフローを取得する"""
        return st.session_state.get('user_workflows', {}).get(workflow_id)

    @staticmethod
    def delete_workflow(workflow_id: str) -> bool:
        """IDで特定のワークフローを削除する"""
        if workflow_id in st.session_state.get('user_workflows', {}):
            del st.session_state.user_workflows[workflow_id]
            return True
        return False

    @staticmethod
    def duplicate_workflow(workflow_id: str, new_name: str) -> Optional[str]:
        """ワークフローを複製する"""
        original = WorkflowManager.get_workflow(workflow_id)
        if original:
            new_workflow = original.copy()
            new_workflow['name'] = new_name
            # 内部のYAML定義の名前も更新
            if 'source_yaml' in new_workflow and isinstance(new_workflow['source_yaml'], dict):
                new_workflow['source_yaml']['name'] = new_name
                
            for key in ['id', 'created_at', 'version', 'updated_at']:
                new_workflow.pop(key, None)
            return WorkflowManager.save_workflow(new_workflow)
        return None

    @staticmethod
    def update_workflow(workflow_id: str, new_definition: Dict[str, Any]) -> bool:
        """IDで指定されたワークフローを新しい定義で更新する"""
        workflows = WorkflowManager.get_saved_workflows()
        if workflow_id in workflows:
            original_workflow = workflows[workflow_id]
            original_created_at = original_workflow.get('created_at', datetime.datetime.now().isoformat())
            original_version = original_workflow.get('version', '1.0')

            new_definition['id'] = workflow_id
            new_definition['created_at'] = original_created_at
            new_definition['updated_at'] = datetime.datetime.now().isoformat()
            try:
                # バージョンをインクリメント
                new_definition['version'] = f"{float(original_version) + 0.1:.1f}"
            except (ValueError, TypeError):
                new_definition['version'] = '1.1'

            st.session_state.user_workflows[workflow_id] = new_definition
            return True
        return False

    @staticmethod
    def validate_workflow_update(workflow_id: str, new_definition: Dict) -> List[str]:
        """ワークフロー更新時のバリデーションを行う。現状は新規作成時と同じ。"""
        # 更新特有のチェックはここに実装できるが、今のところは汎用バリデーションを呼び出す
        return WorkflowManager.validate_workflow(new_definition)

    @staticmethod
    def validate_workflow(workflow_definition: Dict) -> List[str]:
        """ワークフロー定義の構造と変数の整合性を検証する"""
        errors = []
        # source_yaml が存在する場合、それを優先して検証
        if 'source_yaml' in workflow_definition and isinstance(workflow_definition.get('source_yaml'), dict):
            nodes = workflow_definition['source_yaml'].get('nodes', {})
            if not nodes:
                errors.append("ワークフロー定義に 'nodes' がありません。")
            else:
                try:
                    WorkflowManager._topological_sort(nodes)
                except ValueError as e:
                    errors.append(str(e))
                # 各ノードの依存関係の検証
                all_node_ids = set(nodes.keys())
                global_vars = set(workflow_definition.get('global_variables', []))
                for node_id, node_def in nodes.items():
                    dependencies = WorkflowManager._get_node_dependencies(node_def)
                    for dep in dependencies:
                        if dep not in all_node_ids and dep not in global_vars:
                            errors.append(f"ノード '{node_id}' に未定義の依存関係があります: '{dep}'")
            return errors

        # フォールバック (古い形式のデータ用)
        if 'name' not in workflow_definition or not workflow_definition['name'].strip():
            errors.append("必須フィールド 'name' が不足しています。")
        if 'steps' not in workflow_definition or not isinstance(workflow_definition['steps'], list):
            errors.append("必須フィールド 'steps' が空か、リスト形式ではありません。")
            return errors
        
        for i, step in enumerate(workflow_definition['steps']):
            errors.extend(WorkflowManager._validate_step(step, i + 1))
        
        return errors

    @staticmethod
    def _validate_step(step: Dict, step_number: int) -> List[str]:
        """個別のステップを検証する"""
        errors = []
        if not isinstance(step, dict):
            return [f"ステップ {step_number}: 定義が辞書形式ではありません。"]
        if 'name' not in step or not step['name'].strip():
            errors.append(f"ステップ {step_number}: 'name' が不足しています。")
        if 'prompt_template' not in step:
            errors.append(f"ステップ {step_number}: 'prompt_template' が不足しています。")
        return errors
    
    @staticmethod
    def import_from_yaml(yaml_data: str) -> Dict[str, Any]:
        """YAMLからワークフローをインポートする"""
        try:
            workflow_data = yaml.safe_load(yaml_data)
            if not isinstance(workflow_data, dict):
                return {'success': False, 'errors': ['YAMLのルートは辞書形式である必要があります。']}
            
            internal_definition, validation_errors = WorkflowManager._parse_yaml_to_internal(workflow_data)
            if validation_errors:
                return {'success': False, 'errors': validation_errors}

            workflow_id = WorkflowManager.save_workflow(internal_definition)
            return {'success': True, 'workflow_id': workflow_id, 'workflow_name': internal_definition.get('name', '無名')}

        except yaml.YAMLError as e:
            return {'success': False, 'errors': [f'YAML解析エラー: {e}']}
        except Exception as e:
            return {'success': False, 'errors': [f'インポート処理中の予期せぬエラー: {e}']}

    @staticmethod
    def export_to_yaml(workflow_id: str) -> Optional[str]:
        """ワークフローをYAML形式でエクスポートする"""
        workflow = WorkflowManager.get_workflow(workflow_id)
        if not workflow:
            return None
        
        yaml_definition = workflow.get('source_yaml')
        if not yaml_definition or not isinstance(yaml_definition, dict):
             st.error("エクスポート可能なYAML定義が見つかりません。このワークフローは古い形式の可能性があります。")
             return None

        try:
            return yaml.dump(yaml_definition, allow_unicode=True, sort_keys=False, indent=2)
        except Exception as e:
            st.error(f"YAMLエクスポートエラー: {e}")
            return None

    @staticmethod
    def _parse_yaml_to_internal(yaml_def: Dict) -> tuple[Dict, list]:
        """YAML定義を正規化された内部ワークフロー形式に変換する"""
        errors = []
        if 'name' not in yaml_def: errors.append("YAMLに 'name' フィールドがありません。")
        if 'nodes' not in yaml_def: errors.append("YAMLに 'nodes' フィールドがありません。")
        if errors: return {}, errors

        try:
            sorted_node_ids = WorkflowManager._topological_sort(yaml_def['nodes'])
        except ValueError as e:
            return {}, [f"依存関係エラー: {e}"]
        
        internal_steps = [{'name': node_id, 'prompt_template': yaml_def['nodes'][node_id].get('prompt_template', '')} for node_id in sorted_node_ids if yaml_def['nodes'][node_id].get('type') == 'llm']

        internal_def = {
            'name': yaml_def.get('name', '無名のワークフロー'),
            'description': yaml_def.get('description', ''),
            'global_variables': yaml_def.get('global_variables', []),
            'steps': internal_steps,
            'source_yaml': yaml_def
        }
        final_errors = WorkflowManager.validate_workflow(internal_def)
        return internal_def, final_errors

    @staticmethod
    def parse_builder_to_internal(name: str, desc: str, steps: List[Dict], g_vars: List[str]) -> Dict:
        """UIビルダーの情報を正規化された内部形式（YAML互換）に変換する"""
        nodes = {}
        # 👈 [修正] グローバル変数を静的ノードとして追加するロジックを削除。
        # グローバル変数は実行時に context に直接注入されるため、ノードとして定義する必要はない。

        # 各ステップをLLMノードとして追加
        step_names = [s['name'] for s in steps]
        for i, step in enumerate(steps):
            node_id = step.get('name')
            if not node_id: continue # 名前がないステップは無視

            prompt_deps = set()
            prompt = step.get('prompt_template', '')
            for var in re.findall(r'\{([^}]+)\}', prompt):
                dep_name = var.split('|')[0].strip().split('.')[0]
                # 依存先が他のステップかグローバル変数かをチェック
                if dep_name in step_names or dep_name in g_vars:
                     prompt_deps.add(dep_name)

            # UIで明示的に指定された依存関係と、プロンプトから抽出した依存関係をマージ
            all_deps = sorted(list(set(step.get('dependencies', [])) | prompt_deps))

            nodes[node_id] = {
                'type': 'llm',
                'agent': 'default', # 将来的な拡張用
                'prompt_template': step.get('prompt_template', ''),
                'inputs': [f":{dep}" for dep in all_deps]
            }
        
        # 最後のLLMノードを isResult とするロジックは維持
        llm_nodes = [s['name'] for s in steps if s.get('name')]
        if llm_nodes:
            llm_node_deps = {nid: set(WorkflowManager._get_node_dependencies(nodes[nid])) for nid in llm_nodes if nid in nodes}
            
            final_candidates = []
            for nid in llm_nodes:
                # 自分に依存しているノードが存在しないノードを探す
                is_depended_on = any(nid in deps for deps in llm_node_deps.values())
                if not is_depended_on:
                    final_candidates.append(nid)
            
            if final_candidates:
                 # 複数の終点ノードがある場合、名前順で最後のものを結果とする
                 nodes[sorted(final_candidates)[-1]]['isResult'] = True
            elif llm_nodes: # 循環などで見つからない場合は最後のステップを結果とする
                 nodes[llm_nodes[-1]]['isResult'] = True

        yaml_def = {
            'name': name,
            'description': desc,
            'global_variables': g_vars,
            'nodes': nodes
        }
        
        return {
            'name': name,
            'description': desc,
            'global_variables': g_vars,
            'steps': steps, 
            'source_yaml': yaml_def
        }

    @staticmethod
    def _topological_sort(nodes: Dict) -> List[str]:
        """ノードの依存関係を解決し、実行順序を決定する"""
        graph, in_degree = {node_id: [] for node_id in nodes}, {node_id: 0 for node_id in nodes}
        all_node_ids = set(nodes.keys())
        for node_id, node_def in nodes.items():
            dependencies = WorkflowManager._get_node_dependencies(node_def)
            for dep_id in dependencies:
                if dep_id in all_node_ids:
                    graph[dep_id].append(node_id)
                    in_degree[node_id] += 1
        
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        sorted_order = []
        while queue:
            u = queue.popleft()
            sorted_order.append(u)
            for v in graph.get(u, []):
                in_degree[v] -= 1
                if in_degree[v] == 0: queue.append(v)
        
        if len(sorted_order) == len(nodes):
            return sorted_order
        else:
            unprocessed = {node for node, degree in in_degree.items() if degree > 0}
            raise ValueError(f"ワークフローに循環依存が存在します。未処理ノード: {unprocessed}")

    @staticmethod
    def _get_node_dependencies(node_def: Dict) -> List[str]:
        """ノードの依存関係を抽出する"""
        deps = set()
        inputs = node_def.get('inputs', [])
        sources = inputs if isinstance(inputs, list) else list(inputs.values())
        for source in sources:
             if isinstance(source, str): deps.add(source.lstrip(':'))
        prompt = node_def.get('prompt_template', '')
        for var in re.findall(r'\{([^}]+)\}', prompt): deps.add(var.split('|')[0].strip().split('.')[0])
        return list(deps)