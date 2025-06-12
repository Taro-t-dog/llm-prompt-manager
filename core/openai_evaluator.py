"""
OpenAI API評価エンジン (修正版)
- openai>=1.3.0 に対応
- client.chat.completions.create を使用
- メッセージ形式のプロンプトをサポート
"""
import tiktoken
from openai import OpenAI as OpenAIClient
from typing import Dict, Any, Optional, Union, List

class OpenAIEvaluator:
    """OpenAI APIを使用したプロンプト評価システム (openai>=1.3.0対応)"""

    def __init__(self, api_key: str, model_config: dict):
        if not api_key: raise ValueError("OpenAI APIキーが設定されていません。")
        self.api_key = api_key
        self.model_config = model_config
        self.client = OpenAIClient(api_key=self.api_key)
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.model_config['model_id'])
        except KeyError:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(self, text: str) -> int:
        if not text: return 0
        return len(self.tokenizer.encode(text))

    def execute_prompt(self, prompt: str, instructions: Optional[str] = None) -> Dict[str, Any]:
        response_text, input_tokens, output_tokens, cost_usd = None, 0, 0, 0.0
        error_message, success_flag = None, False
        try:
            messages = []
            if instructions: messages.append({"role": "system", "content": instructions})
            if isinstance(prompt, str): messages.append({"role": "user", "content": prompt})
            else: raise TypeError("プロンプトは文字列である必要があります。")

            response_obj = self.client.chat.completions.create(model=self.model_config['model_id'], messages=messages)
            
            if response_obj.choices and response_obj.choices[0].message:
                response_text = response_obj.choices[0].message.content
                success_flag = bool(response_text)
            else:
                error_message = "OpenAIモデルから有効な応答がありませんでした。"

            if response_obj.usage:
                input_tokens, output_tokens = response_obj.usage.prompt_tokens, response_obj.usage.completion_tokens
            else: # フォールバック
                full_prompt = (instructions or "") + prompt
                input_tokens, output_tokens = self._count_tokens(full_prompt), self._count_tokens(response_text or "")
                if not error_message: error_message = "[警告: トークン数はローカル計算値]"

            cost_usd = (self.model_config.get('input_cost_per_token', 0.0) * input_tokens) + \
                       (self.model_config.get('output_cost_per_token', 0.0) * output_tokens)

        except Exception as e:
            error_message = str(e); success_flag = False
            full_prompt = (instructions or "") + prompt
            input_tokens = self._count_tokens(full_prompt); output_tokens = 0

        return {'response_text': response_text, 'input_tokens': input_tokens, 'output_tokens': output_tokens, 'total_tokens': input_tokens + output_tokens,
                'cost_usd': cost_usd, 'model_name': self.model_config.get('name', 'Unknown OpenAI'), 'model_id': self.model_config['model_id'],
                'success': success_flag, 'error': error_message, 'api_provider': 'openai'}

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
        eval_instructions = "あなたは専門的な評価者です。ユーザーの基準に基づいて、公正かつ詳細な評価を提供してください。"
        return self.execute_prompt(prompt=eval_prompt, instructions=eval_instructions)

    def get_model_info(self) -> str:
        return f"{self.model_config.get('name', 'Unknown OpenAI')} ({self.model_config.get('api_provider', 'openai').capitalize()})"