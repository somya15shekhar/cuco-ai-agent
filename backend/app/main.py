from fastapi import FastAPI
from app.routers.claims import router as claim_router
from app.routers.upload import router as upload_router
from app.routers.parse import router as parse_router

app = FastAPI(title="cuco Agent API")

app.include_router(claim_router)
app.include_router(upload_router)
app.include_router(parse_router)

@app.get("/")
def home():
    return {"message": "API Running"}



