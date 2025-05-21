from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, status, Body
from fastapi.responses import StreamingResponse, JSONResponse
from services import storage, db # S3 client and DB interface
from services.agent_framework import execute_workflow  # Import our new agent framework
from typing import Dict, Any, Optional
import uuid
import pandas as pd
import io
import json
import logging
import asyncio
from datetime import datetime
import os
import numpy as np
from functools import lru_cache

router = APIRouter(prefix="/chat", tags=["chat"])

# Simple in-memory cache for dataframes
# In production, consider using Redis or another distributed cache
dataset_cache = {}

async def _get_dataframe_sample_from_s3(s3_key: str) -> Optional[pd.DataFrame]:
    """Helper to fetch a sample of a CSV from S3 and return as a DataFrame."""
    try:
        # Check if dataset is in cache first
        if s3_key in dataset_cache:
            logging.info(f"Using cached dataset for {s3_key}")
            return dataset_cache[s3_key]
            
        # Not in cache, fetch from S3
        file_bytes = await storage.get(s3_key)
        if file_bytes:
            df = pd.read_csv(io.BytesIO(file_bytes))
            # Add to cache for future use
            dataset_cache[s3_key] = df
            return df
        return None
    except Exception as e:
        logging.error(f"Error reading sample from S3 key {s3_key}: {e}")
        return None

@router.get("/dataset/{dataset_id}")
async def get_dataset_metadata(dataset_id: str):
    """
    Get basic metadata about a dataset without loading the full content.
    Useful for displaying info in the UI.
    """
    try:
        # Fetch dataset metadata from DB
        dataset_db_meta = await db.get_meta(dataset_id)
        if not dataset_db_meta:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                               detail=f"Dataset with ID '{dataset_id}' not found.")

        # Access attributes directly on the Pydantic model
        s3_key = dataset_db_meta.s3_key
        filename = dataset_db_meta.filename
        
        if not s3_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                               detail=f"S3 key not found for dataset ID '{dataset_id}'.")

        # Load the dataframe to cache it and get basic stats
        sample_df = await _get_dataframe_sample_from_s3(s3_key)
        
        if sample_df is None or sample_df.empty:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Dataset is empty or could not be loaded."}
            )
            
        # Create a smaller preview with just the basic info for the UI
        # This doesn't send the whole dataset
        sample_preview = sample_df.head(5).to_dict(orient="records")
        
        # Create a safe preview by replacing problematic values
        for record in sample_preview:
            for key, value in record.items():
                if pd.isna(value) or (isinstance(value, float) and (np.isinf(value) or np.isnan(value))):
                    record[key] = None
        
        # Return just the metadata (not the full dataset)
        metadata = {
            "dataset_id": dataset_id,
            "s3_key": s3_key,
            "filename": filename,
            "columns": list(sample_df.columns),
            "row_count": len(sample_df),
            "preview": sample_preview
        }
        
        return JSONResponse(content=metadata)
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching dataset metadata: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                           detail=f"An error occurred: {str(e)}")

@router.post("/stream/{dataset_id}")
async def chat_with_existing_dataset(
    request: Request, 
    dataset_id: str,
    query: str = Form(...)
):
    """Initiates a streaming chat analysis for an existing, cataloged dataset."""
    try:
        # 1. Fetch dataset metadata from DB
        dataset_db_meta = await db.get_meta(dataset_id)
        if not dataset_db_meta:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dataset with ID '{dataset_id}' not found.")

        # Access attributes directly on the Pydantic model
        s3_key = dataset_db_meta.s3_key
        filename = dataset_db_meta.filename
        if not s3_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"S3 key not found for dataset ID '{dataset_id}'. Dataset may be incomplete.")

        # 2. Get the dataset from our cache or load it from S3
        sample_df = await _get_dataframe_sample_from_s3(s3_key)
        
        # Check if sample_df is empty or None, and provide a meaningful error
        if sample_df is None or sample_df.empty:
            logging.warning(f"Empty or missing DataFrame for dataset {dataset_id}")
            # Create a simple response with the error
            async def error_generator():
                error_json = json.dumps({
                    "data": {
                        "error": "Could not process dataset. The sample DataFrame is empty or could not be loaded."
                    },
                    "timestamp": datetime.utcnow().isoformat()
                })
                yield f"data: {error_json}\n\n"
                yield "event: done\ndata: {}\n\n"
            
            return StreamingResponse(error_generator(), media_type="text/event-stream")

        # Convert Pydantic model to dictionary for the agent workflow
        db_meta_dict = dataset_db_meta.model_dump() if hasattr(dataset_db_meta, 'model_dump') else dataset_db_meta.dict()

        df_metadata_for_agents = {
            "s3_key": s3_key,
            "filename": filename,
            "sample_df": sample_df, 
            "columns": list(sample_df.columns),
        }

        # 3. Execute the agent workflow
        async def event_generator():
            try:
                # Store the final story when we receive it
                final_story = None
                
                # Stream results from the agent workflow
                async for chunk in execute_workflow(query, df_metadata_for_agents):
                    if await request.is_disconnected():
                        logging.info(f"Client disconnected for dataset {dataset_id}, query: '{query}'. Stopping stream.")
                        break
                        
                    # Process the chunk data
                    if chunk.startswith("data: "):
                        try:
                            data = json.loads(chunk[6:])  # Remove "data: " prefix
                            
                            # Check for and extract final_story
                            if "data" in data:
                                # Check directly in data object
                                if "final_story" in data["data"]:
                                    final_story = data["data"]["final_story"]
                                # Also check in story node result
                                elif "story" in data["data"] and "final_story" in data["data"]["story"]:
                                    final_story = data["data"]["story"]["final_story"]
                            
                            # Process analysis results and add figure URLs
                            if "data" in data and "analysis" in data["data"] and "analysis_results" in data["data"]["analysis"] and "saved_figures" in data["data"]["analysis"]["analysis_results"]:
                                # Add base URL for accessing the figures
                                figures = data["data"]["analysis"]["analysis_results"]["saved_figures"]
                                # Convert paths to URLs
                                base_url = str(request.base_url)
                                figure_urls = {}
                                for key, path in figures.items():
                                    # Extract filename from path
                                    filename = os.path.basename(path)
                                    # Create absolute URL
                                    figure_urls[key] = f"{base_url}figure/{filename}"
                                
                                data["data"]["analysis"]["analysis_results"]["figure_urls"] = figure_urls
                                
                            # Re-serialize the modified data
                            chunk = f"data: {json.dumps(data)}\n\n"
                        except json.JSONDecodeError as json_err:
                            # If we can't parse the JSON, log it and pass the chunk as is
                            logging.error(f"JSON parsing error in chunk: {json_err}")
                            # Create a valid JSON error message instead
                            error_json = json.dumps({
                                "data": {
                                    "error": f"Error parsing data: {str(json_err)}"
                                },
                                "timestamp": datetime.utcnow().isoformat()
                            })
                            chunk = f"data: {error_json}\n\n"
                    
                    yield chunk
                
                # At the end of processing, send the final story separately if available
                if final_story:
                    # Format final story for chat display
                    story_message = {
                        "data": {
                            "chat_message": {
                                "role": "assistant",
                                "content": format_story_for_display(final_story),
                                "metadata": {
                                    "type": "data_story",
                                    "story_details": final_story
                                }
                            }
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    yield f"data: {json.dumps(story_message)}\n\n"
                
            except asyncio.CancelledError:
                logging.info(f"Stream cancelled for dataset {dataset_id}, query: '{query}'.")
            except Exception as e:
                logging.error(f"Error during event streaming for dataset {dataset_id}: {e}", exc_info=True)
                error_event = {"role": "system", "content": {"error": str(e)}, "ts": datetime.utcnow().isoformat()}
                error_json = json.dumps(error_event)
                yield f"data: {error_json}\n\n"
            finally:
                logging.info(f"Stream generator finished for dataset {dataset_id}, query: '{query}'.")
                # Always ensure we send a proper "done" event
                yield "event: done\ndata: {}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except HTTPException as http_exc:
        logging.error(f"HTTPException in chat_with_existing_dataset for {dataset_id}: {http_exc.detail}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error in chat_with_existing_dataset for {dataset_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

def format_story_for_display(story: Dict[str, Any]) -> str:
    """Format the final story in a readable way for display in the chat interface."""
    if not story:
        return "No data story available."
    
    result = [f"# {story.get('title', 'Data Story')}"]
    
    # Add summary
    if "summary" in story:
        result.append(f"\n## Summary\n{story['summary']}")
    
    # Add sections
    if "sections" in story and story["sections"]:
        for section in story["sections"]:
            result.append(f"\n## {section.get('heading', 'Section')}\n{section.get('content', '')}")
    
    # Add insights
    if "insights" in story and story["insights"]:
        result.append("\n## Key Insights")
        for insight in story["insights"]:
            result.append(f"- {insight}")
    
    # Add next steps
    if "next_steps" in story and story["next_steps"]:
        result.append("\n## Recommended Next Steps")
        for step in story["next_steps"]:
            result.append(f"- {step}")
    
    return "\n".join(result)

# Optional: Keep an ephemeral chat endpoint if direct uploads are still needed for non-cataloged analysis
# This would be similar to the previous version of chat.py but would not interact with db.py for cataloging.
# For now, focusing on the catalog-based approach.

# @router.post("/stream/ephemeral")
# async def chat_ephemeral_upload(...): ...
