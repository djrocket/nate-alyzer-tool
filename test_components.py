
import sys
import os
import re
import json

# Add current directory to path so we can import ingest_videos
sys.path.append(os.getcwd())

from ingest_videos import fetch_transcript_en, process_video, append_to_anthology

VIDEO_ID = "xZX4KHrqwhM"
ENGINE_ID = "projects/134885012683/locations/us-central1/reasoningEngines/2255577735638286336"
PROJECT = "nate-digital-twin"
LOCATION = "us-central1"
ANTHOLOGY_BUCKET = "nate-digital-twin-anthologies-djr"

def test_step_1_fetch():
    print("\n=== STEP 1: Fetch Transcript & Date ===")
    try:
        text, date = fetch_transcript_en(VIDEO_ID)
        print(f"Date: {date}")
        print(f"Transcript Length: {len(text)}")
        if not text or date == "unknown":
            print("FAIL: Missing text or date")
            return None, None
        print("PASS")
        return text, date
    except Exception as e:
        print(f"FAIL: {e}")
        return None, None

def test_step_2_agent(date):
    print("\n=== STEP 2: Agent Analysis (Raw) ===")
    try:
        # Call process_video which calls agent.query()
        resp = process_video(ENGINE_ID, PROJECT, LOCATION, VIDEO_ID, date)
        
        print(f"Response Type: {type(resp)}")
        if isinstance(resp, dict):
            print(f"Response Keys: {list(resp.keys())}")
            if "messages" in resp:
                print(f"Messages Count: {len(resp['messages'])}")
                if resp['messages']:
                    last = resp['messages'][-1]
                    print(f"Last Message Type: {type(last)}")
                    if hasattr(last, 'content'):
                        print(f"Last Message Content (First 200 chars): {str(last.content)[:200]}")
                        return str(last.content)
            elif "response" in resp:
                print(f"Response Content (First 200 chars): {str(resp['response'])[:200]}")
                return str(resp['response'])
        
        print("FAIL: Could not extract content from response")
        print(f"Full Response: {resp}")
        return None
    except Exception as e:
        print(f"FAIL: {e}")
        return None

def test_step_3_parsing(raw_text):
    print("\n=== STEP 3: Parsing Logic ===")
    try:
        # Unescape newlines first
        clean_text = raw_text.replace('\\n', '\n')
        
        theme_match = re.search(r"THEME:\s*(.+?)(?:\n|CONTENT:|$)", clean_text, re.IGNORECASE | re.DOTALL)
        content_match = re.search(r"CONTENT:\s*(.+)", clean_text, re.IGNORECASE | re.DOTALL)
        
        if theme_match and content_match:
            theme = theme_match.group(1).strip()
            # Clean theme
            theme = theme.replace('\\n', '').strip()
            
            analysis = content_match.group(1).strip()
            
            print(f"Theme: '{theme}'")
            print(f"Analysis Length: {len(analysis)}")
            
            slug = theme.lower().replace(" & ", "-").replace(" ", "-").replace("---", "-")
            slug = re.sub(r'[^a-z0-9-]', '', slug)
            
            print(f"Slug: '{slug}'")
            if slug.endswith('n') and len(slug) > 1:
                print("WARN: Slug ends with 'n'")
            
            filename = f"{slug}.md"
            print(f"Filename: {filename}")
            
            print("PASS")
            return filename, analysis
        else:
            print("FAIL: Regex match failed")
            print(f"Raw Text Preview: {clean_text[:500]}")
            return None, None
    except Exception as e:
        print(f"FAIL: {e}")
        return None, None

def test_step_4_gcs_write(filename, analysis, date):
    print("\n=== STEP 4: GCS Write (Local) ===")
    try:
        # Use a test filename to avoid messing up real anthologies
        test_filename = f"TEST_COMPONENT_{filename}"
        print(f"Writing to {test_filename}...")
        
        success = append_to_anthology(ANTHOLOGY_BUCKET, test_filename, VIDEO_ID, date, analysis)
        if success:
            print("PASS: Write successful")
        else:
            print("FAIL: Write returned False")
    except Exception as e:
        print(f"FAIL: {e}")

def main():
    text, date = test_step_1_fetch()
    if not text: return
    
    raw_content = test_step_2_agent(date)
    if not raw_content: return
    
    filename, analysis = test_step_3_parsing(raw_content)
    if not filename: return
    
    test_step_4_gcs_write(filename, analysis, date)

if __name__ == "__main__":
    main()
