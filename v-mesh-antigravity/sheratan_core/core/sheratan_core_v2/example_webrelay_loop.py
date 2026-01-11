# Example usage of WebRelayLLMClient with loop_runner
"""
Demonstrates how to run an autonomous loop with WebRelay HTTP integration.
"""

import sys
sys.path.insert(0, 'c:/sheratan-core-poc/core/sheratan_core_v2')

from webrelay_llm_client import WebRelayLLMClient

# Example mission config for loop runner
mission_config = {
    "loop_config": {
        "max_iterations": 5,  # Limit to 5 LLM calls
        "max_consecutive_errors": 2,
        "profile": "execute"
    },
    "model_config": {
        "provider": "webrelay",
        "model": "chatgpt",
        "temperature": 0.7
    },
    "mission": {
        "mission_id": "test-autonomous-001",
        "goal": "Create 2 followup jobs and demonstrate autonomous loop",
        "mode": "execute"
    },
    "initial_context_packet": {
        "mission": {
            "id": "test-autonomous-001",
            "goal": "Create 2 followup jobs",
            "mode": "execute"
        },
        "progress": [],
        "state": {},
        "memory": {},
        "loop_focus": "Start autonomous loop and create followup jobs"
    }
}

# Test: Create client and check health
client = WebRelayLLMClient()
if client.health_check():
    print("✅ WebRelay is available")
    
    # Simple test call
    test_prompt = "Create 2 simple followup jobs in LCP format. Be brief."
    try:
        response = client.call(test_prompt)
        print(f"✅ LLM Response:\n{response}")
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("❌ WebRelay not available")

print("\nTo use with loop_runner:")
print("1. Update loop_runner.py to accept custom LLMClient")
print("2. Pass WebRelayLLMClient instance")
print("3. Run with mission config above")
