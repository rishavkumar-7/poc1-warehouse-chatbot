from fastapi import FastAPI
from agent.agent_definition import build_agent
from api.routes import router

app = FastAPI(title="AI-Powered Warehouse Operations Assistant")
app.state.agent = build_agent()
app.include_router(router)
