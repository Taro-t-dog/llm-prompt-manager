"""
モデル設定と料金情報
"""

MODEL_CONFIGS = {
    # Gemini Models
    "gemini-2.0-flash-exp": {
        "name": "Gemini 2.0 Flash",
        "model_id": "gemini-2.0-flash-exp",
        "input_cost_per_token": 0.0000001,
        "output_cost_per_token": 0.0000004,
        "description": "Fast, cost-efficient model with 1M context window",
        "context_window": 1000000,
        "free_tier": True
    },
    # OpenAI Models
    "gpt-4.1": { # As per user-provided documentation
        "name": "gpt-4.1 (OpenAI)",
        "model_id": "gpt-4.1", # Model ID from the doc
        "api_provider": "openai",
        "input_cost_per_token": 0.000002,  # $2.00 / 1M tokens
        "output_cost_per_token": 0.000008, # $8.00 / 1M tokens
        "description": "OpenAI's GPT-4.1 model.",
        "context_window": 1000000, # From doc: "up to one million tokens for newer GPT-4.1 models"
        "free_tier": False
    },
    
}

def get_model_options():
    """モデル選択用のオプションリストを返す (ID list)"""
    return list(MODEL_CONFIGS.keys())

def get_model_labels():
    """モデル選択用のラベルリストを返す (Display Name list)"""
    # Now includes API provider in the label for clarity
    return [f"{MODEL_CONFIGS[key]['name']} ({MODEL_CONFIGS[key].get('api_provider','unknown').capitalize()})" for key in MODEL_CONFIGS.keys()]

def get_model_config(model_id: str) -> dict:
    """指定されたモデルIDの設定を返す"""
    # Fallback to a default model if model_id is None or not found
    if model_id is None or model_id not in MODEL_CONFIGS:
        # Try to find a default Gemini model first
        default_gemini = next((k for k, v in MODEL_CONFIGS.items() if v.get("api_provider") == "gemini"), None)
        if default_gemini:
            return MODEL_CONFIGS[default_gemini]
        # If no Gemini, take the first available model
        return MODEL_CONFIGS[next(iter(MODEL_CONFIGS))]
    return MODEL_CONFIGS.get(model_id)

def is_free_model(model_id: str) -> bool:
    """モデルが無料かどうかを判定 (configのfree_tierフラグまたはコストベース)"""
    config = get_model_config(model_id)
    if 'free_tier' in config:
        return config['free_tier']
    # Fallback to cost check if free_tier flag is missing
    return config.get('input_cost_per_token', 1.0) == 0 and config.get('output_cost_per_token', 1.0) == 0