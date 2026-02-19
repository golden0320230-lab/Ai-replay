"""Test multi-call session with LLM + tools."""

import replaypack
from replaypack.intercept import create_default_interceptor

# Setup interceptor before imports
interceptor = create_default_interceptor()
if interceptor:
    interceptor.install()

import requests


@replaypack.tool()
def search_knowledge_base(query: str) -> list:
    """Search a knowledge base."""
    return [
        {"id": 1, "title": f"Article about {query}"},
        {"id": 2, "title": f"Guide to {query}"}
    ]


@replaypack.tool()
def calculate_price(items: list) -> dict:
    """Calculate total price."""
    total = sum(item.get('price', 0) for item in items)
    return {"total": total, "count": len(items)}


def simulate_llm_call(prompt: str) -> str:
    """Simulate an LLM call via HTTP."""
    # In real usage, this would call OpenAI/Anthropic/etc
    # For testing, we'll use httpbin to simulate the pattern
    response = requests.post(
        'https://httpbin.org/post',
        json={"prompt": prompt, "model": "test-model"},
        timeout=10
    )
    return f"Response to: {prompt}"


def main():
    """Multi-step AI workflow."""
    print("=" * 60)
    print("Multi-Call Session Demo")
    print("=" * 60)
    
    # Step 1: Initial LLM call
    print("\n[1] Initial LLM call...")
    response1 = simulate_llm_call("What is machine learning?")
    print(f"    Response: {response1[:50]}...")
    
    # Step 2: Tool call - search
    print("\n[2] Tool call: search_knowledge_base")
    results = search_knowledge_base("machine learning")
    print(f"    Found {len(results)} results")
    
    # Step 3: Second LLM call
    print("\n[3] Follow-up LLM call...")
    response2 = simulate_llm_call("Explain neural networks")
    print(f"    Response: {response2[:50]}...")
    
    # Step 4: Tool call - calculate
    print("\n[4] Tool call: calculate_price")
    items = [{"price": 10}, {"price": 25}, {"price": 15}]
    price_info = calculate_price(items)
    print(f"    Total: ${price_info['total']}")
    
    # Step 5: Final LLM call
    print("\n[5] Final LLM call...")
    response3 = simulate_llm_call("Summary of findings")
    print(f"    Response: {response3[:50]}...")
    
    print("\n" + "=" * 60)
    print("Workflow complete!")
    print("=" * 60)


if __name__ == "__main__":
    # Record the session
    replaypack.init(output_dir='./multi_call_runs')
    
    try:
        main()
    finally:
        path = replaypack.stop()
        if interceptor:
            interceptor.uninstall()
    
    print(f"\nSaved to: {path}")
    
    # Inspect
    print("\n" + "=" * 60)
    print("Captured Steps:")
    print("=" * 60)
    
    from replaypack.artifact import Artifact
    a = Artifact.load(path)
    print(f"\nTotal steps: {len(a.recording.steps)}")
    
    for i, step in enumerate(a.recording.steps, 1):
        func = step.function
        if 'http' in func:
            url = step.kwargs.get('url', 'N/A')
            print(f"{i}. HTTP: {url[:60]}...")
        elif 'tool' in func:
            print(f"{i}. Tool: {func}")
        else:
            print(f"{i}. {func}")
