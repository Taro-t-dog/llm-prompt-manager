"""
OpenAI API評価エンジン
"""
import tiktoken
from openai import OpenAI as OpenAIClient # Alias to avoid conflict with any 'OpenAI' class in user's context
from typing import Dict, Any, Optional, Union, List

class OpenAIEvaluator:
    """OpenAI APIを使用したプロンプト評価システム"""

    def __init__(self, api_key: str, model_config: dict):
        """
        初期化

        Args:
            api_key: OpenAI API キー
            model_config: モデル設定辞書 (includes model_id, costs, etc.)
        """
        self.api_key = api_key
        self.model_config = model_config
        self.client = OpenAIClient(api_key=self.api_key)
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.model_config['model_id'])
        except KeyError: # If model_id not in tiktoken, use a common one
            try:
                self.tokenizer = tiktoken.encoding_for_model("gpt-4") # Fallback for gpt-4 series
            except Exception:
                 self.tokenizer = tiktoken.get_encoding("cl100k_base") # Generic fallback

    def _count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(self.tokenizer.encode(text))

    def execute_prompt(self, prompt: Union[str, List[Dict[str, str]]], instructions: Optional[str] = None) -> Dict[str, Any]:
        """
        プロンプトを実行し、結果とコスト情報を返す。
        Uses client.responses.create based on user-provided documentation.

        Args:
            prompt: 実行するプロンプト (string or list of messages for OpenAI)
            instructions: Optional instructions string for OpenAI's `instructions` parameter.

        Returns:
            実行結果辞書
        """
        response_text = None
        input_tokens = 0
        output_tokens = 0
        cost_usd = 0.0
        error_message = None
        success_flag = False

        try:
            # Count input tokens
            if isinstance(prompt, str):
                input_tokens = self._count_tokens(prompt)
                if instructions:
                    input_tokens += self._count_tokens(instructions) # Add instruction tokens
            elif isinstance(prompt, list): # List of messages
                full_prompt_content = ""
                for message in prompt:
                    full_prompt_content += message.get("content", "") + "\n"
                input_tokens = self._count_tokens(full_prompt_content.strip())
                if instructions:
                    input_tokens += self._count_tokens(instructions)


            # API Call (using client.responses.create as per doc)
            api_params = {
                "model": self.model_config['model_id'],
                "input": prompt
            }
            if instructions:
                api_params["instructions"] = instructions

            response_obj = self.client.responses.create(**api_params)

            # Extract response text
            # The doc mentions `response.output_text` for convenience in some SDKs.
            # It also shows the structure of `output` array.
            # Let's prioritize `output_text` if available, then try to parse `output`.
            if hasattr(response_obj, 'output_text') and response_obj.output_text:
                response_text = response_obj.output_text
            elif hasattr(response_obj, 'output') and isinstance(response_obj.output, list) and response_obj.output:
                # Try to find the first text output as per the documented structure
                aggregated_text = []
                for item in response_obj.output:
                    if item.get("type") == "message" and item.get("role") == "assistant":
                        if isinstance(item.get("content"), list):
                            for content_part in item["content"]:
                                if content_part.get("type") == "output_text" and "text" in content_part:
                                    aggregated_text.append(content_part["text"])
                if aggregated_text:
                    response_text = "".join(aggregated_text)

            if response_text:
                output_tokens = self._count_tokens(response_text)
                success_flag = True
            else: # No text output
                # Check for potential errors if not already set by an exception
                # The `client.responses.create` API might not have explicit error fields like Gemini's `prompt_feedback`.
                # We rely on exceptions or lack of output_text.
                if not error_message: # if no exception caught this far
                     error_message = "No text content in response from OpenAI model."
                success_flag = False


            input_cost_per_token = self.model_config.get('input_cost_per_token', 0.0)
            output_cost_per_token = self.model_config.get('output_cost_per_token', 0.0)
            cost_usd = (input_tokens * input_cost_per_token) + \
                       (output_tokens * output_cost_per_token)

        except Exception as e:
            error_message = str(e)
            success_flag = False
            # If prompt was a string, try to count its tokens even on error
            if isinstance(prompt, str) and input_tokens == 0:
                input_tokens = self._count_tokens(prompt)


        return {
            'response_text': response_text,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
            'cost_usd': cost_usd,
            'model_name': self.model_config.get('name', 'Unknown OpenAI Model'),
            'model_id': self.model_config['model_id'],
            'success': success_flag,
            'error': error_message,
            'api_provider': 'openai'
        }

    def evaluate_response(self, original_prompt: str, llm_response_text: str, evaluation_criteria: str) -> Dict[str, Any]:
        """
        LLMの回答を評価基準に基づいて評価する (OpenAI model for evaluation).
        """
        # For OpenAI, we might prefer a message-based prompt for clarity,
        # or a well-structured single string prompt.
        # Using the single string prompt style for consistency with GeminiEvaluator's approach.
        evaluation_prompt_str = f"""
Please evaluate the following content:

[Original Prompt]
{original_prompt}

[LLM's Response]
{llm_response_text}

[Evaluation Criteria]
{evaluation_criteria}

[Instructions for Evaluation]
Based on the criteria above, provide a detailed evaluation of the LLM's response. Structure your feedback as follows, explaining your reasoning for each point:

1.  **Overall Score (out of 10):** [Score] / 10
    *   Reason: [Main reason for the overall score]

2.  **Detailed Evaluation per Criterion:**
    *   [Criterion 1 from above]: [Your assessment and comments]
    *   [Criterion 2 from above]: [Your assessment and comments]
    *   ... (and so on for all criteria)

3.  **Strengths:**
    *   [Specific point 1 where the response excelled]
    *   [Specific point 2 where the response excelled]

4.  **Areas for Improvement:**
    *   [Specific area 1 for improvement and suggestions]
    *   [Specific area 2 for improvement and suggestions]

5.  **Concluding Remarks:**
    *   [Overall summary of the evaluation, advice for further improvement, etc.]
"""
        # Here, we pass the single string `evaluation_prompt_str` as the `input`
        # and potentially an `instructions` string if we want to guide the evaluation model's persona.
        # For simplicity, let's assume the evaluation_prompt_str is self-contained for now.
        # If the model used for evaluation is a reasoning model, a simpler instruction might be better.
        # If it's a GPT model, detailed instructions as above are good.
        
        # The `instructions` parameter for client.responses.create could be something like:
        # "You are an expert evaluator. Provide a fair and detailed assessment."
        # For now, not using the separate 'instructions' parameter for evaluation call.
        return self.execute_prompt(prompt=evaluation_prompt_str)

    def get_model_info(self) -> str:
        """モデル情報を文字列で返す"""
        return f"{self.model_config.get('name', 'Unknown OpenAI Model')} ({self.model_config.get('model_id', 'unknown-id')})"

    def is_free_tier(self) -> bool:
        """無料ティアかどうかを判定"""
        # OpenAI models in this setup are generally not free tier in the same way Gemini's might be.
        # Rely on cost being zero or a specific 'free_tier' flag in config.
        if 'free_tier' in self.model_config:
            return self.model_config['free_tier']
        return self.model_config.get('input_cost_per_token', 1.0) == 0 and \
               self.model_config.get('output_cost_per_token', 1.0) == 0