"""
Gemini AI評価エンジン
"""

import google.generativeai as genai
import re
from typing import Dict, Any


class GeminiEvaluator:
    """Gemini APIを使用したプロンプト評価システム"""
    
    def __init__(self, api_key: str, model_config: dict):
        """
        初期化
        
        Args:
            api_key: Gemini API キー
            model_config: モデル設定辞書
        """
        self.api_key = api_key
        self.model_config = model_config
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_config['model_id'])
    
    def count_tokens(self, text: str) -> int:
        """
        テキストのトークン数を概算
        
        Args:
            text: トークン数を計算するテキスト
            
        Returns:
            推定トークン数
        """
        return len(text.split()) + len(re.findall(r'[^\w\s]', text))
    
    def execute_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        プロンプトを実行し、結果とコスト情報を返す
        
        Args:
            prompt: 実行するプロンプト
            
        Returns:
            実行結果辞書（response, tokens, cost, success, error等）
        """
        try:
            response = self.model.generate_content(prompt)
            
            input_tokens = self.count_tokens(prompt)
            output_tokens = self.count_tokens(response.text)
            
            # 動的料金計算
            input_cost = input_tokens * self.model_config['input_cost_per_token']
            output_cost = output_tokens * self.model_config['output_cost_per_token']
            total_cost = input_cost + output_cost
            
            return {
                'response': response.text,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens,
                'cost_usd': total_cost,
                'model_name': self.model_config['name'],
                'model_id': self.model_config['model_id'],
                'success': True,
                'error': None
            }
        except Exception as e:
            return {
                'response': None,
                'input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0,
                'cost_usd': 0,
                'model_name': self.model_config['name'],
                'model_id': self.model_config['model_id'],
                'success': False,
                'error': str(e)
            }
    
    def evaluate_response(self, original_prompt: str, response: str, evaluation_criteria: str) -> Dict[str, Any]:
        """
        レスポンスを評価基準に基づいて評価
        
        Args:
            original_prompt: 元のプロンプト
            response: LLMの回答
            evaluation_criteria: 評価基準
            
        Returns:
            評価結果辞書
        """
        evaluation_prompt = f"""
以下の内容を評価してください：

【元のプロンプト】
{original_prompt}

【LLMの回答】
{response}

【評価基準】
{evaluation_criteria}

【評価指示】
上記の評価基準に基づいて、LLMの回答を詳細に評価してください。
以下の形式で回答してください：

1. 総合評価: [1-10点の数値評価]
2. 各項目の評価: [評価基準の各項目について詳細評価]
3. 良い点: [具体的な良い点]
4. 改善点: [具体的な改善すべき点]
5. 総合コメント: [全体的な評価コメント]
"""
        
        return self.execute_prompt(evaluation_prompt)
    
    def get_model_info(self) -> str:
        """モデル情報を文字列で返す"""
        return f"{self.model_config['name']} ({self.model_config['model_id']})"
    
    def is_free_tier(self) -> bool:
        """無料ティアかどうかを判定"""
        return self.model_config.get('free_tier', False)