from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.analyzer import process_repository, get_report, analyze_system_traces
import traceback

router = APIRouter()

class RepoRequest(BaseModel):
    url: str

@router.post("/analyze")
def analyze_repo(request: RepoRequest):
    print(f"Received analysis request (traces + code) for: {request.url}")
    try:
        # Analyze traces first, then correlate with code to find issues.
        result = analyze_system_traces(request.url)
        print("Analysis (traces + code) completed successfully")
        return result
    except Exception as e:
        print(f"Error processing repository and traces: {e}")
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
