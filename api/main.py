from fastapi import FastAPI
from agent.agent_definition import build_runner
from api.routes import router

app = FastAPI(title="AI-Powered Warehouse Operations Assistant")
app.state.runner, app.state.app_name = build_runner()
app.include_router(router)