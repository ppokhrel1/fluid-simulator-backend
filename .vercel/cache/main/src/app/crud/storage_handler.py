import uuid6 as uuid
from typing import Dict, Any
from supabase import create_client, Client 

class StorageCRUD:
    """
    CRUD operations for Supabase Storage buckets using the official 'supabase' Python client.
    """
    def __init__(self, supabase_url: str, supabase_key: str, bucket_name: str):
        """
        Initializes the Supabase client.
        """
        # Ensure URL has protocol
        if not supabase_url.startswith(("http://", "https://")):
            supabase_url = "https://" + supabase_url
            
        self.bucket_name = bucket_name
        if not supabase_key:
            raise ValueError("Supabase key cannot be empty or None.")
        
        # Initialize the main Supabase client
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        # Access the storage client via the main client object
        # self.storage will be the object that exposes the 'from_' method
        self.storage = self.supabase.storage 

    def _get_file_path(self, file_name: str, model_id: uuid.UUID) -> str:
        """Helper to generate the file path: model_id/file_name."""
        return f"{model_id}/{file_name}"

    async def upload_file(self, file_content: bytes, file_name: str, model_id: uuid.UUID) -> bool:
        """
        Uploads a file (bytes) to the specified bucket.
        """
        file_path = self._get_file_path(file_name, model_id)
        print(file_path, file_content[:20], self.bucket_name)
        
        new_limit_bytes = 4194304 * 5
        try:
            response = self.storage.from_(self.bucket_name).upload(
                path=file_path, # 1. The destination path
                file=file_content, # 2. The file content (bytes)
                file_options={
                    "cache-control": "3600", 
                    "upsert": "true",
                }
            )
            
            print("Upload response:", response)
            # Successful upload returns a dict with 'Key' or similar confirmation
            if response.path:
                return True

            return False
            
        except Exception as e:
            print(f"Error uploading file to Supabase Storage: {e}")
            return False

    async def download_file(self, file_path: str) -> bytes:
        """Downloads a file from the bucket and returns its content as bytes."""
        try:
            # FIX: Use self.storage.from_
            file_content = self.storage.from_(self.bucket_name).download(file_path)
            return file_content
        except Exception as e:
            print(f"Error downloading file from Supabase Storage at {file_path}: {e}")
            raise FileNotFoundError(f"File not found or access denied: {file_path}")

    async def delete_file(self, file_path: str) -> bool:
        """Deletes a file from the bucket."""
        try:
            # FIX: Use self.storage.from_
            response = self.storage.from_(self.bucket_name).remove([file_path])
            
            if isinstance(response, list) and len(response) > 0 and 'name' in response[0]:
                return True
            
            if response.get('error'):
                 print(f"Supabase Delete Error: {response['error']}")
                 return False
                 
            return False

        except Exception as e:
            print(f"Error deleting file from Supabase Storage: {e}")
            return False