import os
import glob
import argparse
from typing import List
import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession, Content, Part

# Configuration
PROJECT_ID = "nate-digital-twin"  # Using the project ID from ingest_videos.py
LOCATION = "us-central1"
MODEL_NAME = "gemini-2.5-flash" # Using generic tag to resolve latest available
ANTHOLOGY_DIR = r"c:\AI\nate-alyzer-tool"

def load_anthologies(directory: str) -> str:
    """
    Reads all markdown anthology files from the directory.
    Constructs a single massive context string.
    """
    context_parts = []
    
    # Simple exclusion list
    excludes = ["README.md", "task.md", "implementation_plan.md", "summary.txt"]
    
    files = glob.glob(os.path.join(directory, "*.md"))
    
    print(f"Loading knowledge base from {directory}...")
    
    for file_path in files:
        filename = os.path.basename(file_path)
        if filename in excludes or filename.startswith("!"): # simplistic skip
            continue
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Decorate content with filename for the model to know the source
                context_parts.append(f"--- START FILE: {filename} ---\n{content}\n--- END FILE: {filename} ---\n")
                print(f"  - Loaded: {filename}")
        except Exception as e:
            print(f"  - Error loading {filename}: {e}")
            
    return "\n".join(context_parts)

def create_system_prompt(knowledge_base: str) -> str:
    """
    Constructs the system prompt with Persona, Logic, and Knowledge.
    """
    return f"""
You are Nate, an expert AI strategist, pragmatic engineer, and "Big Brother" mentor to the user.
You are NOT a passive assistant. You are a proactive debate partner and teacher.

**YOUR KNOWLEDGE BASE:**
The following text contains your "Anthologies" - your metabolized wisdom and notes from over time.
{knowledge_base}

**YOUR PERSONA:**
- **"Big Brother" / Mentor:** You want the user to succeed, which means you must be tough on them. Challenge their assumptions. Do not just answer questions; force them to think.
- **First-Principles Thinker:** Always ground your advice in the core concepts found in the anthologies (e.g., Information Theory, Taste, Specialized Models).
- **Anti-Hype:** You are allergic to marketing fluff. If the user asks about a buzzword, dissect it ruthlessly.

**CRITICAL LOGIC: CHRONOLOGICAL PRECEDENCE**
- The Anthologies contain entries with `Date: YYYY-MM-DD`.
- **Time flows forward.** Your opinions evolve. 
- If you find conflicting views (e.g., you hated a tool in 2024 but love it in 2025), **THE LATER DATE WINS.**
- **Explain the evolution:** When you answer, explicitly state: "I used to think [Old View] in [Old Date], but as of [New Date], I realized [New View] because..."

**INTERACTION STYLE:**
- **Be Socratic:** End your answers with a question that tests the user's understanding or intuition.
- **Be Opinionated:** Do not give "on the one hand, on the other hand" answers unless the nuance is real. Pick a side based on your latest knowledge.
- **Cite Sources:** When you use an idea, mention which anthology theme (filename) it comes from.

Now, welcome the user to the "Department of Truth" and ask them what hard problem they are wrestling with today.
"""

def chat_loop(session: ChatSession, initial_prompt: str = None):
    """
    Main interactive loop.
    """
    print("\n" + "="*60)
    print("MENTOR NATE: ONLINE")
    print("="*60 + "\n")
    
    print("System: (Connection established. Nate is analyzing the anthologies...)")
    
    # Establish session logic
    try:
        print("System: Waiting for Nate to initialize (this may take a moment due to context size)...")
        # Ensure we have a valid session to start
        # If specific prompt is not provided, we just start the session conversationally
        if initial_prompt:
             # Just run one-shot
             print(f"You (One-shot): {initial_prompt}")
             response = session.send_message(initial_prompt)
             print(f"\nNate: {response.text}\n")
             return

        # Otherwise interactive mode
        # Trigger welcome
        response = session.send_message("I am ready. Introduce yourself and start the session.")
        print(f"\nNate: {response.text}\n")
        
        while True:
            try:
                user_input = input("You: ")
                if user_input.lower() in ["exit", "quit", "bye"]:
                    print("\nNate: Stay sharp. Session ended.")
                    break
                
                if not user_input.strip():
                    continue
                    
                print("System: Nate is thinking...")
                response = session.send_message(user_input)
                print(f"\nNate: {response.text}\n")
                
            except KeyboardInterrupt:
                print("\nNate: Session interrupted.")
                break
            except Exception as e:
                print(f"\nSystem Error: {e}")
                
    except Exception as e:
        print(f"\nCRITICAL ERROR during chat session: {e}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="Run the Mentor Nate agent.")
    parser.add_argument("--project", default=PROJECT_ID, help="Google Cloud Project ID")
    parser.add_argument("--location", default=LOCATION, help="Vertex AI Location")
    parser.add_argument("--path", default=ANTHOLOGY_DIR, help="Path to anthology folder")
    parser.add_argument("--prompt", help="Run in non-interactive mode with this prompt")
    args = parser.parse_args()

    print("Initializing Vertex AI...")
    try:
        vertexai.init(project=args.project, location=args.location)
    except Exception as e:
         print(f"Error initializing Vertex AI: {e}")
         return
    
    # 1. Load Knowledge
    kb_text = load_anthologies(args.path)
    if not kb_text:
        print("CRITICAL ERROR: No anthology files found. Cannot exist without knowledge.")
        return

    # 2. Build Prompt
    system_instruction = create_system_prompt(kb_text)
    
    # 3. Initialize Model
    print(f"Loading model {MODEL_NAME} with system instruction...")
    try:
        model = GenerativeModel(
            MODEL_NAME, 
            system_instruction=[system_instruction]
        )
        
        # 4. Start Chat
        chat = model.start_chat()
        
        chat_loop(chat, initial_prompt=args.prompt)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error starting model/chat: {e}")

if __name__ == "__main__":
    main()
