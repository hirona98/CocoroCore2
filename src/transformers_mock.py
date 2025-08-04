"""
Minimal transformers mock for MemOS when using external APIs only
パッケージ容量削減のためのtransformersモック
"""

class DynamicCache:
    """Mock DynamicCache for compatibility"""
    def __init__(self):
        pass

class AutoModelForCausalLM:
    """Mock AutoModelForCausalLM for compatibility"""
    @classmethod
    def from_pretrained(cls, model_name_or_path, *args, **kwargs):
        return DummyModel()

class LogitsProcessorList:
    """Mock LogitsProcessorList"""
    def __init__(self, *processors):
        self.processors = processors

class TemperatureLogitsWarper:
    """Mock TemperatureLogitsWarper"""
    def __init__(self, temperature):
        self.temperature = temperature

class TopKLogitsWarper:
    """Mock TopKLogitsWarper"""
    def __init__(self, top_k):
        self.top_k = top_k

class TopPLogitsWarper:
    """Mock TopPLogitsWarper"""
    def __init__(self, top_p):
        self.top_p = top_p

class DummyModel:
    """Dummy model that satisfies MemOS requirements"""
    def __init__(self):
        pass
    
    def generate(self, *args, **kwargs):
        """Mock generate method"""
        return None

class AutoTokenizer:
    """Mock AutoTokenizer for MemOS compatibility"""
    
    @classmethod
    def from_pretrained(cls, model_name_or_path, *args, **kwargs):
        """Return a dummy tokenizer that MemOS can use"""
        return DummyTokenizer()

class DummyTokenizer:
    """Dummy tokenizer that satisfies MemOS requirements"""
    
    def __init__(self):
        self.pad_token_id = 0
        self.eos_token_id = 2
        self.model_max_length = 512
    
    def __call__(self, text, *args, **kwargs):
        """Minimal tokenization (just return dummy tokens)"""
        if isinstance(text, list):
            return {"input_ids": [[1, 2, 3] for _ in text]}
        return {"input_ids": [1, 2, 3]}
    
    def encode(self, text, *args, **kwargs):
        """Simple encode"""
        return [1, 2, 3]
    
    def decode(self, token_ids, *args, **kwargs):
        """Simple decode"""
        return "decoded_text"