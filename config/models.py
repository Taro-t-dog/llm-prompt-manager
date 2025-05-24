"""
モデル設定と料金情報
"""

MODEL_CONFIGS = {
    "gemini-2.0-flash-exp": {
        "name": "Gemini 2.0 Flash",
        "model_id": "gemini-2.0-flash-exp",
        "input_cost_per_token": 0.0000001,
        "output_cost_per_token": 0.0000004,
        "description": "Fast, cost-efficient model with 1M context window",
        "context_window": 1000000,
        "free_tier": True
    },
    "gemini-1.5-flash": {
        "name": "Gemini 1.5 Flash",
        "model_id": "gemini-1.5-flash",
        "input_cost_per_token": 0.0,
        "output_cost_per_token": 0.0,
        "description": "Free model with generous rate limits",
        "context_window": 1000000,
        "free_tier": True
    },
    "gemini-1.5-pro": {
        "name": "Gemini 1.5 Pro",
        "model_id": "gemini-1.5-pro",
        "input_cost_per_token": 0.00000125,
        "output_cost_per_token": 0.000005,
        "description": "High-performance model for complex tasks",
        "context_window": 2000000,
        "free_tier": True
    }
}

def get_model_options():
    """モデル選択用のオプションリストを返す"""
    return list(MODEL_CONFIGS.keys())

def get_model_labels():
    """モデル選択用のラベルリストを返す"""
    return [MODEL_CONFIGS[key]['name'] for key in MODEL_CONFIGS.keys()]

def get_model_config(model_id: str) -> dict:
    """指定されたモデルIDの設定を返す"""
    return MODEL_CONFIGS.get(model_id, MODEL_CONFIGS["gemini-2.0-flash-exp"])

def is_free_model(model_id: str) -> bool:
    """モデルが無料かどうかを判定"""
    config = get_model_config(model_id)
    return config['input_cost_per_token'] == 0 and config['output_cost_per_token'] == 0