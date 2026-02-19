"""Demo script for ReplayPack.

This demonstrates basic recording functionality.
"""

import replaypack

# Simulate a simple workflow
def process_query(query: str) -> str:
    return f"Processed: {query}"

# Record the run
with replaypack.record():
    result = process_query("Hello, world!")
    print(result)
