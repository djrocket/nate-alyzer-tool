# verify_deployment.py
import vertexai
from vertexai import agent_engines

PROJECT_ID = "nate-digital-twin"
LOCATION = "us-central1"
# Resource ID captured from deployment output
AGENT_RESOURCE = "projects/134885012683/locations/us-central1/reasoningEngines/4486055819837702144"

def test_agent():
    print(f"--- Connecting to Agent: {AGENT_RESOURCE} ---")
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    
    try:
        agent = agent_engines.get(AGENT_RESOURCE)
        print("Agent retrieved successfully.")
    except Exception as e:
        print(f"FAIL: Could not retrieve agent: {e}")
        return

    print("\n--- Sending Test Query: 'Hello, are you ready?' ---")
    try:
        response = agent.query(prompt="Hello, are you ready?")
        print(f"Response: {response}")
    except Exception as e:
        print(f"FAIL: Query failed: {e}")
        return

    print("\n--- Success! Agent is reachable. ---")

if __name__ == "__main__":
    test_agent()
