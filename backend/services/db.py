from supabase import create_client, Client
from typing import Optional, Dict, Any, List
from datetime import datetime
import os
from dotenv import load_dotenv

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
        
        Args:
            dataset_id: Unique identifier for the dataset
            meta: Dataset metadata (containing rows, columns, dtypes, summary)
            description: Optional dataset description
            s3_key: S3 key for the dataset file
            filename: Original filename of the dataset
            created_at: Creation timestamp
            updated_at: Last update timestamp (same as created_at on insert)
        """
        data = {
            "id": dataset_id,
            "rows": meta.get("rows"),
            "columns": meta.get("columns"),
            "dtypes": meta.get("dtypes"),
            "summary": meta.get("summary"),
            "description": description,
            "s3_key": s3_key,
            "filename": filename,
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat()
        }
        
        result = self.supabase.table("datasets").insert(data).execute()
        if hasattr(result, 'error') and result.error:
            raise Exception(f"Error inserting dataset: {result.error}")

    async def get_meta(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific dataset.
        
        Args:
            dataset_id: Unique identifier for the dataset
            
        Returns:
            Dataset metadata if found, None otherwise
        """
        result = self.supabase.table("datasets").select("*").eq("id", dataset_id).execute()
        
        if hasattr(result, 'error') and result.error:
            raise Exception(f"Error retrieving dataset: {result.error}")
            
        if not result.data:
            return None
            
        return result.data[0]

    async def list_datasets(
        self, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List all datasets with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of dataset records
        """
        result = self.supabase.table("datasets")\
            .select("*")\
            .order("created_at", desc=True)\
            .range(skip, skip + limit - 1)\
            .execute()
            
        if hasattr(result, 'error') and result.error:
            raise Exception(f"Error listing datasets: {result.error}")
            
        return result.data

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
        meta: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update a dataset record.
        
        Args:
            dataset_id: Unique identifier for the dataset
            description: New description (optional)
            meta: New metadata (optional)
        """
        update_data = {
            "updated_at": datetime.now(datetime.UTC).isoformat()
        }
        
        if description is not None:
            update_data["description"] = description
            
        if meta is not None:
            # Ensure all expected meta fields are updated if meta is provided
            if "rows" in meta: update_data["rows"] = meta["rows"]
            if "columns" in meta: update_data["columns"] = meta["columns"]
            if "dtypes" in meta: update_data["dtypes"] = meta["dtypes"]
            if "summary" in meta: update_data["summary"] = meta["summary"]
            
        result = self.supabase.table("datasets")\
            .update(update_data)\
            .eq("id", dataset_id)\
            .execute()
            
        if hasattr(result, 'error') and result.error:
            raise Exception(f"Error updating dataset: {result.error}")

# Create a singleton instance
db = Database() 