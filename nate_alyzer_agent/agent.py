import json
import logging
from typing import Annotated, Sequence, TypedDict

import vertexai
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

import config
from tools import (
    distill_and_classify_transcript,
    retrieve_transcript,
    save_transcript_to_anthology,
)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


class NateAlyzer:
    def __init__(
        self,
        model: str = config.AGENT_MODEL,
        project: str = config.PROJECT_ID,
        location: str = config.LOCATION,
        debug: bool = False,
    ):
        self.model_name = model
        self.project = project
        self.location = location
        self.debug = debug
        self.tools = [
            retrieve_transcript,
            distill_and_classify_transcript,
            save_transcript_to_anthology,
        ]
        self._tool_map = {t.name: t for t in self.tools}
        self._system_instruction = (
            "You are an orchestration agent. Use tools to complete tasks. "
            "When asked to process a video transcript, follow this plan strictly: "
            "1) Call retrieve_transcript(video_id). "
            "2) Take the returned transcript_text and call distill_and_classify_transcript(transcript_text). "
            "3) Take processed_transcript and theme from step 2 and call "
            "save_transcript_to_anthology(processed_transcript, theme, video_id). "
            "Always call tools in order, passing outputs into the next step. Do not answer directly."
        )

        # Minimal logger setup (only active when debug=True)
        self.logger = logging.getLogger("NateAlyzer")
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                handler.setLevel(logging.DEBUG)
                formatter = logging.Formatter(
                    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%H:%M:%S",
                )
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
        else:
            # Avoid emitting anything unless explicitly enabled
            self.logger.setLevel(logging.WARNING)

    def set_up(self):
        vertexai.init(project=self.project, location=self.location)
        model = ChatVertexAI(model_name=self.model_name, temperature=0)
        model_with_tools = model.bind_tools(self.tools)

        def call_model(state: AgentState):
            messages = state["messages"]
            response = model_with_tools.invoke(messages)
            if self.debug:
                tool_calls = getattr(response, "tool_calls", None) or []
                names = [tc.get("name") for tc in tool_calls]
                self.logger.debug(
                    f"Model responded with {len(tool_calls)} tool call(s): {names}"
                )
            return {"messages": [response]}

        def call_tools(state: AgentState):
            last = state["messages"][-1]
            tool_calls = getattr(last, "tool_calls", None) or []
            tool_messages = []
            if self.debug:
                self.logger.debug(f"Executing {len(tool_calls)} tool call(s)...")
            for tc in tool_calls:
                name = tc.get("name")
                args = tc.get("args") or {}
                tool = self._tool_map.get(name)
                if not tool:
                    content = json.dumps({"error": f"Unknown tool: {name}"})
                    if self.debug:
                        self.logger.debug(f"Unknown tool requested by model: {name}")
                    tool_messages.append(
                        ToolMessage(content=content, tool_call_id=tc.get("id", ""))
                    )
                    continue
                try:
                    if self.debug:
                        self.logger.debug(f"Calling tool '{name}' with args: {args}")
                    result = tool.invoke(args)
                except Exception as e:
                    result = {"error": f"Tool '{name}' execution failed: {e}"}
                    if self.debug:
                        self.logger.debug(f"Tool '{name}' raised exception: {e}")
                if not isinstance(result, str):
                    try:
                        content = json.dumps(result)
                    except Exception:
                        content = str(result)
                else:
                    content = result
                if self.debug:
                    preview = content if len(content) <= 300 else content[:300] + "..."
                    self.logger.debug(f"Tool '{name}' result preview: {preview}")
                tool_messages.append(
                    ToolMessage(content=content, tool_call_id=tc.get("id", ""))
                )
            return {"messages": tool_messages}

        def should_continue(state: AgentState):
            last = state["messages"][-1]
            tool_calls = getattr(last, "tool_calls", None) or []
            return "tools" if tool_calls else "end"

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", call_tools)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent", should_continue, {"tools": "tools", "end": END}
        )
        workflow.add_edge("tools", "agent")
        self.graph = workflow.compile()

    def query(self, inputs: dict):
        incoming = inputs.get("messages", [])
        if self.debug:
            self.logger.debug(
                f"Query received with {len(incoming)} incoming message(s); prepending system instruction."
            )
        state = {
            "messages": [SystemMessage(content=self._system_instruction), *incoming],
        }
        return self.graph.invoke(state)
