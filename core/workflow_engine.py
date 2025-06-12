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
from dataclasses import dataclass
from enum import Enum
import streamlit as st
from .git_manager import GitManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    PENDING, RUNNING, COMPLETED, FAILED, CANCELLED = "pending", "running", "completed", "failed", "cancelled"
    def __str__(self): return self.value

@dataclass
class StepResult:
    success: bool; step_number: int; step_name: str; prompt: str; response: str;
    tokens: int; cost: float; execution_time: float; error: Optional[str] = None;
    git_record: Optional[Dict] = None; metadata: Optional[Dict] = None; model_name: Optional[str] = None

@dataclass
class WorkflowExecutionResult:
    success: bool; execution_id: str; workflow_name: str; start_time: datetime.datetime;
    end_time: Optional[datetime.datetime]; duration_seconds: float; status: ExecutionStatus;
    steps: List[StepResult]; total_cost: float; total_tokens: int; final_output: Optional[str];
    error: Optional[str] = None; metadata: Optional[Dict] = None

class VariableProcessor:
    def __init__(self): self.variable_pattern = re.compile(r'\{([^}]+)\}')
    def substitute_variables(self, template: str, context: Dict[str, Any]) -> str:
        return self.variable_pattern.sub(lambda m: self._process_variable_expression(m.group(1), context), template)
    def _process_variable_expression(self, expression: str, context: Dict[str, Any]) -> str:
        if '|' in expression:
            var_part, filters = expression.split('|', 1); value = self._get_variable_value(var_part.strip(), context); return self._apply_filters(value, filters)
        return self._get_variable_value(expression, context)
    def _get_variable_value(self, var_name: str, context: Dict[str, Any]) -> str:
        if '.' in var_name: base_var, section = var_name.split('.', 1); return self._extract_section(str(context.get(base_var, '')), section)
        return str(context.get(var_name, ''))
    def _extract_section(self, text: str, section_name: str) -> str:
        match = re.search(rf'#{{1,3}}\s*{re.escape(section_name)}[^\n]*\n(.*?)(?=\n#{{1,3}}|\Z)', text, re.I | re.S); return match.group(1).strip() if match else text
    def _apply_filters(self, value: str, filters: str) -> str:
        for f_expr in filters.split('|'):
            f_expr = f_expr.strip()
            if ':' in f_expr: f_name, param = f_expr.split(':', 1); value = self._apply_single_filter(value, f_name.strip(), param.strip())
            else: value = self._apply_single_filter(value, f_expr, None)
        return value
    def _apply_single_filter(self, val: str, name: str, param: Optional[str]) -> str:
        if name == 'default' and param and not val: return param
        if name == 'upper': return val.upper()
        if name == 'lower': return val.lower()
        if name == 'strip': return val.strip()
        if name == 'first_line': return val.split('\n')[0] if val else ''
        if name == 'truncate' and param and param.isdigit(): length = int(param); return val[:length] + '...' if len(val) > length else val
        return val
    def validate_template(self, template: str, available_vars: List[str]) -> List[str]:
        return [f"未定義の変数: {v.split('|')[0].split('.')[0]}" for v in self.variable_pattern.findall(template) if v.split('|')[0].split('.')[0] not in available_vars]

class WorkflowErrorHandler:
    def categorize_error(self, err_msg: str) -> Tuple[str, str, List[str]]: return 'unknown', err_msg, ['エラー内容を確認して再試行してください。']

class WorkflowEngine:
    def __init__(self, llm_evaluator, max_retries: int = 3):
        self.evaluator, self.max_retries = llm_evaluator, max_retries
        self.variable_processor, self.error_handler = VariableProcessor(), WorkflowErrorHandler()
    
    def execute_workflow(self, wf_config, inputs, progress_callback=None):
        exec_id, start_time = str(uuid.uuid4())[:12], datetime.datetime.now()
        state = {'execution_id': exec_id, 'workflow_name': wf_config.get('name', '無名'), 'status': ExecutionStatus.RUNNING, 'total_steps': len(wf_config.get('steps', []))}
        if progress_callback: progress_callback(state)
        
        results, context = [], inputs.copy()
        try:
            for i, step_config in enumerate(wf_config.get('steps', [])):
                if progress_callback: state.update({'current_step': i + 1, 'step_name': step_config.get('name', f'Step {i+1}')}); progress_callback(state)
                step_result = self._execute_step_with_retry(step_config, context, i + 1, exec_id, wf_config.get('name', '無名'))
                results.append(step_result)
                if not step_result.success: return self._create_failure_result(exec_id, wf_config.get('name','無名'), start_time, step_result.error, results)
                context[f'step_{i+1}_output'] = step_result.response
                if step_result.git_record: GitManager.add_commit_to_history(step_result.git_record)
            if progress_callback: state.update({'status': ExecutionStatus.COMPLETED}); progress_callback(state)
            return self._create_success_result(exec_id, wf_config.get('name','無名'), start_time, results)
        except Exception as e:
            if progress_callback: state.update({'status': ExecutionStatus.FAILED, 'error': str(e)}); progress_callback(state)
            return self._create_failure_result(exec_id, wf_config.get('name','無名'), start_time, str(e), results)

    def _execute_step_with_retry(self, step_config, context, step_num, exec_id, wf_name, use_cache=True, auto_retry=True):
        attempt, last_error = 0, None
        while attempt < (self.max_retries if auto_retry else 1):
            try:
                attempt += 1; step_start_time = time.time()
                prompt = self.variable_processor.substitute_variables(step_config.get('prompt_template', ''), context)
                llm_res = self.evaluator.execute_prompt(prompt)
                if not llm_res.get('success'): raise Exception(llm_res.get('error', 'LLM実行失敗'))
                res = self._create_step_result(step_config, step_num, exec_id, wf_name, prompt, llm_res, True, model_name=llm_res.get('model_name'))
                res.execution_time = time.time() - step_start_time; return res
            except Exception as e:
                last_error = str(e); logger.warning(f"Step {step_num} (Attempt {attempt}) failed: {last_error}")
                if attempt >= (self.max_retries if auto_retry else 1): break
                time.sleep(2 ** attempt)
        failed_prompt = self.variable_processor.substitute_variables(step_config.get('prompt_template', ''), context)
        failed_res = self._create_step_result(step_config, step_num, exec_id, wf_name, failed_prompt, None, False, last_error)
        failed_res.execution_time = time.time() - (step_start_time if 'step_start_time' in locals() else time.time()); return failed_res

    def _create_step_result(self, config, num, exec_id, wf_name, prompt, llm_res, success, error=None, model_name=None):
        data = {'success': success, 'step_number': num, 'step_name': config.get('name', ''), 'prompt': prompt,
                'response': llm_res.get('response_text', '') if success else '', 'tokens': llm_res.get('total_tokens', 0) if success else 0,
                'cost': llm_res.get('cost_usd', 0.0) if success else 0.0, 'execution_time': 0, 'error': error,
                'model_name': model_name or (llm_res.get('model_name') if success else None)}
        if success and llm_res:
            git_data = {'timestamp': datetime.datetime.now(), 'execution_mode': 'Workflow Step', 'final_prompt': prompt,
                        'response': llm_res.get('response_text'), 'evaluation': f'Step {num}: {config.get("name")}', 'execution_tokens': llm_res.get('total_tokens', 0),
                        'evaluation_tokens': 0, 'execution_cost': llm_res.get('cost_usd', 0.0), 'evaluation_cost': 0.0, 'total_cost': llm_res.get('cost_usd', 0.0),
                        'model_name': llm_res.get('model_name'), 'model_id': llm_res.get('model_id'), 'api_provider': llm_res.get('api_provider'),
                        'workflow_execution_id': exec_id, 'workflow_name': wf_name, 'step_number': num, 'step_name': config.get('name')}
            data['git_record'] = GitManager.create_commit(git_data, f'WF-Step: {wf_name} - {config.get("name")}')
        return StepResult(**data)

    def _create_workflow_summary_record(self, result: WorkflowExecutionResult) -> Dict:
        summary_data = {'timestamp': result.end_time, 'execution_mode': 'Workflow Summary', 'workflow_execution_id': result.execution_id,
                        'workflow_name': result.workflow_name, 'final_prompt': f"Workflow: {result.workflow_name}", 'response': result.final_output,
                        'evaluation': f"Workflow {'Completed' if result.success else 'Failed'}: {len(result.steps)} steps in {result.duration_seconds:.1f}s. Error: {result.error or 'None'}",
                        'execution_tokens': result.total_tokens, 'evaluation_tokens': 0, 'execution_cost': result.total_cost, 'evaluation_cost': 0.0,
                        'total_cost': result.total_cost, 'model_name': "Workflow", 'api_provider': 'workflow'}
        commit_message = f"WF-Summary: {result.workflow_name} ({'Success' if result.success else 'Failed'})"
        summary_record = GitManager.create_commit(summary_data, commit_message)
        GitManager.add_commit_to_history(summary_record); return summary_record

    def _create_success_result(self, exec_id, wf_name, start_time, steps):
        end_time = datetime.datetime.now()
        result = WorkflowExecutionResult(success=True, execution_id=exec_id, workflow_name=wf_name, start_time=start_time, end_time=end_time,
                                     duration_seconds=(end_time - start_time).total_seconds(), status=ExecutionStatus.COMPLETED, steps=steps,
                                     total_cost=sum(s.cost for s in steps), total_tokens=sum(s.tokens for s in steps), final_output=steps[-1].response if steps else None)
        self._create_workflow_summary_record(result); return result

    def _create_failure_result(self, exec_id, wf_name, start_time, error, completed_steps):
        end_time = datetime.datetime.now()
        result = WorkflowExecutionResult(success=False, execution_id=exec_id, workflow_name=wf_name, start_time=start_time, end_time=end_time,
                                     duration_seconds=(end_time - start_time).total_seconds(), status=ExecutionStatus.FAILED, steps=completed_steps,
                                     total_cost=sum(s.cost for s in completed_steps), total_tokens=sum(s.tokens for s in completed_steps),
                                     final_output=None, error=error)
        self._create_workflow_summary_record(result); return result