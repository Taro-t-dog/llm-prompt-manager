"""
Gemini AI評価エンジン (改訂版)
"""

import google.generativeai as genai
from typing import Dict, Any, Optional

class GeminiEvaluator:
    """Gemini APIを使用したプロンプト評価システム"""

    def __init__(self, api_key: str, model_config: dict):
        """
        初期化

        Args:
            api_key: Gemini API キー
            model_config: モデル設定辞書
                          (例: {'model_id': 'gemini-1.5-flash-latest',
                                 'name': 'Gemini 1.5 Flash',
                                 'input_cost_per_token': 0.0000005, # 例: 100万トークンあたり0.5 USD
                                 'output_cost_per_token': 0.0000015, # 例: 100万トークンあたり1.5 USD
                                 'free_tier': False,
                                 'generation_config': Optional[genai.types.GenerationConfigDict] = None})
        """
        self.api_key = api_key
        self.model_config = model_config
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_config['model_id'])
        self.generation_config = model_config.get('generation_config')

    def execute_prompt(self, prompt: str, generation_config_override: Optional[genai.types.GenerationConfigDict] = None) -> Dict[str, Any]:
        """
        プロンプトを実行し、結果とコスト情報を返す。
        トークン数はAPIのusage_metadataから取得する。

        Args:
            prompt: 実行するプロンプト
            generation_config_override: この実行に一時的に適用する生成設定

        Returns:
            実行結果辞書（response_text, input_tokens, output_tokens, total_tokens, cost_usd, success, error等）
        """
        response_text = None
        input_tokens = 0
        output_tokens = 0
        total_tokens_api = 0 # APIが報告する合計トークン数
        cost_usd = 0.0
        error_message = None
        success_flag = False

        try:
            current_generation_config = generation_config_override if generation_config_override else self.generation_config
            response = self.model.generate_content(
                prompt,
                generation_config=current_generation_config
            )

            # レスポンスからテキストを取得 (モデルやSDKのバージョンにより調整が必要な場合あり)
            # 通常、response.text または response.parts[0].text で取得可能
            if hasattr(response, 'text') and response.text:
                response_text = response.text
            elif response.parts:
                response_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
            else:
                # テキストが取得できない場合、プロンプトのフィードバックを確認
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    error_message = f"Blocked: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
                else:
                    error_message = "No text content in response and no explicit blocking reason."


            # APIのusage_metadataからトークン数を取得
            if hasattr(response, 'usage_metadata'):
                input_tokens = response.usage_metadata.prompt_token_count
                # candidates_token_countは、生成された候補全体のトークン数を示すことが多い
                output_tokens = response.usage_metadata.candidates_token_count
                total_tokens_api = response.usage_metadata.total_token_count
            else:
                # usage_metadataがない場合のフォールバック (より不正確になる可能性)
                # この場合、入力トークンのみAPIでカウントし、出力は0とするか、
                # またはエラーとして扱う方が適切かもしれません。
                # ここでは、フォールバックとして入力のみカウントする例を示します。
                # 実際のプロダクションコードでは、このケースをどう扱うか慎重に検討してください。
                count_tokens_response_input = self.model.count_tokens(prompt)
                input_tokens = count_tokens_response_input.total_tokens
                output_tokens = 0 # 出力トークンは不明
                total_tokens_api = input_tokens # 不完全な合計
                error_message = (error_message or "") + " Warning: usage_metadata not available. Token counts may be incomplete."


            # コスト計算 (model_configにコスト情報がない場合は0)
            input_cost_per_token = self.model_config.get('input_cost_per_token', 0.0)
            output_cost_per_token = self.model_config.get('output_cost_per_token', 0.0)

            cost_usd = (input_tokens * input_cost_per_token) + \
                       (output_tokens * output_cost_per_token)

            success_flag = True if response_text or not error_message else False # テキストがあるか、エラーがなければ成功とみなす

        except Exception as e:
            error_message = str(e)
            success_flag = False
            # エラー時にも入力プロンプトのトークン数を計算しておく（オプション）
            try:
                count_tokens_response_error_input = self.model.count_tokens(prompt)
                input_tokens = count_tokens_response_error_input.total_tokens
            except Exception:
                input_tokens = 0 # これも失敗した場合

        return {
            'response_text': response_text,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens_api if total_tokens_api else (input_tokens + output_tokens), # APIの合計がない場合は計算値
            'cost_usd': cost_usd,
            'model_name': self.model_config['name'],
            'model_id': self.model_config['model_id'],
            'success': success_flag,
            'error': error_message
        }

    def evaluate_response(self, original_prompt: str, llm_response_text: str, evaluation_criteria: str) -> Dict[str, Any]:
        """
        LLMの回答を評価基準に基づいて評価する。
        この評価自体もLLMへのAPIコールとなる。

        Args:
            original_prompt: 元のプロンプト
            llm_response_text: 評価対象のLLMの回答テキスト
            evaluation_criteria: 評価基準

        Returns:
            評価結果を示す実行結果辞書 (execute_promptの戻り値と同じ形式)
        """
        evaluation_prompt = f"""
以下の内容を評価してください：

【元のプロンプト】
{original_prompt}

【LLMの回答】
{llm_response_text}

【評価基準】
{evaluation_criteria}

【評価指示】
上記の評価基準に基づいて、LLMの回答を詳細に評価し、以下の形式で構造化されたフィードバックを提供してください。
各項目について具体的な理由や例を挙げて説明してください。

1.  **総合評価 (10点満点):** [点数] / 10
    * 理由: [総合評価の主な理由]

2.  **各評価基準項目に基づく詳細評価:**
    * **[評価基準1]:** [評価とコメント]
    * **[評価基準2]:** [評価とコメント]
    * ... (他の評価基準項目も同様に)

3.  **特に優れている点:**
    * [具体的な良い点1]
    * [具体的な良い点2]

4.  **改善が望まれる点:**
    * [具体的な改善点1とその提案]
    * [具体的な改善点2とその提案]

5.  **総括コメント:**
    * [評価全体のまとめや、さらなる改善のためのアドバイスなど]
"""
        # 評価用プロンプトの実行には、デフォルトの生成設定を使用
        return self.execute_prompt(evaluation_prompt)

    def get_model_info(self) -> str:
        """モデル情報を文字列で返す"""
        return f"{self.model_config.get('name', 'Unknown Model')} ({self.model_config.get('model_id', 'unknown-id')})"

    def is_free_tier(self) -> bool:
        """無料ティアかどうかを判定"""
        return self.model_config.get('free_tier', False)

    def count_input_tokens(self, text_or_contents: Any) -> int:
        """
        指定されたテキストまたはコンテンツの入力トークン数をAPIを使用してカウントする。
        これはAPIコール前に概算を得るために使用できる。

        Args:
            text_or_contents: トークン数をカウントするテキスト文字列、または genai.types.ContentsType

        Returns:
            推定入力トークン数
        """
        try:
            count_response = self.model.count_tokens(text_or_contents)
            return count_response.total_tokens
        except Exception:
            # APIでのカウントに失敗した場合、非常に大まかな推定または0を返す
            if isinstance(text_or_contents, str):
                return len(text_or_contents.split()) # 非常に粗い近似
            return 0