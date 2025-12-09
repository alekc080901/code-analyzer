from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.analyzer import process_repository, get_report, analyze_system_traces
import traceback

router = APIRouter()

class RepoRequest(BaseModel):
    url: str

class TraceRequest(BaseModel):
    url: Optional[str] = None

@router.post("/analyze")
def analyze_repo(request: RepoRequest):
    print(f"Received analysis request for: {request.url}")
    try:
        result = process_repository(request.url)
        print("Analysis completed successfully")
        return result
    except Exception as e:
        print(f"Error processing repository: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-traces")
def analyze_traces_endpoint(request: TraceRequest):
    print(f"Received trace analysis request. Repo URL: {request.url}")
    try:
        result = analyze_system_traces(request.url)
        return result
    except Exception as e:
        print(f"Error analyzing traces: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/report/{report_id}")
def read_report(report_id: int):
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@router.get("/health")
def health_check():
    return {"status": "ok"}
