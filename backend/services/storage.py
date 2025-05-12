import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile
import os
from dotenv import load_dotenv
from typing import Optional
import logging

load_dotenv()

class S3Client:
    def __init__(self):
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'ap-southeast-1')
        )
        self.bucket = os.getenv('AWS_BUCKET_NAME')
        if not self.bucket:
            raise ValueError("AWS_BUCKET_NAME environment variable is required")

    async def save(self, file: UploadFile, dataset_id: str) -> str:
        """
        Save a file to S3.
        
        Args:
            file: The file to upload
            dataset_id: Unique identifier for the dataset
            
        Returns:
            The S3 key of the uploaded file
        """
        try:
            key = f"datasets/{dataset_id}/{file.filename}"
            content = await file.read()
            
            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType=file.content_type
            )
            
            return key
        except ClientError as e:
            logging.error(f"Error uploading file to S3: {e}")
            raise Exception(f"Failed to upload file: {str(e)}")

    async def get(self, key: str) -> Optional[bytes]:
        """
        Get a file from S3.
        
        Args:
            key: The S3 key of the file
            
        Returns:
            The file contents if found, None otherwise
        """
        try:
            response = self.s3.get_object(
                Bucket=self.bucket,
                Key=key
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            logging.error(f"Error retrieving file from S3: {e}")
            raise Exception(f"Failed to retrieve file: {str(e)}")

    async def delete(self, key: str) -> None:
        """
        Delete a file from S3.
        
        Args:
            key: The S3 key of the file to delete
        """
        try:
            self.s3.delete_object(
                Bucket=self.bucket,
                Key=key
            )
        except ClientError as e:
            logging.error(f"Error deleting file from S3: {e}")
            raise Exception(f"Failed to delete file: {str(e)}")

    async def list_files(self, prefix: str = "datasets/") -> list[str]:
        """
        List files in S3 with a given prefix.
        
        Args:
            prefix: The prefix to filter files by
            
        Returns:
            List of file keys
        """
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            return [obj['Key'] for obj in response.get('Contents', [])]
        except ClientError as e:
            logging.error(f"Error listing files in S3: {e}")
            raise Exception(f"Failed to list files: {str(e)}")

    def get_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for temporary access to a file.
        
        Args:
            key: The S3 key of the file
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL for the file
        """
        try:
            return self.s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': key
                },
                ExpiresIn=expiration
            )
        except ClientError as e:
            logging.error(f"Error generating presigned URL: {e}")
            raise Exception(f"Failed to generate presigned URL: {str(e)}")

# Create a singleton instance
storage = S3Client() 