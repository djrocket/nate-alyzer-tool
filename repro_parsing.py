
import re

# Simulated response structure based on user output
# The user sees: ... deployment.', 'thought_signature': ...'}]
# This implies str(obj) produced that.
# If obj was [{'text': '...', 'thought_signature': '...'}]
# str(obj) -> "[{'text': '...', 'thought_signature': '...'}]"

fake_response_content = [
    {
        "text": "THEME: AI Strategy\nCONTENT: Some analysis here.",
        "thought_signature": "xyz"
    }
]

resp = {"response": fake_response_content}

def parse_response(resp):
    resp_text = ""
    if isinstance(resp, dict):
        if "response" in resp:
            # CURRENT BUGGY LOGIC:
            resp_text = str(resp["response"])
        elif "text" in resp:
            resp_text = resp["text"]
    
    print(f"Parsed Text: {resp_text}")
    return resp_text

print("--- Current Logic ---")
parse_response(resp)

def parse_response_fixed(resp):
    resp_text = ""
    if isinstance(resp, dict):
        if "response" in resp:
            val = resp["response"]
            # Handle list
            if isinstance(val, list) and len(val) > 0:
                # Assuming first item has text
                if isinstance(val[0], dict) and "text" in val[0]:
                    resp_text = val[0]["text"]
                else:
                    resp_text = str(val[0])
            # Handle dict
            elif isinstance(val, dict) and "text" in val:
                resp_text = val["text"]
            else:
                resp_text = str(val)
        elif "text" in resp:
            resp_text = resp["text"]
            
    print(f"Fixed Text: {resp_text}")
    return resp_text

print("\n--- Fixed Logic ---")
parse_response_fixed(resp)
