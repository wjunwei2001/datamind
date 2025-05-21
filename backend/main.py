from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from api.chat import router as chat_router
from api.datasets import router as datasets_router
from services.agent_framework import execute_workflow
from services import storage
import uuid
import io
import os
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

# Create figures directory if it doesn't exist
os.makedirs("figures", exist_ok=True)

# Mount figures directory as static files
app.mount("/figures", StaticFiles(directory="figures"), name="figures")

# Include routers
app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(datasets_router, prefix="/api", tags=["datasets"])

@app.get("/figure/{figure_name}")
async def get_figure(figure_name: str):
    """
    Get a figure from the figures directory.
    
    Args:
        figure_name: The name of the figure file
        
    Returns:
        The figure file
        
    Raises:
        HTTPException: If the figure is not found
    """
    figure_path = f"figures/{figure_name}"
    if not os.path.exists(figure_path):
        raise HTTPException(status_code=404, detail="Figure not found")
    
    return FileResponse(figure_path)

@app.get("/")
async def root():
    return {
        "message": "Welcome to DataMind API",
        "docs": "/docs",
        "endpoints": {
            "chat": "/api/chat",
            "datasets": "/api/datasets",
            "analyze": "/analyze",
            "figure": "/figure/{figure_name}"
        }
    }

@app.post("/analyze")
async def analyze(
    request: Request,
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
                    # If chunk contains saved_figures, add figure_urls to the response
                    if "data: " in chunk:
                        data = json.loads(chunk[6:])  # Remove "data: " prefix
                        if "data" in data and "analysis_results" in data["data"] and "saved_figures" in data["data"]["analysis_results"]:
                            # Add base URL for accessing the figures
                            figures = data["data"]["analysis_results"]["saved_figures"]
                            # Convert paths to URLs
                            base_url = request.base_url
                            figure_urls = {}
                            for key, path in figures.items():
                                # Extract filename from path
                                filename = os.path.basename(path)
                                # Create absolute URL
                                figure_urls[key] = f"{base_url}figure/{filename}"
                            
                            data["data"]["analysis_results"]["figure_urls"] = figure_urls
                            # Re-serialize the modified data
                            chunk = f"data: {json.dumps(data)}\n\n"
                    
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
