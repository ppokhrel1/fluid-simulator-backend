# app/services/supabase_storage.py
import os
from src.app.core.config import AppSettings
from supabase import create_client, Client
import uuid
import tempfile
import asyncio
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class SupabaseStorage:
    def __init__(self):
        supabase_url = "https://" + AppSettings().SUPABASE_URL
        supabase_key = AppSettings().SUPABASE_KEY
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        
        self.client: Client = create_client(supabase_url, supabase_key)
        self.bucket_name = "3d-models"
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the storage bucket exists"""
        try:
            # Try to get bucket info - if it fails, create the bucket
            self.client.storage.get_bucket(self.bucket_name)
        except Exception:
            # Create the bucket if it doesn't exist
            self.client.storage.create_bucket(
                self.bucket_name,
                options={"public": True}  # Make files publicly accessible
            )
    
    async def store_mesh(self, mesh, mesh_id: str, format: str = "stl") -> str:
        """Store mesh in Supabase storage and return public URL"""
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Export mesh to file
            mesh.export(temp_path, file_type=format)
            
            # Read the file content
            with open(temp_path, 'rb') as file:
                file_content = file.read()
            
            filename = f"{mesh_id}.{format}"
            
            # Upload to Supabase storage
            response = self.client.storage.from_(self.bucket_name).upload(
                file_path=filename,
                file=file_content,
                file_options={"content-type": f"application/{format}"}
            )
            
            # Clean up temporary file
            import os
            os.unlink(temp_path)
            
            if response.get('error'):
                raise Exception(f"Supabase upload error: {response['error']}")
            
            # Get public URL
            public_url = self.client.storage.from_(self.bucket_name).get_public_url(filename)
            
            # Store metadata in database table (optional)
            try:
                self.client.table("mesh_exports").insert({
                    "mesh_id": mesh_id,
                    "file_name": filename,
                    "format": format,
                    "url": public_url,
                    "created_at": "now()"
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to store metadata: {str(e)}")
            
            return public_url
            
        except Exception as e:
            logger.error(f"Supabase storage failed: {str(e)}")
            raise Exception(f"Storage failed: {str(e)}")