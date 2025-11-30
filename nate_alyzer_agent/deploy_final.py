# deploy_final.py - CORRECTED MONOLITHIC DEPLOYMENT SCRIPT

import os
import vertexai
from vertexai import agent_engines
import requests
from langchain_core.tools import tool
from langchain_google_vertexai import ChatVertexAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages # <-- CORRECT IMPORT
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, AIMessage
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from google.oauth2 import id_token as google_id_token
from google.auth.transport.requests import Request as GoogleAuthRequest

# --- CONFIGURATION ---
PROJECT_ID = "nate-digital-twin"
LOCATION = "us-central1"
AGENT_MODEL = "gemini-2.5-flash"
RETRIEVER_URL = "https://us-central1-nate-digital-twin.cloudfunctions.net/gcs-transcript-retriever"
PROCESSOR_URL = "https://us-central1-nate-digital-twin.cloudfunctions.net/transcript-processor-and-classifier"
UPDATER_URL = "https://us-central1-nate-digital-twin.cloudfunctions.net/anthology-updater"

# --- HTTP session with retries/timeouts ---
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
_TIMEOUT = (5, 60)  # (connect, read) seconds
_ID_TOKEN_CACHE: Dict[str, str] = {}


def _auth_headers(audience_url: str) -> Dict[str, str]:
    """Return Authorization header with a Google ID token for the given audience URL.
    Caches tokens per audience within process lifetime."""
    try:
        token = _ID_TOKEN_CACHE.get(audience_url)
        if not token:
            token = google_id_token.fetch_id_token(GoogleAuthRequest(), audience_url)
            _ID_TOKEN_CACHE[audience_url] = token
        return {"Authorization": f"Bearer {token}"}
    except Exception as e:
        # Surface as error to the tool caller for clarity
        # Callers will receive a structured error if auth fails
        raise RuntimeError(f"Failed to obtain ID token for {audience_url}: {e}")


# --- Pydantic schemas for tools ---
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

# --- AGENT CLASS & GRAPH DEFINITION ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages] # <-- CORRECTED

 


# --- Pydantic schemas for API surface ---
class ToolCall(BaseModel):
    name: str
    args: Dict[str, object]


class QueryOutput(BaseModel):
    text: str = Field(..., description="Assistant text response")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tool calls requested by the model, if any")


    
class NateAlyzer:
    def __init__(self, model: str = AGENT_MODEL, project: str = PROJECT_ID, location: str = LOCATION):
        self.model_name = model
        self.project = project
        self.location = location
        self.tools = [retrieve_transcript, distill_and_classify_transcript, save_transcript_to_anthology]

    def set_up(self):
        # NOTE: We are now importing ToolNode inside set_up.
        # This is a best practice to ensure the class is pickle-able.
        from langgraph.prebuilt import ToolNode
        vertexai.init(project=self.project, location=self.location)
        model = ChatVertexAI(model_name=self.model_name, temperature=0)
        model_with_tools = model.bind_tools(self.tools)
        
        tool_node = ToolNode(self.tools)

        def model_node(state: AgentState):
            response = model_with_tools.invoke(state["messages"])
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

    def query(self, prompt: str) -> QueryOutput:
        # Convert the prompt into the graph's expected message format
        state = self.graph.invoke({"messages": [("user", prompt)]})
        last = state["messages"][-1]
        text_out = str(getattr(last, "content", ""))

        tool_calls: List[ToolCall] = []
        if isinstance(last, AIMessage):
            for tc in getattr(last, "tool_calls", []) or []:
                # tc is typically a dict-like or object with name/args
                name = getattr(tc, "name", None) or (tc.get("name") if isinstance(tc, dict) else None)
                args = getattr(tc, "args", None) or (tc.get("args") if isinstance(tc, dict) else None)
                if name and args is not None:
                    tool_calls.append(ToolCall(name=name, args=args))

        return QueryOutput(text=text_out, tool_calls=tool_calls)

# --- DEPLOYMENT LOGIC ---
def deploy():
    staging_bucket = f"gs://{PROJECT_ID}_cloudbuild"
    print(f"--- Initializing Vertex AI with Staging Bucket: {staging_bucket} ---")
    vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=staging_bucket)

    # Read requirements from this package directory to avoid path issues
    requirements = []
    here = os.path.dirname(__file__)
    req_path = os.path.join(here, "requirements.txt")
    if os.path.exists(req_path):
        with open(req_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    requirements.append(line)

    print(f"--- Deploying agent with requirements: {requirements} ---")
    
    remote_agent = agent_engines.create(
        NateAlyzer(), # Pass an instance so set_up(self) is bound
        display_name="Nate-alyzer",
        description="An agent to process and curate Nate Jones transcripts.",
        requirements=requirements
    )

    print("\n--- Deployment Complete ---")
    print(f"Deployed Agent Name: {remote_agent.name}")
    resource_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{remote_agent.name}"
    print(f"Deployed Agent Resource: {resource_path}")
    print("To use this AgentEngine later:")
    print(f"agent = agent_engines.get('{resource_path}')")

if __name__ == "__main__":
    deploy()
