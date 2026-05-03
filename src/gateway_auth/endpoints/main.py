"""
Run the server:
    uvicorn src.gateway_auth.endpoints.main:app --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.gateway_auth.endpoints.gateway_router import gateway_router
from src.gateway_auth.endpoints.oauth_router import oauth_router


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length"],
)

app.include_router(gateway_router)
app.include_router(oauth_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
