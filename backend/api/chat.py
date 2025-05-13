from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from services import storage, db # S3 client and DB interface
from services.agents import planner # The multi-agent planner
from typing import Dict, Any, Optional
import uuid
import pandas as pd
import io
import json
import logging
import asyncio
from datetime import datetime

router = APIRouter(prefix="/chat", tags=["chat"])

@router.on_event("startup")
async def startup_event():
    logging.info("Booting agents for chat router...")
    if not planner.agent_instances: # Boot agents if not already booted
        planner.boot_agents()

async def _get_dataframe_sample_from_s3(s3_key: str, nrows: int = 500) -> Optional[pd.DataFrame]:
    """Helper to fetch a sample of a CSV from S3 and return as a DataFrame."""
    try:
        file_bytes = await storage.get(s3_key)
        if file_bytes:
            return pd.read_csv(io.BytesIO(file_bytes), nrows=nrows)
        return None
    except Exception as e:
        logging.error(f"Error reading sample from S3 key {s3_key}: {e}")
        return None

@router.post("/stream/{dataset_id}")
async def chat_with_existing_dataset(
    request: Request, 
    dataset_id: str,
    query: str = Form(...)
):
    """Initiates a streaming chat analysis for an existing, cataloged dataset."""
    try:
        # 1. Fetch dataset metadata from DB using dataset_id
        dataset_db_meta = await db.get_meta(dataset_id)
        if not dataset_db_meta:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dataset with ID '{dataset_id}' not found.")

        s3_key = dataset_db_meta.get("s3_key")
        filename = dataset_db_meta.get("filename", "N/A")
        if not s3_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"S3 key not found for dataset ID '{dataset_id}'. Dataset may be incomplete.")

        # 2. Prepare metadata for the planner, including an S3 sample for EDA
        sample_df = await _get_dataframe_sample_from_s3(s3_key, nrows=500)
        # Agents should be robust to sample_df being None if S3 read fails or file is empty/corrupt

        df_metadata_for_planner = {
            "s3_key": s3_key,
            "filename": filename,
            "dataset_id": dataset_id,
            "db_meta": dataset_db_meta, # Full DB meta might be useful for agents
            "sample_df": sample_df, 
            "columns": list(sample_df.columns) if sample_df is not None else dataset_db_meta.get("columns", []),
        }

        # 3. Trigger the planner
        await planner.plan_and_execute(query, df_metadata_for_planner)

        # 4. Stream results
        async def event_generator():
            try:
                async for chunk in planner.stream_results():
                    if await request.is_disconnected():
                        logging.info(f"Client disconnected for dataset {dataset_id}, query: '{query}'. Stopping stream.")
                        # TODO: Implement robust task cancellation that propagates to agents
                        break
                    yield chunk
            except asyncio.CancelledError:
                logging.info(f"Stream cancelled for dataset {dataset_id}, query: '{query}'.")
            except Exception as e:
                logging.error(f"Error during event streaming for dataset {dataset_id}: {e}", exc_info=True)
                error_event = {"role": "system", "content": {"error": str(e)}, "ts": datetime.utcnow().isoformat()}
                yield f"data: {json.dumps(error_event)}\n\n"
            finally:
                logging.info(f"Stream generator finished for dataset {dataset_id}, query: '{query}'.")

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except HTTPException as http_exc:
        logging.error(f"HTTPException in chat_with_existing_dataset for {dataset_id}: {http_exc.detail}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error in chat_with_existing_dataset for {dataset_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

# Optional: Keep an ephemeral chat endpoint if direct uploads are still needed for non-cataloged analysis
# This would be similar to the previous version of chat.py but would not interact with db.py for cataloging.
# For now, focusing on the catalog-based approach.

# @router.post("/stream/ephemeral")
# async def chat_ephemeral_upload(...): ...
