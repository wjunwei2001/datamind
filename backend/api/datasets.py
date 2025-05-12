from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from typing import Annotated, Optional
from uuid import uuid4
from pydantic import BaseModel, Field
from datetime import datetime
from services import db, storage
from services.agents import analyze_data

router = APIRouter(prefix="/datasets", tags=["datasets"])

class DatasetMeta(BaseModel):
    rows: int = Field(..., description="Number of rows in the dataset")
    columns: list[str] = Field(..., description="List of column names")
    dtypes: dict[str, str] = Field(..., description="Data types of each column")
    summary: dict[str, dict[str, float]] = Field(..., description="Statistical summary of numeric columns")

class DatasetOut(BaseModel):
    id: str = Field(..., description="Unique identifier of the dataset")
    rows: int = Field(..., description="Number of rows in the dataset")
    columns: list[str] = Field(..., description="List of column names")
    dtypes: dict[str, str] = Field(..., description="Data types of each column")
    summary: dict[str, dict[str, float]] = Field(..., description="Statistical summary of numeric columns")
    description: Optional[str] = Field(None, description="Optional description of the dataset")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of dataset creation")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of last update")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "rows": 1000,
                "columns": ["id", "name", "value"],
                "dtypes": {"id": "int64", "name": "object", "value": "float64"},
                "summary": {"value": {"mean": 42.5, "std": 10.2}},
                "description": "Sample dataset for testing",
                "created_at": "2024-02-20T12:00:00Z",
                "updated_at": "2024-02-20T12:00:00Z"
            }
        }

@router.post("", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    file: Annotated[UploadFile, File(description="The CSV file to upload")],
    description: Annotated[Optional[str], Form(description="Optional description of the dataset")] = None,
):
    """
    Upload and analyze a new dataset.
    
    Args:
        file: The CSV file to upload
        description: Optional description of the dataset
        
    Returns:
        Dataset metadata and ID
        
    Raises:
        HTTPException: If there's an error processing the dataset
    """
    try:
        uid = uuid4().hex
        key = await storage.save(file, uid)
        await file.close()

        meta = await run_in_threadpool(analyze_data, key)
        now = datetime.now(datetime.UTC)
        await run_in_threadpool(db.insert_dataset, uid, meta, description, now)
        
        return {**meta, "id": uid, "description": description,
                "created_at": now, "updated_at": now}
    except Exception as e:
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
        return meta
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
        return await db.list_datasets(skip=skip, limit=limit)
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
        # Delete from storage
        await storage.delete(f"datasets/{dataset_id}")
        # Delete from database
        await db.delete_dataset(dataset_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting dataset: {str(e)}"
        )
