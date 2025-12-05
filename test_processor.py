
import requests
import json

PROCESSOR_URL = "https://us-central1-nate-digital-twin.cloudfunctions.net/transcript-processor-and-classifier"

def test_processor():
    # Simulate the text with injected date
    text = "This video was published on 2025-06-23.\n\nHere is the transcript content about AI strategy..."
    
    payload = {"transcript_text": text}
    headers = {"Content-Type": "application/json"}
    
    print(f"Sending text to Processor: {text}")
    try:
        response = requests.post(PROCESSOR_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        print("\n--- Processor Result ---")
        print(json.dumps(result, indent=2))
        
        processed = result.get("processed_transcript", "")
        if "2025-06-23" in processed:
            print("\nSUCCESS: Date preserved in processed transcript.")
        else:
            print("\nFAILURE: Date LOST in processed transcript.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_processor()
