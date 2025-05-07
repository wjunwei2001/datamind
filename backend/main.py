from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later!
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze")
async def analyze(csv: UploadFile = File(...)):
    # TODO: call agents, return JSON
    return {"rows": sum(1 for _ in csv.file)}
