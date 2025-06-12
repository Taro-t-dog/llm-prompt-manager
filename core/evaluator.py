"""
Gemini AI評価エンジン (改訂版)
"""

import google.generativeai as genai
from typing import Dict, Any, Optional

class GeminiEvaluator:
    """Gemini APIを使用したプロンプト評価システム"""

    def __init__(self, api_key: str, model_config: dict):
        self.api_key = api_key
        self.model_config = model_config
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_config['model_id'])
        self.generation_config = model_config.get('generation_config')

    def execute_prompt(self, prompt: str, instructions: Optional[str] = None) -> Dict[str, Any]:
        response_text, input_tokens, output_tokens, cost_usd = None, 0, 0, 0.0
        error_message, success_flag = None, False
        try:
            # Geminiではinstructionsはプロンプトに含めるのが一般的
            full_prompt = f"{instructions}\n\n{prompt}" if instructions else prompt
            response = self.model.generate_content(full_prompt, generation_config=self.generation_config)

            if hasattr(response, 'text') and response.text: response_text = response.text
            elif response.parts: response_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
            else:
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    error_message = f"Blocked: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
                if not response_text and not error_message: error_message = "No text in response."
            
            if hasattr(response, 'usage_metadata'):
                input_tokens, output_tokens = response.usage_metadata.prompt_token_count, response.usage_metadata.candidates_token_count
            else:
                input_tokens = self.model.count_tokens(full_prompt).total_tokens
                output_tokens = self.model.count_tokens(response_text).total_tokens if response_text else 0
                error_message = (error_message or "") + " [Warning: usage_metadata not available]"
            
            cost_usd = (input_tokens * self.model_config.get('input_cost_per_token', 0.0)) + (output_tokens * self.model_config.get('output_cost_per_token', 0.0))
            success_flag = bool(response_text)

        except Exception as e:
            error_message = str(e); success_flag = False
            try: input_tokens = self.model.count_tokens(full_prompt).total_tokens
            except: input_tokens = 0

        return {'response_text': response_text, 'input_tokens': input_tokens, 'output_tokens': output_tokens, 'total_tokens': input_tokens + output_tokens,
                'cost_usd': cost_usd, 'model_name': self.model_config['name'], 'model_id': self.model_config['model_id'],
                'success': success_flag, 'error': error_message, 'api_provider': 'gemini'}

    def evaluate_response(self, original_prompt: str, llm_response_text: str, evaluation_criteria: str) -> Dict[str, Any]:
        eval_prompt = f"""
以下の内容を評価してください：
【元のプロンプト】\n{original_prompt}\n\n【LLMの回答】\n{llm_response_text}\n\n【評価基準】\n{evaluation_criteria}

【評価指示】
上記の評価基準に基づき、LLMの回答を詳細に評価し、以下の形式で構造化されたフィードバックを提供してください。
1.  **総合評価 (10点満点):** [点数] / 10\n    * 理由: [総合評価の主な理由]
2.  **各評価基準項目に基づく詳細評価:**\n    * **[評価基準1]:** [評価とコメント]\n    * ... (他の評価基準項目も同様に)
3.  **特に優れている点:**\n    * [具体的な良い点1]\n    * [具体的な良い点2]
4.  **改善が望まれる点:**\n    * [具体的な改善点1とその提案]
5.  **総括コメント:**\n    * [評価全体のまとめ]
"""
        return self.execute_prompt(eval_prompt)

    def get_model_info(self) -> str: return f"{self.model_config.get('name', 'Unknown Model')} ({self.model_config.get('model_id', 'unknown-id')})"
    def is_free_tier(self) -> bool: return self.model_config.get('free_tier', False)