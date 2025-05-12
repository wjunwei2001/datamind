from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from api.chat import router as chat_router

app = FastAPI(
    title="DataMind API",
    description="A chat-first data analysis API powered by CrewAI",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later!
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router, prefix="/api", tags=["chat"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to DataMind API",
        "docs": "/docs",
        "endpoints": {
            "chat": "/api/chat"
        }
    }

@app.post("/analyze")
async def analyze(csv: UploadFile = File(...)):
    # TODO: call agents, return JSON
    return {"rows": sum(1 for _ in csv.file)}
