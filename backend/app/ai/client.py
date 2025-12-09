import os
from transformers import pipeline

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct" 
pipe = None

def get_model():
    global pipe
    if pipe is None:
        try:
            print(f"Loading local model: {MODEL_NAME}...")
            pipe = pipeline("text-generation", model=MODEL_NAME, device="cpu", max_new_tokens=500)
            print("Model loaded successfully.")
        except Exception as e:
            print(f"Failed to load model: {e}")
            raise e
    return pipe

def analyze_code(code_content: str) -> str:
    """Analyzes code using a local lightweight LLM."""
    if not code_content:
        return "No code found to analyze."
    
    try:
        model = get_model()
    except Exception as e:
        return f"Model loading failed: {str(e)}"

    if model is None:
        return "Local model is not initialized."

    # Truncate to avoid extremely long processing times on CPU
    truncated_content = code_content[:2000] 
    
    prompt = f"Analyze the following code for bugs and improvements:\n\n{truncated_content}\n\nAnalysis:"
    
    try:
        # Генерация ответа
        outputs = model(prompt, do_sample=True, temperature=0.7, top_k=50, top_p=0.95)
        generated_text = outputs[0]["generated_text"]
        
        # Возвращаем только новую часть (анализ), убирая промпт
        if generated_text.startswith(prompt):
            return generated_text[len(prompt):].strip()
        return generated_text
    except Exception as e:
        return f"Error interacting with local AI: {str(e)}"
