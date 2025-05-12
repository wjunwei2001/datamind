from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from datasets import dataset_manager
from services.agents import analyze_data
from typing import Dict, Any
import uuid

router = APIRouter()

@router.post("/chat")
async def chat_with_data_analyst(
    csv: UploadFile = File(...),
    query: str = Form(...)
) -> Dict[str, Any]:
    """
    Analyze CSV data and answer questions about it.
    
    Args:
        csv: The CSV file to analyze
        query: The question to ask about the data
        
    Returns:
        Dict containing the analysis results
    """
    try:
        # Read CSV content
        content = (await csv.read()).decode("utf-8")
        
        # Generate a unique dataset ID
        dataset_id = str(uuid.uuid4())
        
        # Load the dataset
        load_result = dataset_manager.load_csv(content, dataset_id)
        if load_result["status"] == "error":
            raise HTTPException(
                status_code=400,
                detail=f"Error loading dataset: {load_result['error']}"
            )
        
        try:
            # Get dataset info for context
            dataset_info = dataset_manager.get_dataset_info(dataset_id)
            
            # Analyze the data
            result = analyze_data(content, query, dataset_info)
            
            return result
        finally:
            # Clean up the dataset
            dataset_manager.remove_dataset(dataset_id)
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing data: {str(e)}"
        )
