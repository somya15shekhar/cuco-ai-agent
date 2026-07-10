from fastapi import FastAPI
from app.routers.claims import router as claim_router
from app.routers.upload import router as upload_router
from app.routers.parse import router as parse_router
from app.api.insurance import router as insurance_router
from app.models.claim import ParsedClaim
from app.agent.graph import run_cob_agent

app = FastAPI(title="cuco Agent API")

app.include_router(claim_router)
app.include_router(upload_router)
app.include_router(parse_router)
app.include_router(insurance_router)

@app.post("/process-claim")
def process_claim_endpoint(claim: ParsedClaim):
    """Executes the agentic Coordination of Benefits workflow for a parsed claim."""
    result = run_cob_agent(claim)
    return result

@app.get("/")
def home():
    return {"message": "API Running"}



