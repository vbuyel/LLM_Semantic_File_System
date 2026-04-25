"""
Run the server:
    uvicorn src.gateway_auth.endpoints.main:app --port 8000
"""
from fastapi import FastAPI

from src.gateway_auth.endpoints.router import router


app = FastAPI()
app.include_router(router)
