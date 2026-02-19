"""Multi-step session demo for ReplayPack.

This demonstrates a realistic AI workflow with:
- Multiple LLM calls
- Tool/function calls
- HTTP requests
- All captured in one session
"""

import replaypack
import requests


@replaypack.tool()
def search_database(query: str) -> dict:
    """Simulate a database search tool."""
    return {
        "results": [
            {"id": 1, "title": f"Result for {query}"},
            {"id": 2, "title": f"Another result for {query}"}
        ],
        "count": 2
    }


@replaypack.tool()
def format_output(data: dict) -> str:
    """Format data for display."""
    lines = [f"- {r['title']}" for r in data.get("results", [])]
    return "\n".join(lines)


def main():
    """Run a multi-step AI workflow."""
    print("=" * 50)
    print("Multi-Step Session Demo")
    print("=" * 50)
    
    # Step 1: Initial LLM call (simulated)
    print("\n[Step 1] Initial query processing...")
    query = "machine learning"
    
    # Step 2: Tool call - search
    print("[Step 2] Searching database...")
    search_results = search_database(query)
    
    # Step 3: Another tool call - format
    print("[Step 3] Formatting output...")
    formatted = format_output(search_results)
    
    # Step 4: HTTP API call (example)
    print("[Step 4] Fetching additional data...")
    try:
        # Make an actual HTTP request to httpbin.org
        response = requests.get('https://httpbin.org/get', timeout=10)
        print(f"  HTTP status: {response.status_code}")
        data = response.json()
        print(f"  Origin: {data.get('origin', 'unknown')}")
    except Exception as e:
        print(f"  HTTP error: {e}")
        # Fallback to simulated response if network fails
        response = {"status": "ok", "data": "example"}
        print(f"  Using fallback: {response['status']}")
    except Exception as e:
        print(f"  HTTP error: {e}")
    
    # Step 5: Final processing
    print("[Step 5] Final output:")
    print(formatted)
    
    print("\n" + "=" * 50)
    print("Session complete!")
    print("=" * 50)


if __name__ == "__main__":
    import os
    # Use CLI-specified output dir if available, otherwise default
    output_dir = os.environ.get('REPLAYPACK_OUTPUT_DIR', './demo_runs')
    
    # Record the entire session
    with replaypack.record(output_dir=output_dir):
        main()
    
    print(f"\nRun recorded to {output_dir}/")
    print(f"Replay with: replaypack replay {output_dir}/*.rpk")
