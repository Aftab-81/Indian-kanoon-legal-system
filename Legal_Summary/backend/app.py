from logger_setup import get_logger
logger = get_logger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.cases import router as cases_router

app = FastAPI(title="Judge Project - Case Summarizer")

# Configure CORS - MUST be before adding routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative frontend port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
)

app.include_router(cases_router, prefix="/api")

# ...existing code...
if __name__ == "__main__":
    import uvicorn
    logger.info("\n" + "="*60)
    logger.info("🚀 Legal Case Summarizer Backend")
    logger.info("="*60)
    logger.info(f"✅ Server running on: http://localhost:8003")
    logger.info(f"✅ API docs: http://localhost:8003/docs")
    logger.info("="*60 + "\n")
    uvicorn.run("app:app", host="0.0.0.0", port=8003, reload=True)  # Changed to port 8003