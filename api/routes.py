import uuid
from typing import Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel
from google.genai import types

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


@router.post("/chat")
async def chat(payload: ChatRequest, request: Request):
    runner = request.app.state.runner
    app_name = request.app.state.app_name
    user_id = "demo_user"
    session_id = payload.session_id or str(uuid.uuid4())

    try:
        await runner.session_service.create_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )

        content = types.Content(role="user", parts=[types.Part(text=payload.message)])

        answer_text = ""
        lineage = []

        for event in runner.run(user_id=user_id, session_id=session_id, new_message=content):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        answer_text = part.text
                    # Confirmed via debug_agent.py: function_response.response is the
                    # tool's return dict unchanged, so this pulls the real lineage out.
                    fr = getattr(part, "function_response", None)
                    if fr and isinstance(getattr(fr, "response", None), dict):
                        if "lineage" in fr.response:
                            lineage.append(fr.response["lineage"])

        return {"answer": answer_text, "lineage": lineage, "session_id": session_id}
    except Exception as exc:
        return {"answer": f"Something went wrong: {exc}", "lineage": []}