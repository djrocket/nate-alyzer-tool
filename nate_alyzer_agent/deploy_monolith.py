# deploy_monolith.py
# A strictly self-contained deployment script to avoid ModuleNotFoundError in Vertex AI Agent Engine.

import os
import logging
import requests
from typing import List, Optional, Dict, Any, TypedDict, Annotated, Sequence
from pydantic import BaseModel, Field

# Third-party imports that MUST be in requirements
import vertexai
from vertexai import agent_engines
from langchain_core.tools import tool
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from google.oauth2 import id_token as google_id_token
from google.auth.transport.requests import Request as GoogleAuthRequest
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# --- CONFIGURATION (HARDCODED FOR STABILITY) ---
PROJECT_ID = "nate-digital-twin"
LOCATION = "us-central1"
AGENT_MODEL = "gemini-2.5-flash"

# Cloud Function URLs (Standard naming convention based on project/region)
RETRIEVER_URL = f"https://{LOCATION}-{PROJECT_ID}.cloudfunctions.net/gcs-transcript-retriever"
PROCESSOR_URL = f"https://{LOCATION}-{PROJECT_ID}.cloudfunctions.net/transcript-processor-and-classifier"
UPDATER_URL = f"https://{LOCATION}-{PROJECT_ID}.cloudfunctions.net/anthology-updater"

# --- AUTH & NETWORK UTILS ---
# These are defined globally so they are available to the tools.
# Note: In the cloud environment, _SESSION will be re-initialized when the module is loaded.

def _make_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST", "GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

_SESSION = _make_session()
_TIMEOUT = (5, 300)
_ID_TOKEN_CACHE: Dict[str, str] = {}

def _auth_headers(audience_url: str) -> Dict[str, str]:
    """Return Authorization header with a Google ID token."""
    # In the remote environment, we might need to handle auth differently if not using default creds,
    # but Application Default Credentials (ADC) usually work for Cloud Run/Functions.
    try:
        token = _ID_TOKEN_CACHE.get(audience_url)
        if not token:
            # This requires google-auth
            token = google_id_token.fetch_id_token(GoogleAuthRequest(), audience_url)
            _ID_TOKEN_CACHE[audience_url] = token
        return {"Authorization": f"Bearer {token}"}
    except Exception as e:
        # Fallback or error. In some local contexts, this might fail if not logged in.
        # We log but don't crash, letting the request fail naturally if auth is missing.
        print(f"Warning: Could not fetch ID token for {audience_url}: {e}")
        return {}

# --- PYDANTIC MODELS ---
class RetrieveTranscriptArgs(BaseModel):
    video_id: str = Field(..., description="The YouTube or internal video identifier")

class DistillClassifyArgs(BaseModel):
    transcript_text: str = Field(..., description="Raw transcript text to process and classify")

class SaveAnthologyArgs(BaseModel):
    processed_transcript: str = Field(..., description="Processed/cleaned transcript text")
    theme: str = Field(..., description="Classified theme/category for the transcript")
    video_id: str = Field(..., description="Original video identifier for traceability")
    date: Optional[str] = Field(None, description="Normalized date for the entry (YYYY-MM-DD) or 'unknown'")

# --- TOOLS ---
@tool(args_schema=RetrieveTranscriptArgs)
def retrieve_transcript(video_id: str) -> dict:
    """Fetch the raw transcript text for a given video_id."""
    payload = {"video_id": video_id}
    try:
        headers = _auth_headers(RETRIEVER_URL)
        response = _SESSION.post(RETRIEVER_URL, json=payload, timeout=_TIMEOUT, headers=headers)
        response.raise_for_status()
        return {"status": "ok", "data": response.json()}
    except Exception as e:
        return {"status": "error", "message": f"retriever failed: {str(e)}"}

@tool(args_schema=DistillClassifyArgs)
def distill_and_classify_transcript(transcript_text: str) -> dict:
    """Analyze and classify raw transcript text."""
    payload = {"transcript_text": transcript_text}
    try:
        headers = _auth_headers(PROCESSOR_URL)
        response = _SESSION.post(PROCESSOR_URL, json=payload, timeout=_TIMEOUT, headers=headers)
        response.raise_for_status()
        return {"status": "ok", "data": response.json()}
    except Exception as e:
        return {"status": "error", "message": f"processor failed: {str(e)}"}

@tool(args_schema=SaveAnthologyArgs)
def save_transcript_to_anthology(processed_transcript: str, theme: str, video_id: str, date: Optional[str] = None) -> dict:
    """Save the processed transcript to the correct anthology."""
    payload = {"processed_transcript": processed_transcript, "theme": theme, "video_id": video_id}
    if date is not None:
        payload["date"] = date
    try:
        headers = _auth_headers(UPDATER_URL)
        response = _SESSION.post(UPDATER_URL, json=payload, timeout=_TIMEOUT, headers=headers)
        response.raise_for_status()
        return {"status": "ok", "data": response.json()}
    except Exception as e:
        return {"status": "error", "message": f"updater failed: {str(e)}"}

# --- AGENT STATE & CLASS ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

class NateAlyzer:
    def __init__(self, model: str = AGENT_MODEL, project: str = PROJECT_ID, location: str = LOCATION):
        self.model_name = model
        self.project = project
        self.location = location
        # Tools are defined at module level, so we just list them here.
        # This avoids pickling issues with nested functions or local definitions.
        self.tools = [retrieve_transcript, distill_and_classify_transcript, save_transcript_to_anthology]

    def set_up(self):
        """Initialize the agent resources. Called by Agent Engine on startup."""
        vertexai.init(project=self.project, location=self.location)
        
        model = ChatVertexAI(model_name=self.model_name, temperature=0)
        model_with_tools = model.bind_tools(self.tools)
        tool_node = ToolNode(self.tools)

        # Define system instruction
        system_instruction = (
            "You are an orchestration agent. Use tools to complete tasks. "
            "When asked to process a video transcript, follow this plan strictly: "
            "1) Call retrieve_transcript(video_id). "
            "2) Take the returned transcript_text and call distill_and_classify_transcript(transcript_text). "
            "3) Take processed_transcript and theme from step 2 and call "
            "save_transcript_to_anthology(processed_transcript, theme, video_id). "
            "Always call tools in order, passing outputs into the next step. Do not answer directly."
        )

        def model_node(state: AgentState):
            messages = state["messages"]
            # Prepend system message if not present (simple check)
            # In a robust app, we might manage this differently, but for now we trust the graph.
            if not isinstance(messages[0], SystemMessage):
                messages = [SystemMessage(content=system_instruction)] + list(messages)
            
            response = model_with_tools.invoke(messages)
            return {"messages": [response]}

        def should_continue(state: AgentState):
            last = state["messages"][-1]
            if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
                return "continue"
            return "end"

        workflow = StateGraph(AgentState)
        workflow.add_node("model", model_node)
        workflow.add_node("tools", tool_node)
        workflow.set_entry_point("model")
        workflow.add_conditional_edges("model", should_continue, {"continue": "tools", "end": END})
        workflow.add_edge("tools", "model")
        self.graph = workflow.compile()

    def query(self, prompt: str) -> dict:
        """Entry point for the Agent Engine."""
        # The input is a simple string prompt.
        # The output must be JSON-serializable.
        inputs = {"messages": [("user", prompt)]}
        result = self.graph.invoke(inputs)
        
        # Extract the final response text
        last = result["messages"][-1]
        text_out = str(getattr(last, "content", ""))
        
        return {"response": text_out}

# --- DEPLOYMENT ---
def deploy():
    # Staging bucket for the build artifacts
    staging_bucket = f"gs://{PROJECT_ID}_cloudbuild"
    print(f"--- Initializing Vertex AI with Staging Bucket: {staging_bucket} ---")
    vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=staging_bucket)

    # Explicit requirements list to ensure the remote environment matches
    requirements = [
        "google-cloud-aiplatform",
        "langchain",
        "langchain-google-vertexai",
        "langgraph",
        "pydantic",
        "requests",
        "google-auth",
        "google-auth-httplib2",
        "google-auth-oauthlib"
    ]

    print(f"--- Deploying NateAlyzer Monolith ---")
    
    # We pass the class instance. Agent Engine will pickle this instance.
    # Because the class and all its dependencies are in THIS file, 
    # and we are running THIS file, cloudpickle should capture it correctly 
    # as long as we don't have external local dependencies.
    remote_agent = agent_engines.create(
        NateAlyzer(),
        display_name="Nate-alyzer-Monolith",
        description="Monolithic deployment of NateAlyzer agent.",
        requirements=requirements
    )

    print("\n--- Deployment Complete ---")
    print(f"Deployed Agent Name: {remote_agent.name}")
    resource_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{remote_agent.name}"
    print(f"Deployed Agent Resource: {resource_path}")

if __name__ == "__main__":
    deploy()
