from app.git.loader import clone_repository, get_code_content, clean_up
from app.ai.client import analyze_code
from app.db.database import SessionLocal, Report
from app.traces.tracer import tracer
import requests
import json
import os
import yaml
import glob

# JAEGER_QUERY_HOST должен указывать на хост, где крутится Jaeger UI/Query (порт 16686)
JAEGER_API_URL = os.getenv("JAEGER_QUERY_HOST", "http://host.docker.internal:16686")

INFRA_SERVICES = {"db", "postgres", "redis", "jaeger", "prometheus", "grafana", "nginx"}

def fetch_traces(service_name: str, limit: int = 5):
    """Fetches traces from Jaeger for a specific service."""
    try:
        url = f"{JAEGER_API_URL}/api/traces?service={service_name}&limit={limit}"
        print(f"Fetching traces from: {url}")
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching traces for {service_name}: {e}")
        return {"error": str(e), "data": []}

def format_traces_for_analysis(traces_data):
    """Simplifies trace JSON for LLM analysis."""
    if "data" not in traces_data:
        return str(traces_data)
    
    summary = []
    for trace in traces_data["data"]:
        trace_id = trace.get("traceID")
        spans = []
        for span in trace.get("spans", []):
            spans.append({
                "operation": span.get("operationName"),
                "duration": span.get("duration"),
                "startTime": span.get("startTime"),
                "tags": {t["key"]: t["value"] for t in span.get("tags", []) if t["key"] in ["http.method", "http.status_code", "error", "http.url"]}
            })
        summary.append(f"Trace {trace_id}:\n" + json.dumps(spans, indent=2))
    return "\n\n".join(summary)

def extract_service_names(repo_path: str) -> list[str]:
    """Parses docker-compose.yml to find service names."""
    service_names = set()
    
    # Ищем все docker-compose файлы
    compose_files = glob.glob(os.path.join(repo_path, "**", "docker-compose*.y*ml"), recursive=True)
    
    for compose_file in compose_files:
        try:
            with open(compose_file, 'r') as f:
                data = yaml.safe_load(f)
                if 'services' in data:
                    for service in data['services']:
                        # Игнорируем инфраструктурные сервисы по эвристике
                        if service not in INFRA_SERVICES:
                            service_names.add(service)
        except Exception as e:
            print(f"Error parsing {compose_file}: {e}")
            
    return list(service_names)

def get_available_services() -> list[str]:
    """Reads service list directly from Jaeger to align with actual service names."""
    try:
        url = f"{JAEGER_API_URL}/api/services"
        print(f"Fetching available services from: {url}")
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        services = data.get("data", [])
        return [s for s in services if s not in INFRA_SERVICES]
    except Exception as e:
        print(f"Error fetching services list from Jaeger: {e}")
        return []

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

def analyze_system_traces(repo_url: str = None) -> dict:
    """Fetches traces for services and analyzes them ALONG WITH source code."""
    with tracer.start_as_current_span("analyze_system_traces"):
        
        service_names = []
        code_context = ""
        db = SessionLocal()
        
        if repo_url:
            # 1. Clone & Analyze Code structure
            with tracer.start_as_current_span("clone_and_read_code"):
                repo_path = clone_repository(repo_url)
                try:
                    service_names = extract_service_names(repo_path)
                    
                    # Читаем код, чтобы дать контекст модели
                    # get_code_content читает .py, .js и т.д.
                    raw_code = get_code_content(repo_path)
                    
                    # Ограничиваем размер кода, чтобы осталось место для трейсов
                    # GigaChat имеет большой контекст, но все же.
                    # Допустим, выделим 15000 символов под код.
                    code_context = f"Source Code Context:\n\n{raw_code[:15000]}\n\n"
                    if len(raw_code) > 15000:
                        code_context += "...(code truncated)...\n\n"
                        
                finally:
                    clean_up(repo_path)
        
        # Fallback
        if not service_names:
            jaeger_services = get_available_services()
            service_names = jaeger_services or ["service-a", "service-b"]
        
        print(f"Analyzing traces for services: {service_names}")

        traces_context = ""
        has_data = False

        # 2. Fetch Traces
        for service in service_names:
            traces = fetch_traces(service)
            formatted = format_traces_for_analysis(traces)
            if formatted.strip():
                traces_context += f"Traces for Service '{service}':\n{formatted}\n\n"
                has_data = True
            else:
                traces_context += f"No traces found for Service '{service}'.\n\n"

        if not has_data:
             return {"status": "completed", "result": f"No traces found in Jaeger for services: {', '.join(service_names)}. Please ensure traffic is generated."}

        # 3. Combine Traces-first (primary signal) + Code context
        full_prompt_content = f"=== SYSTEM TRACES ===\n{traces_context}\n\n=== SOURCE CODE CONTEXT ===\n{code_context}"

        # 4. Analyze
        result = analyze_code(full_prompt_content)

        # 5. Persist report so it shows up in UI refresh
        try:
            with tracer.start_as_current_span("save_db_traces"):
                report = Report(repo_url=repo_url, status="completed", result=result)
                db.add(report)
                db.commit()
                db.refresh(report)
        except Exception as e:
            print(f"Error saving trace report: {e}")
            db.rollback()
        finally:
            db.close()
        
        return {"status": "completed", "result": result}

def get_report(report_id: int):
    db = SessionLocal()
    try:
        return db.query(Report).filter(Report.id == report_id).first()
    finally:
        db.close()

def list_reports(limit: int = 20):
    """Returns latest reports for frontend consumption."""
    db = SessionLocal()
    try:
        reports = (
            db.query(Report)
            .order_by(Report.id.desc())
            .limit(limit)
            .all()
        )
        print(reports)
        return [
            {
                "id": r.id,
                "repo_url": r.repo_url,
                "status": r.status,
                "result": r.result,
            }
            for r in reports
        ]
    finally:
        db.close()

def delete_report(report_id: int) -> bool:
    """Deletes a report by id. Returns True if deleted, False if not found."""
    db = SessionLocal()
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            return False
        db.delete(report)
        db.commit()
        return True
    finally:
        db.close()
