from supabase import create_client, Client
from typing import Optional, Dict, Any, List
from datetime import datetime
import os
from dotenv import load_dotenv
from .schema import DatasetDB

load_dotenv()

class Database:
    def __init__(self):
        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Missing Supabase credentials")
        self.supabase: Client = create_client(url, key)
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensure required tables exist in the database."""
        # This would typically be handled by migrations, but for simplicity:
        self.supabase.table("datasets").select("*").limit(1).execute()

    async def insert_dataset(
        self, 
        dataset_id: str, 
        meta: Dict[str, Any], 
        description: Optional[str],
        s3_key: str,
        filename: str,
        created_at: datetime,
        updated_at: datetime
    ) -> None:
        """
        Insert a new dataset record.
        The 'meta' dict should contain 'rows', 'columns', 'dtypes', 'summary'.
        """
        # Prepare data for Supabase, ensuring it matches DatasetDB fields implicitly
        data_to_insert = {
            "id": dataset_id,
            "rows": meta.get("rows"),
            "columns": meta.get("columns"),
            "dtypes": meta.get("dtypes"),
            "summary": meta.get("summary"), # Ensure this is JSON serializable
            "description": description,
            "s3_key": s3_key,
            "filename": filename,
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat()
        }
        
        result = self.supabase.table("datasets").insert(data_to_insert).execute()
        if hasattr(result, 'error') and result.error:
            raise Exception(f"Error inserting dataset: {result.error}")

    async def get_meta(self, dataset_id: str) -> Optional[DatasetDB]:
        """
        Get metadata for a specific dataset.
        
        Args:
            dataset_id: Unique identifier for the dataset
            
        Returns:
            DatasetDB model instance if found, None otherwise
        """
        result = self.supabase.table("datasets").select("*").eq("id", dataset_id).limit(1).execute() # Use limit(1) for single record
        
        if hasattr(result, 'error') and result.error:
            raise Exception(f"Error retrieving dataset: {result.error}")
            
        if not result.data:
            return None
            
        # Parse the dictionary from Supabase into our Pydantic model
        try:
            return DatasetDB(**result.data[0])
        except Exception as e: # Handle potential Pydantic validation errors
            # Log this error, as it indicates a mismatch between DB data and schema.py
            # For now, re-raise or return None, depending on desired strictness.
            print(f"Error parsing data from DB into DatasetDB model: {e}") # Basic logging
            raise Exception(f"Data mismatch for dataset {dataset_id}: {e}")

    async def list_datasets(
        self, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[DatasetDB]:
        """
        List all datasets with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of DatasetDB model instances
        """
        result = self.supabase.table("datasets")\
            .select("*")\
            .order("created_at", desc=True)\
            .range(skip, skip + limit - 1)\
            .execute()
            
        if hasattr(result, 'error') and result.error:
            raise Exception(f"Error listing datasets: {result.error}")
        
        datasets = []
        for item_data in result.data:
            try:
                datasets.append(DatasetDB(**item_data))
            except Exception as e: # Handle potential Pydantic validation errors per item
                # Log this error. You might choose to skip this item or raise an error.
                print(f"Error parsing item data from DB into DatasetDB model: {e}") # Basic logging
                # Continue to next item for now, or raise
        return datasets

    async def delete_dataset(self, dataset_id: str) -> None:
        """
        Delete a dataset record.
        
        Args:
            dataset_id: Unique identifier for the dataset
        """
        result = self.supabase.table("datasets")\
            .delete()\
            .eq("id", dataset_id)\
            .execute()
            
        if hasattr(result, 'error') and result.error:
            raise Exception(f"Error deleting dataset: {result.error}")

    async def update_dataset(
        self,
        dataset_id: str,
        description: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None # 'meta' here is a partial dict for updates
    ) -> None:
        """
        Update a dataset record.
        
        Args:
            dataset_id: Unique identifier for the dataset
            description: New description (optional)
            meta: Partial dictionary with metadata fields to update (e.g., rows, columns)
        """
        update_data = {
            "updated_at": datetime.now(datetime.UTC).isoformat()
        }
        
        if description is not None:
            update_data["description"] = description
            
        if meta is not None:
            # Update specific fields from the meta dictionary if they are provided
            if "rows" in meta: update_data["rows"] = meta["rows"]
            if "columns" in meta: update_data["columns"] = meta["columns"]
            if "dtypes" in meta: update_data["dtypes"] = meta["dtypes"]
            if "summary" in meta: update_data["summary"] = meta["summary"] # Ensure summary is JSON serializable
            
        result = self.supabase.table("datasets")\
            .update(update_data)\
            .eq("id", dataset_id)\
            .execute()
            
        if hasattr(result, 'error') and result.error:
            raise Exception(f"Error updating dataset: {result.error}")

# Create a singleton instance
db = Database() 