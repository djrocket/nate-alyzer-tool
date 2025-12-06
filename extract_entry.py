
import re

FILE = "temp_anthology.md"
VIDEO_ID = "xZX4KHrqwhM"

def extract_entry():
    with open(FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        
    start_marker = f"<!-- VIDEO_ID: {VIDEO_ID} -->"
    start_idx = content.find(start_marker)
    
    if start_idx == -1:
        print(f"Video ID {VIDEO_ID} not found.")
        return
        
    # Find next ID or end of file
    next_marker_regex = r"<!-- VIDEO_ID: .*? -->"
    # Search for next marker AFTER the start
    match = re.search(next_marker_regex, content[start_idx + len(start_marker):])
    
    if match:
        end_idx = start_idx + len(start_marker) + match.start()
        entry = content[start_idx:end_idx]
    else:
        entry = content[start_idx:]
        
    print(f"Extracted {len(entry)} characters.")
    print("-" * 20)
    print(entry)
    print("-" * 20)
    
    if "Transcript:" in entry:
        print("Transcript Header FOUND.")
        transcript_part = entry.split("Transcript:")[1]
        print(f"Transcript length: {len(transcript_part.strip())}")
    else:
        print("Transcript Header NOT FOUND.")

if __name__ == "__main__":
    extract_entry()
