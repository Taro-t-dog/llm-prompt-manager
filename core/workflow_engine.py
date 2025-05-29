"""
汎用多段階LLM処理エンジン
高度な変数置換、エラーハンドリング、実行速度最適化を実装
"""
import uuid
import datetime
import re
import json
import time
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import streamlit as st
from core import GitManager
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    """実行状態"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class StepResult:
    """ステップ実行結果"""
    success: bool
    step_number: int
    step_name: str
    prompt: str
    response: str
    tokens: int
    cost: float
    execution_time: float
    error: Optional[str] = None
    git_record: Optional[Dict] = None
    metadata: Optional[Dict] = None

@dataclass
class WorkflowExecutionResult:
    """ワークフロー実行結果"""
    success: bool
    execution_id: str
    workflow_name: str
    start_time: datetime.datetime
    end_time: Optional[datetime.datetime]
    duration_seconds: float
    status: ExecutionStatus
    steps: List[StepResult]
    total_cost: float
    total_tokens: int
    final_output: Optional[str]
    error: Optional[str] = None
    metadata: Optional[Dict] = None

class VariableProcessor:
    """高度な変数置換処理クラス"""
    
    def __init__(self):
        # 変数パターン: {variable}, {step_N_output}, {step_N_output.section}
        self.variable_pattern = re.compile(r'\{([^}]+)\}')
        self.section_pattern = re.compile(r'([^.]+)\.(.+)')
    
    def substitute_variables(self, template: str, context: Dict[str, Any]) -> str:
        """
        高度な変数置換
        
        サポートする形式:
        - {variable_name} - 基本変数
        - {step_1_output} - ステップ出力
        - {step_1_output.section} - セクション抽出
        - {variable_name|default:デフォルト値} - デフォルト値
        - {variable_name|upper} - 大文字変換
        - {variable_name|truncate:100} - 文字数制限
        """
        def replace_variable(match):
            var_expression = match.group(1)
            return self._process_variable_expression(var_expression, context)
        
        try:
            result = self.variable_pattern.sub(replace_variable, template)
            return result
        except Exception as e:
            logger.error(f"Variable substitution error: {e}")
            return template
    
    def _process_variable_expression(self, expression: str, context: Dict[str, Any]) -> str:
        """変数式を処理"""
        # パイプによるフィルター処理
        if '|' in expression:
            var_part, filters = expression.split('|', 1)
            value = self._get_variable_value(var_part.strip(), context)
            return self._apply_filters(value, filters, context)
        else:
            return self._get_variable_value(expression, context)
    
    def _get_variable_value(self, var_name: str, context: Dict[str, Any]) -> str:
        """変数値を取得"""
        # セクション指定の処理
        if '.' in var_name:
            section_match = self.section_pattern.match(var_name)
            if section_match:
                base_var = section_match.group(1)
                section_name = section_match.group(2)
                base_value = context.get(base_var, '')
                return self._extract_section(str(base_value), section_name)
        
        # 通常の変数取得
        value = context.get(var_name, '')
        return str(value)
    
    def _extract_section(self, text: str, section_name: str) -> str:
        """テキストからセクションを抽出"""
        try:
            # マークダウン形式のセクション抽出
            section_patterns = [
                rf'#{{{1,3}}}\s*{re.escape(section_name)}[^\n]*\n(.*?)(?=\n#{{{1,3}}}|\Z)',
                rf'{re.escape(section_name)}[:\n](.*?)(?=\n[A-Z]|\Z)'
            ]
            
            for pattern in section_patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    return match.group(1).strip()
            
            return text  # セクションが見つからない場合は全体を返す
        except Exception as e:
            logger.warning(f"Section extraction error for '{section_name}': {e}")
            return text
    
    def _apply_filters(self, value: str, filters: str, context: Dict[str, Any]) -> str:
        """フィルターを適用"""
        try:
            for filter_expr in filters.split('|'):
                filter_expr = filter_expr.strip()
                if ':' in filter_expr:
                    filter_name, param = filter_expr.split(':', 1)
                    value = self._apply_single_filter(value, filter_name.strip(), param.strip())
                else:
                    value = self._apply_single_filter(value, filter_expr, None)
            return value
        except Exception as e:
            logger.warning(f"Filter application error: {e}")
            return value
    
    def _apply_single_filter(self, value: str, filter_name: str, param: Optional[str]) -> str:
        """単一フィルターを適用"""
        if filter_name == 'default' and param and not value:
            return param
        elif filter_name == 'upper':
            return value.upper()
        elif filter_name == 'lower':
            return value.lower()
        elif filter_name == 'truncate' and param:
            try:
                length = int(param)
                return value[:length] + '...' if len(value) > length else value
            except ValueError:
                return value
        elif filter_name == 'strip':
            return value.strip()
        elif filter_name == 'first_line':
            return value.split('\n')[0] if value else ''
        else:
            return value
    
    def validate_template(self, template: str, available_vars: List[str]) -> List[str]:
        """テンプレートの変数使用を検証"""
        errors = []
        variables_used = self.variable_pattern.findall(template)
        
        for var_expr in variables_used:
            var_name = var_expr.split('|')[0].split('.')[0]
            if var_name not in available_vars:
                errors.append(f"未定義の変数: {var_name}")
        
        return errors

class WorkflowErrorHandler:
    """汎用エラーハンドリングクラス"""
    
    def __init__(self):
        self.error_patterns = {
            'api_rate_limit': re.compile(r'rate.?limit|quota.?exceeded', re.IGNORECASE),
            'api_timeout': re.compile(r'timeout|timed.?out', re.IGNORECASE),
            'api_auth': re.compile(r'auth|unauthorized|invalid.?key', re.IGNORECASE),
            'token_limit': re.compile(r'token.?limit|max.?tokens', re.IGNORECASE),
            'content_filter': re.compile(r'content.?filter|blocked|inappropriate', re.IGNORECASE)
        }
    
    def categorize_error(self, error_message: str) -> Tuple[str, str, List[str]]:
        """
        エラーを分類し、対処法を提案
        
        Returns:
            (error_type, description, suggested_actions)
        """
        error_msg_lower = error_message.lower()
        
        for error_type, pattern in self.error_patterns.items():
            if pattern.search(error_msg_lower):
                return self._get_error_info(error_type, error_message)
        
        return 'unknown', 'Unknown error occurred', ['Check the error message and try again']
    
    def _get_error_info(self, error_type: str, original_error: str) -> Tuple[str, str, List[str]]:
        """エラータイプごとの情報を取得"""
        error_info = {
            'api_rate_limit': (
                'APIレート制限',
                'API呼び出し回数が制限に達しました',
                [
                    '数分間待ってから再実行',
                    '自動リトライを有効化',
                    'プロンプトを短縮してトークン数を削減',
                    '異なるモデルを使用'
                ]
            ),
            'api_timeout': (
                'APIタイムアウト',
                'API応答時間が制限を超えました', 
                [
                    'プロンプトを短縮',
                    '再実行を試行',
                    'ネットワーク接続を確認'
                ]
            ),
            'api_auth': (
                '認証エラー',
                'APIキーが無効または期限切れです',
                [
                    'APIキーを確認・更新',
                    'API権限を確認',
                    'アカウント状態を確認'
                ]
            ),
            'token_limit': (
                'トークン制限超過',
                'プロンプトまたは応答が長すぎます',
                [
                    'プロンプトを短縮',
                    '入力データを分割',
                    '異なるモデルを使用'
                ]
            ),
            'content_filter': (
                'コンテンツフィルター',
                '内容がポリシー違反と判定されました',
                [
                    'プロンプト内容を確認・修正',
                    '入力データを見直し',
                    '異なる表現を使用'
                ]
            )
        }
        
        if error_type in error_info:
            return error_info[error_type]
        else:
            return 'unknown', original_error, ['エラー内容を確認して再試行']
    
    def should_retry(self, error_type: str, attempt_count: int) -> bool:
        """リトライすべきかを判定"""
        retry_policies = {
            'api_rate_limit': attempt_count < 3,
            'api_timeout': attempt_count < 2,
            'token_limit': False,  # プロンプト修正が必要
            'content_filter': False,  # プロンプト修正が必要
            'api_auth': False  # 認証修正が必要
        }
        
        return retry_policies.get(error_type, attempt_count < 1)
    
    def get_retry_delay(self, error_type: str, attempt_count: int) -> float:
        """リトライ間隔を取得（指数バックオフ）"""
        base_delays = {
            'api_rate_limit': 60,  # 1分
            'api_timeout': 10,     # 10秒
            'unknown': 5           # 5秒
        }
        
        base_delay = base_delays.get(error_type, 5)
        return base_delay * (2 ** (attempt_count - 1))

class WorkflowEngine:
    """汎用ワークフロー実行エンジン"""
    
    def __init__(self, llm_evaluator, max_retries: int = 3):
        self.evaluator = llm_evaluator
        self.max_retries = max_retries
        self.variable_processor = VariableProcessor()
        self.error_handler = WorkflowErrorHandler()
        self._execution_cache = {}
    
    def execute_workflow(self, workflow_config: Dict, input_data: Dict, 
                        progress_callback: Optional[Callable] = None) -> WorkflowExecutionResult:
        """
        ワークフローを実行（進捗コールバック対応）
        """
        execution_id = self._generate_execution_id()
        start_time = datetime.datetime.now()
        
        # 実行状態を初期化
        execution_state = {
            'execution_id': execution_id,
            'workflow_name': workflow_config['name'],
            'status': ExecutionStatus.RUNNING,
            'current_step': 0,
            'total_steps': len(workflow_config['steps']),
            'start_time': start_time
        }
        
        if progress_callback:
            progress_callback(execution_state)
        
        try:
            result = self._execute_workflow_steps(
                workflow_config, input_data, execution_id, progress_callback
            )
            
            execution_state['status'] = ExecutionStatus.COMPLETED if result.success else ExecutionStatus.FAILED
            if progress_callback:
                progress_callback(execution_state)
                
            return result
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            execution_state['status'] = ExecutionStatus.FAILED
            if progress_callback:
                progress_callback(execution_state)
                
            return WorkflowExecutionResult(
                success=False,
                execution_id=execution_id,
                workflow_name=workflow_config['name'],
                start_time=start_time,
                end_time=datetime.datetime.now(),
                duration_seconds=0,
                status=ExecutionStatus.FAILED,
                steps=[],
                total_cost=0,
                total_tokens=0,
                final_output=None,
                error=str(e)
            )
    
    def _execute_workflow_steps(self, workflow_config: Dict, input_data: Dict, 
                               execution_id: str, progress_callback: Optional[Callable]) -> WorkflowExecutionResult:
        """ワークフローステップを実行"""
        start_time = datetime.datetime.now()
        results = []
        context = input_data.copy()
        
        for step_index, step_config in enumerate(workflow_config['steps']):
            step_start_time = time.time()
            
            # 進捗更新
            if progress_callback:
                progress_callback({
                    'execution_id': execution_id,
                    'current_step': step_index + 1,
                    'step_name': step_config['name'],
                    'status': ExecutionStatus.RUNNING
                })
            
            # ステップ実行（リトライ機能付き）
            step_result = self._execute_step_with_retry(
                step_config, context, step_index + 1, execution_id, workflow_config['name']
            )
            
            step_result.execution_time = time.time() - step_start_time
            results.append(step_result)
            
            if not step_result.success:
                return self._create_failure_result(
                    execution_id, workflow_config['name'], start_time, 
                    step_result.error, results
                )
            
            # 次ステップ用にコンテキスト更新
            context[f'step_{step_index + 1}_output'] = step_result.response
            
            # Git履歴に記録
            if step_result.git_record:
                GitManager.add_commit_to_history(step_result.git_record)
        
        return self._create_success_result(execution_id, workflow_config['name'], start_time, results)
    
    def _execute_step_with_retry(self, step_config: Dict, context: Dict, 
                               step_number: int, execution_id: str, workflow_name: str) -> StepResult:
        """リトライ機能付きステップ実行"""
        attempt = 0
        last_error = None
        
        while attempt < self.max_retries:
            try:
                attempt += 1
                
                # キャッシュチェック
                cache_key = self._generate_cache_key(step_config, context)
                if cache_key in self._execution_cache:
                    cached_result = self._execution_cache[cache_key]
                    logger.info(f"Using cached result for step {step_number}")
                    return cached_result
                
                # プロンプト生成
                final_prompt = self.variable_processor.substitute_variables(
                    step_config['prompt_template'], context
                )
                
                # LLM実行
                llm_result = self.evaluator.execute_prompt(final_prompt)
                
                if not llm_result['success']:
                    raise Exception(llm_result.get('error', 'LLM execution failed'))
                
                # 成功結果の作成
                step_result = self._create_step_result(
                    step_config, step_number, execution_id, workflow_name,
                    final_prompt, llm_result, True
                )
                
                # キャッシュに保存
                self._execution_cache[cache_key] = step_result
                
                return step_result
                
            except Exception as e:
                last_error = str(e)
                error_type, _, _ = self.error_handler.categorize_error(last_error)
                
                if not self.error_handler.should_retry(error_type, attempt):
                    break
                
                if attempt < self.max_retries:
                    delay = self.error_handler.get_retry_delay(error_type, attempt)
                    logger.info(f"Retrying step {step_number} after {delay} seconds (attempt {attempt + 1})")
                    time.sleep(delay)
        
        # 失敗結果の作成
        return self._create_step_result(
            step_config, step_number, execution_id, workflow_name,
            '', None, False, last_error
        )
    
    def _create_step_result(self, step_config: Dict, step_number: int, execution_id: str,
                          workflow_name: str, prompt: str, llm_result: Optional[Dict],
                          success: bool, error: Optional[str] = None) -> StepResult:
        """ステップ結果を作成"""
        if success and llm_result:
            # Git記録作成
            git_record = GitManager.create_commit({
                'timestamp': datetime.datetime.now(),
                'execution_mode': f'Workflow Step {step_number}',
                'final_prompt': prompt,
                'response': llm_result['response_text'],
                'evaluation': f'Step {step_number}: {step_config["name"]}',
                'execution_tokens': llm_result['total_tokens'],
                'evaluation_tokens': 0,
                'execution_cost': llm_result['cost_usd'],
                'evaluation_cost': 0.0,
                'total_cost': llm_result['cost_usd'],
                'model_name': llm_result['model_name'],
                'model_id': llm_result['model_id'],
                'workflow_id': execution_id,
                'step_number': step_number
            }, f'Workflow: {workflow_name} - {step_config["name"]}')
            
            return StepResult(
                success=True,
                step_number=step_number,
                step_name=step_config['name'],
                prompt=prompt,
                response=llm_result['response_text'],
                tokens=llm_result['total_tokens'],
                cost=llm_result['cost_usd'],
                execution_time=0,  # 後で設定
                git_record=git_record
            )
        else:
            return StepResult(
                success=False,
                step_number=step_number,
                step_name=step_config['name'],
                prompt=prompt,
                response='',
                tokens=0,
                cost=0,
                execution_time=0,
                error=error
            )
    
    def _generate_cache_key(self, step_config: Dict, context: Dict) -> str:
        """キャッシュキーを生成"""
        import hashlib
        content = json.dumps({
            'template': step_config['prompt_template'],
            'context': {k: str(v)[:100] for k, v in context.items()}  # 最初の100文字のみ
        }, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _generate_execution_id(self) -> str:
        """実行IDを生成"""
        return str(uuid.uuid4())[:12]
    
    def _create_success_result(self, execution_id: str, workflow_name: str,
                             start_time: datetime.datetime, steps: List[StepResult]) -> WorkflowExecutionResult:
        """成功結果を作成"""
        end_time = datetime.datetime.now()
        return WorkflowExecutionResult(
            success=True,
            execution_id=execution_id,
            workflow_name=workflow_name,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=(end_time - start_time).total_seconds(),
            status=ExecutionStatus.COMPLETED,
            steps=steps,
            total_cost=sum(step.cost for step in steps),
            total_tokens=sum(step.tokens for step in steps),
            final_output=steps[-1].response if steps else None
        )
    
    def _create_failure_result(self, execution_id: str, workflow_name: str,
                             start_time: datetime.datetime, error: str, 
                             completed_steps: List[StepResult]) -> WorkflowExecutionResult:
        """失敗結果を作成"""
        return WorkflowExecutionResult(
            success=False,
            execution_id=execution_id,
            workflow_name=workflow_name,
            start_time=start_time,
            end_time=datetime.datetime.now(),
            duration_seconds=0,
            status=ExecutionStatus.FAILED,
            steps=completed_steps,
            total_cost=sum(step.cost for step in completed_steps),
            total_tokens=sum(step.tokens for step in completed_steps),
            final_output=None,
            error=error
        )
    
    def clear_cache(self):
        """実行キャッシュをクリア"""
        self._execution_cache.clear()

class WorkflowManager:
    """ワークフロー管理クラス"""
    
    @staticmethod
    def save_workflow(workflow_definition: Dict) -> str:
        """ワークフローを保存"""
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
        """保存済みワークフロー一覧を取得"""
        return st.session_state.get('user_workflows', {})
    
    @staticmethod
    def get_workflow(workflow_id: str) -> Optional[Dict]:
        """特定ワークフローを取得"""
        workflows = st.session_state.get('user_workflows', {})
        return workflows.get(workflow_id)
    
    @staticmethod
    def update_workflow(workflow_id: str, workflow_definition: Dict) -> bool:
        """ワークフローを更新"""
        if workflow_id in st.session_state.get('user_workflows', {}):
            workflow_definition['id'] = workflow_id
            workflow_definition['updated_at'] = datetime.datetime.now().isoformat()
            st.session_state.user_workflows[workflow_id] = workflow_definition
            return True
        return False
    
    @staticmethod
    def delete_workflow(workflow_id: str) -> bool:
        """ワークフローを削除"""
        if workflow_id in st.session_state.get('user_workflows', {}):
            del st.session_state.user_workflows[workflow_id]
            return True
        return False
    
    @staticmethod
    def duplicate_workflow(workflow_id: str, new_name: str) -> Optional[str]:
        """ワークフローを複製"""
        original = WorkflowManager.get_workflow(workflow_id)
        if original:
            new_workflow = original.copy()
            new_workflow['name'] = new_name
            return WorkflowManager.save_workflow(new_workflow)
        return None
    
    @staticmethod
    def validate_workflow(workflow_definition: Dict) -> List[str]:
        """ワークフロー定義を検証"""
        errors = []
        
        # 基本フィールドチェック
        required_fields = ['name', 'steps']
        for field in required_fields:
            if field not in workflow_definition or not workflow_definition[field]:
                errors.append(f"必須フィールド '{field}' が不足しています")
        
        # ステップ検証
        if 'steps' in workflow_definition:
            steps = workflow_definition['steps']
            if not isinstance(steps, list) or len(steps) == 0:
                errors.append("少なくとも1つのステップが必要です")
            else:
                for i, step in enumerate(steps):
                    step_errors = WorkflowManager._validate_step(step, i + 1)
                    errors.extend(step_errors)
        
        # 変数整合性チェック
        if 'steps' in workflow_definition and 'global_variables' in workflow_definition:
            variable_errors = WorkflowManager._validate_variables(workflow_definition)
            errors.extend(variable_errors)
        
        return errors
    
    @staticmethod
    def _validate_step(step: Dict, step_number: int) -> List[str]:
        """個別ステップを検証"""
        errors = []
        
        required_step_fields = ['name', 'prompt_template']
        for field in required_step_fields:
            if field not in step or not step[field].strip():
                errors.append(f"ステップ {step_number}: 必須フィールド '{field}' が不足しています")
        
        return errors
    
    @staticmethod
    def _validate_variables(workflow_definition: Dict) -> List[str]:
        """変数の整合性を検証"""
        errors = []
        processor = VariableProcessor()
        
        global_vars = workflow_definition.get('global_variables', [])
        
        for i, step in enumerate(workflow_definition['steps']):
            # 利用可能変数リストを作成
            available_vars = global_vars.copy()
            if i > 0:
                available_vars.extend([f'step_{j+1}_output' for j in range(i)])
            
            # テンプレート検証
            template_errors = processor.validate_template(
                step['prompt_template'], available_vars
            )
            
            for error in template_errors:
                errors.append(f"ステップ {i+1} ({step['name']}): {error}")
        
        return errors
    
    @staticmethod
    def export_workflow(workflow_id: str) -> Optional[str]:
        """ワークフローをJSON形式でエクスポート"""
        workflow = WorkflowManager.get_workflow(workflow_id)
        if workflow:
            return json.dumps(workflow, ensure_ascii=False, indent=2)
        return None
    
    @staticmethod
    def import_workflow(json_data: str) -> Dict[str, Any]:
        """JSONからワークフローをインポート"""
        try:
            workflow_data = json.loads(json_data)
            
            # 検証
            errors = WorkflowManager.validate_workflow(workflow_data)
            if errors:
                return {'success': False, 'errors': errors}
            
            # 保存
            workflow_id = WorkflowManager.save_workflow(workflow_data)
            return {
                'success': True, 
                'workflow_id': workflow_id,
                'workflow_name': workflow_data['name']
            }
            
        except json.JSONDecodeError as e:
            return {'success': False, 'errors': [f'JSON解析エラー: {str(e)}']}
        except Exception as e:
            return {'success': False, 'errors': [f'インポートエラー: {str(e)}']}
