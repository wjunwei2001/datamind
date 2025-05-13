from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from typing import Annotated, Optional, Dict, Any
from uuid import uuid4
from pydantic import BaseModel, Field
from datetime import datetime
from services import db, storage
import pandas as pd
import io
import json # For serializing summary if necessary
import logging

router = APIRouter(prefix="/datasets", tags=["datasets"])

class DatasetMeta(BaseModel):
    rows: int = Field(..., description="Number of rows in the dataset")
    columns: list[str] = Field(..., description="List of column names")
    dtypes: Dict[str, str] = Field(..., description="Data types of each column")
    # Storing describe() output which can be complex, ensure DB compatibility
    summary: Dict[str, Any] = Field(..., description="Statistical summary of numeric columns")

class DatasetOut(DatasetMeta):
    id: str = Field(..., description="Unique identifier of the dataset")
    description: Optional[str] = Field(None, description="Optional description of the dataset")
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC), description="Timestamp of dataset creation")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC), description="Timestamp of last update")
    s3_key: str = Field(..., description="S3 key for the dataset file")
    filename: str = Field(..., description="Original filename of the dataset")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "rows": 1000,
                "columns": ["id", "name", "value"],
                "dtypes": {"id": "int64", "name": "object", "value": "float64"},
                "summary": {"value": {"mean": 42.5, "std": 10.2, "min": 1.0, "25%": 35.0, "50%": 42.0, "75%": 50.0, "max": 100.0, "count": 1000.0}},
                "description": "Sample dataset for testing",
                "created_at": "2024-02-20T12:00:00Z",
                "updated_at": "2024-02-20T12:00:00Z",
                "s3_key": "datasets/550e8400-e29b-41d4-a716-446655440000/data.csv",
                "filename": "data.csv"
            }
        }
        # Pydantic v2 config
        # from_attributes = True # if you were creating from ORM models directly

def _extract_basic_metadata(df: pd.DataFrame) -> Dict[str, Any]:
    """Extracts basic metadata from a pandas DataFrame."""
    meta = {
        "rows": len(df),
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        # df.describe() can include NaNs, which json.dumps handles as null.
        # It can also include timestamps, ensure your DB can handle the describe() output.
        # Forcing to_dict to handle potential non-serializable types from describe()
        "summary": json.loads(df.describe(include='all').to_json(default_handler=str, date_format='iso'))
    }
    return meta

@router.post("", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    file: Annotated[UploadFile, File(description="The CSV file to upload")],
    description: Annotated[Optional[str], Form(description="Optional description of the dataset")] = None,
):
    uid = uuid4().hex
    s3_key = ""
    try:
        s3_key = await storage.save(file, uid) # pass uid as part of path/prefix for S3
        
        # For metadata, read the file content (or a sample for large files)
        await file.seek(0) # Reset file pointer to read again
        file_content_bytes = await file.read()
        await file.close()

        # Run pandas operations in a thread pool to avoid blocking event loop
        def sync_extract_metadata(content_bytes: bytes) -> Dict[str, Any]:
            try:
                df = pd.read_csv(io.BytesIO(content_bytes))
                return _extract_basic_metadata(df)
            except Exception as e:
                logging.error(f"Error processing CSV for metadata: {e}")
                # You might want to raise a specific error or return partial/default meta
                raise ValueError(f"Could not parse CSV for metadata: {e}")

        meta = await run_in_threadpool(sync_extract_metadata, file_content_bytes)
        
        now = datetime.now(datetime.UTC)
        db_payload = {
            **meta,
            "id": uid,
            "description": description,
            "s3_key": s3_key,
            "filename": file.filename, 
            # Timestamps are handled by default_factory in Pydantic model for response,
            # but need to be explicitly passed to DB if your DB schema expects them.
            # Assuming db.insert_dataset will handle created_at and updated_at based on its signature.
        }
        # Ensure db.insert_dataset matches this payload signature
        await db.insert_dataset(
            dataset_id=uid, 
            meta=meta, # This should contain rows, columns, dtypes, summary
            description=description, 
            s3_key=s3_key, 
            filename=file.filename,
            created_at=now, # Pass now, as db method signature might require it
            updated_at=now
        )
        
        return DatasetOut(
            id=uid,
            description=description,
            s3_key=s3_key,
            filename=file.filename,
            created_at=now,
            updated_at=now,
            **meta
        )
    except ValueError as ve: # Catch specific error from metadata extraction
        if s3_key: # Attempt to clean up S3 if upload succeeded but metadata failed
            try: await storage.delete(s3_key)
            except Exception as s3_e: logging.error(f"Failed to cleanup S3 object {s3_key} after metadata error: {s3_e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logging.error(f"Error creating dataset: {e}", exc_info=True)
        if s3_key: # Attempt to clean up S3 if upload succeeded but something else failed
            try: await storage.delete(s3_key)
            except Exception as s3_e: logging.error(f"Failed to cleanup S3 object {s3_key} after general error: {s3_e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing dataset: {str(e)}"
        )

@router.get("/{dataset_id}/meta", response_model=DatasetMeta)
async def get_dataset_meta(
    dataset_id: Annotated[str, Field(..., description="The unique identifier of the dataset")]
):
    """
    Get metadata for a specific dataset.
    
    Args:
        dataset_id: The unique identifier of the dataset
        
    Returns:
        Dataset metadata
        
    Raises:
        HTTPException: If the dataset is not found or there's an error
    """
    try:
        meta = await db.get_meta(dataset_id)
        if not meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found"
            )
        return DatasetMeta(**meta)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving dataset metadata: {str(e)}"
        )

@router.get("", response_model=list[DatasetOut])
async def list_datasets(
    skip: Annotated[int, Field(0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Field(10, description="Maximum number of records to return")] = 10
):
    """
    List all available datasets with pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of dataset records
        
    Raises:
        HTTPException: If there's an error listing datasets
    """
    try:
        datasets_from_db = await db.list_datasets(skip=skip, limit=limit)
        return [DatasetOut(**ds_data) for ds_data in datasets_from_db]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing datasets: {str(e)}"
        )

@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: Annotated[str, Field(..., description="The unique identifier of the dataset")]
):
    """
    Delete a dataset and its associated files.
    
    Args:
        dataset_id: The unique identifier of the dataset
        
    Raises:
        HTTPException: If there's an error deleting the dataset
    """
    try:
        dataset_info = await db.get_meta(dataset_id) # Fetch s3_key before deleting DB record
        if not dataset_info or not dataset_info.get("s3_key"):
            # If no s3_key, maybe just delete DB record or log warning
            logging.warning(f"Dataset {dataset_id} not found or no s3_key for deletion from storage.")
        else:
            await storage.delete(dataset_info["s3_key"]) # Use the s3_key from DB
        
        await db.delete_dataset(dataset_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting dataset: {str(e)}"
        )
