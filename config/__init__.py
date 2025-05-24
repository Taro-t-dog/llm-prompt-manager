"""
設定モジュール
"""

try:
    from .models import MODEL_CONFIGS, get_model_config, get_model_options, get_model_labels, is_free_model
except ImportError as e:
    print(f"Error importing from models: {e}")
    # フォールバック定義
    MODEL_CONFIGS = {
        "gemini-2.0-flash-exp": {
            "name": "Gemini 2.0 Flash",
            "model_id": "gemini-2.0-flash-exp",
            "input_cost_per_token": 0.0000001,
            "output_cost_per_token": 0.0000004,
            "description": "Fast, cost-efficient model",
            "context_window": 1000000,
            "free_tier": True
        }
    }
    
    def get_model_config(model_id: str) -> dict:
        return MODEL_CONFIGS.get(model_id, MODEL_CONFIGS["gemini-2.0-flash-exp"])
    
    def get_model_options():
        return list(MODEL_CONFIGS.keys())
    
    def get_model_labels():
        return [MODEL_CONFIGS[key]['name'] for key in MODEL_CONFIGS.keys()]
    
    def is_free_model(model_id: str) -> bool:
        config = get_model_config(model_id)
        return config['input_cost_per_token'] == 0 and config['output_cost_per_token'] == 0

__all__ = [
    'MODEL_CONFIGS',
    'get_model_config',
    'get_model_options', 
    'get_model_labels',
    'is_free_model'
]