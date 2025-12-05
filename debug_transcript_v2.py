
import sys
import os
from google.cloud import storage
import vertexai
from vertexai.preview import reasoning_engines
import traceback

# Configuration
VIDEO_ID = "xZX4KHrqwhM"
TRANSCRIPT_BUCKET = "nate-digital-twin-transcript-cache"
ENGINE_ID = "projects/134885012683/locations/us-central1/reasoningEngines/2255577735638286336"
PROJECT = "nate-digital-twin"
LOCATION = "us-central1"

def debug_transcript_content():
    print(f"\n=== 1. Analyzing Transcript Content ===")
    storage_client = storage.Client()
    bucket = storage_client.bucket(TRANSCRIPT_BUCKET)
    blob = bucket.blob(f"{VIDEO_ID}.txt")
    
    content = blob.download_as_text()
    print(f"Length: {len(content)}")
    
    # Check for the weird string seen in debug output
    snippet = "saying there's a new p"
    if snippet in content:
        print(f"Found snippet '{snippet}' in transcript.")
        idx = content.find(snippet)
        print(f"Context: {content[idx-50:idx+50]}")
    else:
        print(f"Snippet '{snippet}' NOT found in transcript.")
        
    return content

def test_agent_connectivity():
    print(f"\n=== 2. Testing Agent Connectivity (Hello World) ===")
    vertexai.init(project=PROJECT, location=LOCATION)
    agent = reasoning_engines.ReasoningEngine(ENGINE_ID)
    
    try:
        response = agent.query(input="Hello, are you working?")
        print(f"Agent Response: {response}")
    except Exception as e:
        print(f"FAIL: Connectivity test failed: {e}")
        traceback.print_exc()

def test_agent_with_transcript(transcript):
    print(f"\n=== 3. Testing Agent with Transcript Chunk ===")
    vertexai.init(project=PROJECT, location=LOCATION)
    agent = reasoning_engines.ReasoningEngine(ENGINE_ID)
    
    # Use a safe chunk
    chunk = transcript[:500]
    prompt = f"Echo this text back to me: {chunk}"
    
    try:
        response = agent.query(input=prompt)
        print(f"Agent Response: {response}")
    except Exception as e:
        print(f"FAIL: Transcript test failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    transcript = debug_transcript_content()
    test_agent_connectivity()
    if transcript:
        test_agent_with_transcript(transcript)
