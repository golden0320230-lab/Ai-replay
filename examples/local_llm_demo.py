"""Local LLM demo using Ollama-compatible endpoint.

This demonstrates using ReplayPack with local/open-source models.
"""

import requests
import replaypack


def call_local_llm(prompt: str, model: str = "qwen2.5:14b-instruct-q4_K_M") -> str:
    """Call a local LLM via Ollama API."""
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 100
            }
        },
        timeout=60
    )
    response.raise_for_status()
    return response.json().get("response", "")


def main():
    """Run a conversation with local LLM."""
    print("=" * 50)
    print("Local LLM Demo (Ollama)")
    print("=" * 50)
    
    # Conversation with multiple turns
    prompts = [
        "What is machine learning in one sentence?",
        "Give me a simple example.",
        "What are the main types?"
    ]
    
    for i, prompt in enumerate(prompts, 1):
        print(f"\n[Turn {i}]")
        print(f"User: {prompt}")
        
        try:
            response = call_local_llm(prompt)
            print(f"Assistant: {response.strip()}")
        except Exception as e:
            print(f"Error: {e}")
            print("Make sure Ollama is running and the model is pulled.")
            break
    
    print("\n" + "=" * 50)
    print("Conversation complete!")
    print("=" * 50)


if __name__ == "__main__":
    print("\nRequirements:")
    print("1. Ollama installed and running")
    print("2. Model pulled: ollama pull qwen2.5:14b-instruct-q4_K_M")
    print("   (or change model name in script)")
    print()
    
    # Record the session
    with replaypack.record(output_dir="./local_llm_runs"):
        main()
    
    print("\nRun recorded to ./local_llm_runs/")
