from app.git.loader import clone_repository, get_code_content, clean_up
from app.ai.client import analyze_code
from app.db.database import SessionLocal, Report
from app.traces.tracer import tracer

def process_repository(repo_url: str) -> dict:
    with tracer.start_as_current_span("process_repository"):
        db = SessionLocal()
        try:
            # 1. Clone
            with tracer.start_as_current_span("clone_repo"):
                repo_path = clone_repository(repo_url)
            
            try:
                # 2. Extract content
                with tracer.start_as_current_span("extract_content"):
                    content = get_code_content(repo_path)
                
                # 3. Analyze with AI
                with tracer.start_as_current_span("ai_analysis"):
                    result = analyze_code(content)
                
                # 4. Save to DB
                with tracer.start_as_current_span("save_db"):
                    report = Report(repo_url=repo_url, status="completed", result=result)
                    db.add(report)
                    db.commit()
                    db.refresh(report)
                    return {"id": report.id, "status": "completed", "result": result}
            
            finally:
                clean_up(repo_path)

        except Exception as e:
            with tracer.start_as_current_span("error_handling"):
                report = Report(repo_url=repo_url, status="failed", result=str(e))
                db.add(report)
                db.commit()
                return {"id": report.id, "status": "failed", "error": str(e)}
        finally:
            db.close()

def get_report(report_id: int):
    db = SessionLocal()
    try:
        return db.query(Report).filter(Report.id == report_id).first()
    finally:
        db.close()

