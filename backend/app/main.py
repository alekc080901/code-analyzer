from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.ui.router import router
from app.db.database import init_db
from app.traces.tracer import init_tracer

app = FastAPI()

# Setup CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Init DB
init_db()

# Init Tracing
# init_tracer() # Already initialized in module, but explicit call logic can go here if needed.

app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Code Analyzer API"}

