from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class DatasetDB(BaseModel):
    """
    Represents a record in the 'datasets' table in Supabase.
    """
    id: str = Field(..., description="Unique identifier of the dataset (UUID hex)")
    rows: Optional[int] = Field(None, description="Number of rows in the dataset")
    columns: Optional[List[str]] = Field(None, description="List of column names")
    dtypes: Optional[Dict[str, str]] = Field(None, description="Data types of each column")
    summary: Optional[Dict[str, Any]] = Field(None, description="Statistical summary of data (JSONB in DB)")
    description: Optional[str] = Field(None, description="User-provided description of the dataset")
    s3_key: str = Field(..., description="S3 key where the raw dataset file is stored")
    filename: str = Field(..., description="Original filename of the uploaded dataset")
    created_at: datetime = Field(..., description="Timestamp of when the dataset record was created")
    updated_at: datetime = Field(..., description="Timestamp of when the dataset record was last updated")

    class Config:
        from_attributes = True # Useful if fetching data and parsing into this model directly
        # Pydantic v1: orm_mode = True
