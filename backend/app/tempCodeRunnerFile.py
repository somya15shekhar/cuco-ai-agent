from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.claims import router as claim_router
from app.routers.upload import router as upload_router
from app.routers.parse import router as parse_router
from app.api.insurance import router as insurance_router
from app.models.claim import ParsedClaim
from app.agent.graph import run_cob_agent
from app.api.household import router as household_router

app = FastAPI(title="cuco Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(claim_router)
app.include_router(upload_router)
app.include_router(parse_router)
app.include_router(insurance_router)
app.include_router(household_router)

import os
from fastapi.staticfiles import StaticFiles

@app.post("/process-claim")
def process_claim_endpoint(claim: ParsedClaim):
    """Executes the agentic Coordination of Benefits workflow for a parsed claim."""
    result = run_cob_agent(claim)
    return result

# Serve the frontend website statically from the root route
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")



