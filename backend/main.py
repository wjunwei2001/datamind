from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from api.chat import router as chat_router
from api.datasets import router as datasets_router
from services.agent_framework import execute_workflow
from services import storage
import uuid
import io
import pandas as pd
import json
import logging
from datetime import datetime

app = FastAPI(
    title="DataMind API",
    description="A multi-agent data analysis platform with LangGraph",
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
app.include_router(datasets_router, prefix="/api", tags=["datasets"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to DataMind API",
        "docs": "/docs",
        "endpoints": {
            "chat": "/api/chat",
            "datasets": "/api/datasets",
            "analyze": "/analyze"
        }
    }

@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...), 
    query: str = Form(...)
):
    """
    Direct file upload and analysis without storing in the catalog.
    
    This is useful for quick analyses without persisting the data.
    """
    try:
        # Read file into DataFrame
        file_contents = await file.read()
        df = pd.read_csv(io.BytesIO(file_contents))
        
        # Generate a temporary S3 key for this analysis
        temp_key = f"temp/{uuid.uuid4()}/{file.filename}"
        
        # Upload to S3 (optional, could be skipped for truly ephemeral analysis)
        await storage.put(temp_key, file_contents)
        
        # Prepare metadata for agent workflow
        df_metadata = {
            "s3_key": temp_key,
            "filename": file.filename,
            "sample_df": df.head(500),  # Sample for agents to work with
            "columns": list(df.columns),
        }
        
        # Execute agent workflow and stream results
        async def event_generator():
            try:
                async for chunk in execute_workflow(query, df_metadata):
                    yield chunk
            except Exception as e:
                logging.error(f"Error during direct analysis streaming: {e}", exc_info=True)
                error_event = {
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                yield "event: done\ndata: {}\n\n"
        
        return StreamingResponse(event_generator(), media_type="text/event-stream")
        
    except Exception as e:
        logging.error(f"Error in direct analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
