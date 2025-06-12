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
        workflow_definition['version'] = '1.0'
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
            for key in ['id', 'created_at', 'version', 'updated_at']:
                new_workflow.pop(key, None)
            return WorkflowManager.save_workflow(new_workflow)
        return None

    @staticmethod
    def validate_workflow(workflow_definition: Dict) -> List[str]:
        """ワークフロー定義の構造と変数の整合性を検証する"""
        errors = []
        if 'name' not in workflow_definition or not workflow_definition['name'].strip():
            errors.append("必須フィールド 'name' が不足しています。")
        if 'steps' not in workflow_definition or not isinstance(workflow_definition['steps'], list) or not workflow_definition['steps']:
            errors.append("必須フィールド 'steps' が空か、リスト形式ではありません。")
            return errors
        
        for i, step in enumerate(workflow_definition['steps']):
            errors.extend(WorkflowManager._validate_step(step, i + 1))
        errors.extend(WorkflowManager._validate_variables(workflow_definition))
        return errors

    @staticmethod
    def _validate_step(step: Dict, step_number: int) -> List[str]:
        """個別のステップを検証する"""
        errors = []
        if not isinstance(step, dict):
            return [f"ステップ {step_number}: 定義が辞書形式ではありません。"]
        if 'name' not in step or not step['name'].strip():
            errors.append(f"ステップ {step_number}: 'name' が不足しています。")
        if 'prompt_template' not in step or not step['prompt_template'].strip():
            errors.append(f"ステップ {step_number}: 'prompt_template' が不足しています。")
        return errors

    @staticmethod
    def _validate_variables(workflow_definition: Dict) -> List[str]:
        """ワークフロー全体の変数の整合性を検証する"""
        errors, processor = [], VariableProcessor()
        global_vars = workflow_definition.get('global_variables', [])
        if not isinstance(global_vars, list):
            errors.append("'global_variables' はリスト形式である必要があります。")
            global_vars = []
        for i, step in enumerate(workflow_definition.get('steps', [])):
            available_vars = global_vars + [f'step_{j+1}_output' for j in range(i)]
            template_errors = processor.validate_template(step.get('prompt_template', ''), available_vars)
            for error in template_errors:
                errors.append(f"ステップ {i+1} ({step.get('name', '無名')}): {error}")
        return errors

    # ----------------------------------------------------------------------
    # 🆕 Phase 1: YAML インポート/エクスポート関連メソッド (修正・統合版)
    # ----------------------------------------------------------------------

    @staticmethod
    def import_from_yaml(yaml_data: str) -> Dict[str, Any]:
        """YAMLからワークフローをインポートする"""
        try:
            workflow_data = yaml.safe_load(yaml_data)
            if not isinstance(workflow_data, dict):
                return {'success': False, 'errors': ['YAMLのルートは辞書形式である必要があります。']}
            
            # YAML定義を内部形式に変換
            internal_definition, validation_errors = WorkflowManager._parse_yaml_to_internal(workflow_data)
            if validation_errors:
                return {'success': False, 'errors': validation_errors}

            # save_workflow には正規化された内部定義を渡す
            workflow_id = WorkflowManager.save_workflow(internal_definition)
            return {'success': True, 'workflow_id': workflow_id, 'workflow_name': internal_definition.get('name', '無名')}

        except yaml.YAMLError as e:
            return {'success': False, 'errors': [f'YAML解析エラー: {e}']}
        except Exception as e:
            return {'success': False, 'errors': [f'インポート処理中の予期せぬエラー: {e}']}

    @staticmethod
    def export_to_yaml(workflow_id: str) -> Optional[str]:
        """ワークフローをYAML形式でエクスポートする（改善版）"""
        workflow = WorkflowManager.get_workflow(workflow_id)
        if not workflow:
            return None
        
        # 内部形式をYAML形式に変換する
        yaml_definition = WorkflowManager.parse_internal_to_yaml(workflow)
        try:
            return yaml.dump(yaml_definition, allow_unicode=True, sort_keys=False, indent=2)
        except Exception as e:
            st.error(f"YAMLエクスポートエラー: {e}")
            return None

    @staticmethod
    def _parse_yaml_to_internal(yaml_def: Dict) -> tuple[Dict, list]:
        """YAML定義を正規化された内部ワークフロー形式に変換する"""
        errors = []
        if 'name' not in yaml_def:
            errors.append("YAMLに 'name' フィールドがありません。")
        if 'nodes' not in yaml_def:
            errors.append("YAMLに 'nodes' フィールドがありません。")
        if errors:
            return {}, errors

        try:
            sorted_node_ids = WorkflowManager._topological_sort(yaml_def['nodes'])
        except ValueError as e:
            return {}, [f"依存関係エラー: {e}"]
        
        internal_steps = [
            {'name': node_id, 'prompt_template': yaml_def['nodes'][node_id].get('prompt_template', '')}
            for node_id in sorted_node_ids if yaml_def['nodes'][node_id].get('type') == 'llm'
        ]

        internal_def = {
            'name': yaml_def.get('name', '無名のワークフロー'),
            'description': yaml_def.get('description', ''),
            'global_variables': yaml_def.get('global_variables', []),
            'steps': internal_steps,
            'source_yaml': yaml_def  # 元のYAML構造を保持
        }
        return internal_def, []

    @staticmethod
    def parse_internal_to_yaml(internal_def: Dict) -> Dict:
        """内部ワークフロー形式をYAML定義に変換する（改善版）"""
        # YAMLからインポートされた場合、元の構造を優先的に返す
        if 'source_yaml' in internal_def and internal_def['source_yaml']:
            return internal_def['source_yaml']

        # UIビルダーで作成されたワークフローをエクスポートするためのロジック
        nodes, global_vars = {}, internal_def.get('global_variables', [])
        for var in global_vars:
            nodes[var] = {'type': 'static', 'value': f'{{{var}}}'}
        
        step_outputs = {}
        for i, step in enumerate(internal_def.get('steps', [])):
            node_id = step.get('name', f'step_{i+1}')
            step_outputs[f"step_{i+1}_output"] = node_id
            
            prompt_template, inputs = step.get('prompt_template', ''), []
            used_vars = re.findall(r'\{([^}]+)\}', prompt_template)
            
            for var in set(used_vars):
                if var in step_outputs:
                    inputs.append(f":{step_outputs[var]}")
                elif var in global_vars and f":{var}" not in inputs:
                    inputs.append(f":{var}")

            if not inputs and i > 0:
                prev_node_id = internal_def['steps'][i-1].get('name', f'step_{i}')
                inputs.append(f":{prev_node_id}")
            
            nodes[node_id] = {
                'type': 'llm',
                'agent': 'default',
                'prompt_template': prompt_template,
                'inputs': sorted(list(set(inputs)))
            }
            if i == len(internal_def.get('steps', [])) - 1:
                nodes[node_id]['isResult'] = True

        return {
            'name': internal_def['name'],
            'description': internal_def.get('description', ''),
            'global_variables': global_vars,
            'nodes': nodes
        }

    @staticmethod
    def _topological_sort(nodes: Dict) -> List[str]:
        """ノードの依存関係を解決し、実行順序を決定する"""
        graph, in_degree = {node_id: [] for node_id in nodes}, {node_id: 0 for node_id in nodes}
        for node_id, node_def in nodes.items():
            if node_def.get('type') != 'llm':
                continue
            inputs = node_def.get('inputs', [])
            sources = []
            if isinstance(inputs, list):
                sources = inputs
            elif isinstance(inputs, dict):
                sources = list(inputs.values())
            
            for source in sources:
                source_id = source.lstrip(':')
                if source_id not in graph:
                    raise ValueError(f"'{node_id}'が未定義のノード'{source_id}'に依存")
                graph[source_id].append(node_id)
                in_degree[node_id] += 1
        
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        sorted_order = []
        while queue:
            u = queue.popleft()
            sorted_order.append(u)
            for v in graph.get(u, []):
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)
        
        if len(sorted_order) == len(nodes):
            return sorted_order
        else:
            raise ValueError("ワークフローに循環依存が存在します。")