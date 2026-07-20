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
    print("\n" + "="*60)
    print("🚀 Legal Case Summarizer Backend")
    print("="*60)
    print(f"✅ Server running on: http://localhost:8003")
    print(f"✅ API docs: http://localhost:8003/docs")
    print("="*60 + "\n")
    uvicorn.run("app:app", host="0.0.0.0", port=8003, reload=True)  # Changed to port 8003