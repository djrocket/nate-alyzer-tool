# main.py
import os
from flask import jsonify

# Import the Vertex AI SDK
import vertexai
from vertexai.generative_models import GenerativeModel
import re
from datetime import datetime

# Initialize Vertex AI. This is best done globally.
# The PROJECT_ID and REGION are automatically discovered by the library.
vertexai.init()
model = GenerativeModel("gemini-2.5-flash") # Using 2.5 Flash for its large context window

# Deterministic generation config to reduce run-to-run variance
GEN_CONFIG = {"temperature": 0}

def _call_llm_for_processing(raw_text: str) -> str:
    """
    Makes the first LLM call to distill the transcript through a specific analytical lens.
    """
    print("Executing LLM call 1: Distillation and Structuring...")

    # This is the new, more sophisticated prompt.
    prompt = f"""
    **Role and Goal:**
    You are an expert AI strategist and a critical analyst, acting as my research partner. Your primary function is to distill the core, non-obvious insights from the provided transcript. You are not a generic summarizer. Your goal is to create a high-signal, information-dense summary that captures the true "gems of wisdom" from the talk, not just a list of topics.

    **Your Guiding Principles (Analyze through this lens):**
    - **First-Principles Thinking:** Prioritize insights that connect practical advice back to underlying theoretical concepts (e.g., information theory, computational complexity, cognitive science).
    - **Pragmatic Engineering over Hype:** Focus on actionable, real-world strategies for building robust systems, especially those that challenge marketing hype or simplistic narratives.
    - **Mental Models & Frameworks:** Identify and extract novel analogies or structured frameworks that provide a new way to think about a problem.
    - **Counter-Intuitive Findings:** Highlight insights that go against common wisdom or reveal a surprising truth about AI behavior.

    **Task:**
    Process the following raw transcript and transform it into a clean, structured, and readable document. Follow these instructions precisely:
    1.  **Analyze the entire transcript** through the guiding principles above.
    2.  **Generate a structured header.** The header must contain:
        - A level-two Markdown heading `## Core Thesis` followed by a concise, one or two-sentence summary of the speaker's main, non-obvious argument, framed by your analytical role.
        - A level-two Markdown heading `## Key Concepts` followed by a bulleted list of the most important mental models, frameworks, and counter-intuitive findings discussed.
    3.  **Add a separator** `---` after the header.
    4.  **Clean the main body of the transcript.** This involves removing any timestamps or speaker labels. Preserve the original paragraph breaks. Do not summarize the body; it should be the full, cleaned text.

    **Raw Transcript:**
    ---
    {raw_text}
    ---
    """

    # Send the prompt to the model.
    response = model.generate_content(prompt, generation_config=GEN_CONFIG)
    
    # Return the generated text.
    return response.text

def _call_llm_for_classification(processed_text: str) -> str:
    """
    Makes the second LLM call to classify the text into one of the six themes.
    """
    print("Executing LLM call 2: Classification...")

    # This prompt is highly constrained to ensure a valid output.
    prompt = f"""
    You are an expert document classifier. Your task is to assign the following document to one, and only one, of the predefined thematic categories.

    **Predefined Categories:**
    1.  **AI Strategy & Leadership:** For content focused on business integration, change management, ROI, organizational structure, and high-level strategic planning for AI.
    2.  **Prompt & Context Engineering:** For content focused on the practical craft of prompting, context window management, chunking strategies, and specific techniques (e.g., RAG, Metaprompting).
    3.  **Agentic Architectures & Systems:** For content focused on the design of AI agents, tool use, memory systems, protocols like MCP, and hybrid architectures.
    4.  **Model Analysis & Limitations:** For content focused on the analysis of specific AI models, their underlying mechanisms, theoretical limitations, and core AI theory.
    5.  **Market Analysis & Future Trends:** For content focused on the broader AI market, competitive landscape, emerging technologies, and future predictions for the industry.
    6.  **News & Weekly Recap:** For news roundups, weekly recaps, and time-sensitive updates.
    6.  **Uncategorized:** If the document does not clearly fit into any of the above categories.

    **Instructions:**
    Analyze the following document. Based on its Core Thesis and Key Concepts, determine which single category it best fits into. Your response MUST be only the exact name of the category and nothing else.

    **Document to Classify:**
    ---
    {processed_text}
    ---
    """

    response = model.generate_content(prompt, generation_config=GEN_CONFIG)
    
    # Clean up the response to ensure it's just the category name.
    theme = response.text.strip()

    # Normalize to one of the predefined categories to avoid drift
    CANON = {
        "ai strategy & leadership": "AI Strategy & Leadership",
        "prompt & context engineering": "Prompt & Context Engineering",
        "agentic architectures & systems": "Agentic Architectures & Systems",
        "model analysis & limitations": "Model Analysis & Limitations",
        "market analysis & future trends": "Market Analysis & Future Trends",
        "news & weekly recap": "News & Weekly Recap",
        "uncategorized": "Uncategorized",
    }

    theme_lc = theme.lower().strip()
    # Remove any stray punctuation or trailing dots
    if theme_lc.endswith('.'):
        theme_lc = theme_lc[:-1]
    candidate = CANON.get(theme_lc)
    if candidate is None:
        # Fallback to Uncategorized if the model produced a near-miss
        normalized = "Uncategorized"
        print(f"Classifier produced non-canonical theme '{theme}'. Defaulting to 'Uncategorized'.")
    else:
        normalized = candidate
        if normalized != theme:
            print(f"Normalized theme: raw='{theme}' -> canonical='{normalized}'")
    return normalized


def _extract_date_iso(raw_text: str) -> tuple[str, str]:
    """Extract a leading 'date: ...' line and return (normalized_date, text_without_date).
    - Accepts patterns like 'date: 11-04-2025' (MM-DD-YYYY) or with '/', '.' separators.
    - Normalizes to ISO 'YYYY-MM-DD'. If ambiguous, prefers MM-DD if first <=12.
    - Returns ("unknown", original_text) if not found or unparsable.
    """
    lines = raw_text.splitlines()
    if not lines:
        return "unknown", raw_text
    first = lines[0].strip()
    m = re.match(r"^date\s*:\s*([0-9]{1,2})[./-]([0-9]{1,2})[./-]([0-9]{4})\s*$", first, flags=re.IGNORECASE)
    if not m:
        return "unknown", raw_text
    a, b, y = m.groups()
    mm = int(a)
    dd = int(b)
    yyyy = int(y)
    # If first number > 12, treat as DD-MM-YYYY
    if mm > 12:
        dd, mm = mm, dd
    try:
        dt = datetime(yyyy, mm, dd)
        iso = dt.strftime("%Y-%m-%d")
    except Exception:
        return "unknown", raw_text
    # Drop the first line
    without = "\n".join(lines[1:])
    return iso, without

def transcript_processor_and_classifier(request):
    """
    An HTTP-triggered Cloud Function that processes and classifies a transcript.
    """
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }

    if request.method == 'OPTIONS':
        return ('', 204, headers)

    if request.method != 'POST':
        return jsonify({"error": "Method not allowed"}), 405, headers

    request_json = request.get_json(silent=True)
    if not request_json or 'transcript_text' not in request_json:
        return jsonify({"error": "Invalid request: JSON payload with 'transcript_text' is required."}), 400, headers

    raw_text = request_json['transcript_text']
    # Extract date (if present) and remove it from the text we send to LLMs
    normalized_date, cleaned_text = _extract_date_iso(raw_text)

    try:
        processed_transcript = _call_llm_for_processing(cleaned_text)
        theme = _call_llm_for_classification(processed_transcript)

        return jsonify({
            "processed_transcript": processed_transcript,
            "theme": theme,
            "date": normalized_date
        }), 200, headers

    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        print(f"ERROR: {error_message}")
        return jsonify({"error": error_message}), 500, headers
