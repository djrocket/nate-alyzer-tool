
import sys
import os
from google.cloud import storage
import vertexai
from vertexai.preview import reasoning_engines

# Configuration
VIDEO_ID = "xZX4KHrqwhM"
TRANSCRIPT_BUCKET = "nate-digital-twin-transcript-cache"
ENGINE_ID = "projects/134885012683/locations/us-central1/reasoningEngines/2255577735638286336"

def debug_transcript():
    print(f"\n=== 1. Checking GCS Transcript: {VIDEO_ID} ===")
    storage_client = storage.Client()
    bucket = storage_client.bucket(TRANSCRIPT_BUCKET)
    blob = bucket.blob(f"{VIDEO_ID}.txt")
    
    if not blob.exists():
        print("FAIL: Blob does not exist!")
        return None

    content = blob.download_as_text()
    print(f"Content Length: {len(content)}")
    print(f"Content Type: {type(content)}")
    print("--- First 500 chars ---")
    print(content[:500])
    print("-----------------------")
    
    # Check if it looks like JSON
    if content.strip().startswith("{") or content.strip().startswith("["):
        print("WARNING: Content looks like JSON! It should be raw text.")
    
    return content

def debug_agent_echo(transcript):
    print(f"\n=== 2. Testing Agent Perception ===")
    vertexai.init(project="nate-digital-twin", location="us-central1")
    agent = reasoning_engines.ReasoningEngine(ENGINE_ID)
    
    # Ask the agent to simply echo the first sentence of the transcript it receives
    # This verifies what the agent 'sees' in the context
    prompt = f"""
    I am testing your context window. 
    Here is a transcript:
    {transcript[:2000]} ... [truncated for test]
    
    TASK: Please output ONLY the first 10 words of the transcript provided above. Do not analyze it. Just echo it.
    """
    
    print("Sending prompt to agent...")
    try:
        response = agent.query(input=prompt)
        print(f"Agent Response Raw: {response}")
        
        # Try to parse it using the logic we just fixed
        resp_text = ""
        if isinstance(response, dict):
            if "response" in response:
                val = response["response"]
                if isinstance(val, list) and len(val) > 0:
                    if isinstance(val[0], dict) and "text" in val[0]:
                        resp_text = val[0]["text"]
                    else:
                        resp_text = str(val[0])
                elif isinstance(val, dict) and "text" in val:
                    resp_text = val["text"]
                else:
                    resp_text = str(val)
            elif "text" in response:
                resp_text = response["text"]
            elif "messages" in response:
                 messages = response["messages"]
                 if messages:
                     last_msg = messages[-1]
                     if hasattr(last_msg, "content"):
                         resp_text = str(last_msg.content)
        else:
             resp_text = str(response)
             
        print(f"Parsed Agent Output: '{resp_text}'")
        
    except Exception as e:
        print(f"FAIL: Agent query failed: {e}")

if __name__ == "__main__":
    transcript = debug_transcript()
    if transcript:
        debug_agent_echo(transcript)
