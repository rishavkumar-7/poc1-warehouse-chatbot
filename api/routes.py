from typing import Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


@router.post("/chat")
def chat(payload: ChatRequest, request: Request):
    """
    Input:  {"message": str, "session_id": str (optional)}
    Does:   passes the message to the shared Agent instance built at startup.
            NOTE: the exact call (agent.run / agent.invoke / etc.) depends on the
            installed google-adk version — check agent_definition.py's note.
    Output: {"answer": str, "lineage": [<lineage envelope of each tool call made>]}
    """
    agent = request.app.state.agent
    try:
        result = agent.run(payload.message)
        return {
            "answer": getattr(result, "text", str(result)),
            "lineage": getattr(result, "tool_lineage", []),
        }
    except Exception as exc:
        return {"answer": f"Something went wrong: {exc}", "lineage": []}
