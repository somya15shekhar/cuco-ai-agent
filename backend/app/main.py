from fastapi import FastAPI
from app.routers.claims import router as claim_router

app = FastAPI(title="cuCO Agent API")

app.include_router(claim_router)

@app.get("/")
def home():
    return {"message": "API Running"}