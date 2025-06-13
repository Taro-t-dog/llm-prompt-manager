"""
モデル設定と料金情報
"""

MODEL_CONFIGS = {
    # Gemini Models
    "gemini-2.0-flash-exp": {
        "name": "Gemini 2.0 Flash",
        "model_id": "gemini-2.0-flash-exp",
        "api_provider": "gemini", # プロバイダーを明記
        "input_cost_per_token": 0.0000001,
        "output_cost_per_token": 0.0000004,
        "description": "Fast, cost-efficient model with 1M context window",
        "context_window": 1000000,
        "free_tier": True
    },
    # OpenAI Models
    "gpt-4.1": {
        "name": "gpt-4.1 (OpenAI)",
        "model_id": "gpt-4.1",
        "api_provider": "openai",
        "input_cost_per_token": 0.000002,  # $2.00 / 1M tokens
        "output_cost_per_token": 0.000008, # $8.00 / 1M tokens
        "description": "OpenAI's GPT-4.1 model.",
        "context_window": 1000000,
        "free_tier": False
    },
    # 👈 [追加] 新しいモデル gpt-4.1-mini
    "gpt-4.1-mini": {
        "name": "gpt-4.1-mini (OpenAI)",
        "model_id": "gpt-4.1-mini",
        "api_provider": "openai",
        "input_cost_per_token": 0.0000004,  # $0.40 / 1M tokens
        "output_cost_per_token": 0.0000016, # $1.60 / 1M tokens
        "description": "OpenAI's cost-efficient GPT-4.1-mini model.",
        "context_window": 1047576, # 一般的なminiモデルのコンテキスト長に修正（必要に応じて変更してください）
        "free_tier": False
    },
}

def get_model_options():
    """モデル選択用のオプションリストを返す (ID list)"""
    return list(MODEL_CONFIGS.keys())

def get_model_labels():
    """モデル選択用のラベルリストを返す (Display Name list)"""
    # ラベルにプロバイダー名を含めて明確化
    return [f"{config['name']}" for config in MODEL_CONFIGS.values()]

def get_model_config(model_id: str) -> dict:
    """指定されたモデルIDの設定を返す"""
    if model_id is None or model_id not in MODEL_CONFIGS:
        default_gemini = next((k for k, v in MODEL_CONFIGS.items() if v.get("api_provider", "gemini") == "gemini"), None)
        if default_gemini:
            return MODEL_CONFIGS[default_gemini]
        return MODEL_CONFIGS[next(iter(MODEL_CONFIGS))]
    return MODEL_CONFIGS.get(model_id)

def is_free_model(model_id: str) -> bool:
    """モデルが無料かどうかを判定 (configのfree_tierフラグまたはコストベース)"""
    config = get_model_config(model_id)
    if not config: return False
    if 'free_tier' in config:
        return config['free_tier']
    return config.get('input_cost_per_token', 1.0) == 0 and config.get('output_cost_per_token', 1.0) == 0