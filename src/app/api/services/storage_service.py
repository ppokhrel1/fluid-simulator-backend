"""Storage service for handling file storage operations with Supabase."""

import os
import uuid
from typing import Optional, Dict, Any, List, BinaryIO
from datetime import datetime, timedelta
from pathlib import Path
import aiofiles
from fastapi import HTTPException, status, UploadFile
import asyncio

from supabase import create_client, Client
from src.app.core.config import AppSettings
from src.app.core.logger import *

settings = AppSettings()


class StorageService:
    """Service for handling file storage operations with Supabase."""
    
    def __init__(self):
        self.settings = AppSettings()
        self.supabase: Client = create_client(
            self.settings.SUPABASE_URL,
            self.settings.SUPABASE_KEY
        )
        self.bucket_name = self.settings.SUPABASE_BUCKET_NAME
    
    async def initialize_bucket(self):
        """Initialize the storage bucket if it doesn't exist."""
        try:
            # Check if bucket exists
            buckets = self.supabase.storage.list_buckets()
            bucket_names = [bucket.name for bucket in buckets]
            
            if self.bucket_name not in bucket_names:
                # Create bucket with public access for downloads
                self.supabase.storage.create_bucket(
                    self.bucket_name,
                    {
                        "public": True,
                        "file_size_limit": 500 * 1024 * 1024,  # 500MB
                        "allowed_mime_types": [
                            "model/stl", "application/sla", "text/plain",
                            "application/octet-stream", "model/gltf-binary",
                            "model/gltf+json", "application/json",
                            "image/jpeg", "image/png", "image/gif", "image/webp",
                            "application/zip", "application/x-rar-compressed",
                            "application/x-7z-compressed"
                        ]
                    }
                )
                logger.info(f"Created storage bucket: {self.bucket_name}")
            else:
                logger.info(f"Storage bucket already exists: {self.bucket_name}")
                
        except Exception as e:
            logger.error(f"Bucket initialization failed: {str(e)}")
            raise
    
    async def upload_file(
        self, 
        file: UploadFile, 
        destination_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to Supabase storage.
        
        Args:
            file: UploadFile instance
            destination_path: Path in storage bucket
            metadata: Additional file metadata
            
        Returns:
            Upload result with file info
        """
        try:
            # Read file content
            content = await file.read()
            
            # Upload to Supabase
            result = self.supabase.storage.from_(self.bucket_name).upload(
                destination_path,
                content,
                {
                    "contentType": file.content_type,
                    "metadata": metadata or {}
                }
            )
            
            # Get public URL
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(destination_path)
            
            logger.info(f"File uploaded successfully: {destination_path}")
            
            return {
                "success": True,
                "file_path": destination_path,
                "public_url": public_url,
                "file_size": len(content),
                "content_type": file.content_type,
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File upload failed: {str(e)}"
            )
    
    async def download_file(self, file_path: str) -> bytes:
        """
        Download a file from Supabase storage.
        
        Args:
            file_path: Path to file in storage
            
        Returns:
            File content as bytes
        """
        try:
            result = self.supabase.storage.from_(self.bucket_name).download(file_path)
            return result
            
        except Exception as e:
            logger.error(f"File download failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_path}"
            )
    
    async def create_signed_download_url(
        self, 
        file_path: str, 
        expires_in: int = 3600
    ) -> str:
        """
        Create a signed URL for secure file downloads.
        
        Args:
            file_path: Path to file in storage
            expires_in: URL expiration time in seconds
            
        Returns:
            Signed download URL
        """
        try:
            # Supabase doesn't have signed URLs for public buckets
            # For private buckets, you would use:
            # result = self.supabase.storage.from_(self.bucket_name).create_signed_url(file_path, expires_in)
            
            # For public buckets, return public URL
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)
            
            # In production with private buckets, you'd return the signed URL
            # For now, we'll return the public URL
            logger.info(f"Created download URL for: {file_path}")
            
            return public_url
            
        except Exception as e:
            logger.error(f"Signed URL creation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Download URL creation failed: {str(e)}"
            )
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_path: Path to file in storage
            
        Returns:
            Success status
        """
        try:
            result = self.supabase.storage.from_(self.bucket_name).remove([file_path])
            logger.info(f"File deleted: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"File deletion failed: {str(e)}")
            return False
    
    async def list_files(self, prefix: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """
        List files in storage with optional prefix.
        
        Args:
            prefix: Path prefix to filter files
            limit: Maximum number of files to return
            
        Returns:
            List of file information dictionaries
        """
        try:
            # Supabase storage list operation
            result = self.supabase.storage.from_(self.bucket_name).list(prefix)
            
            files = []
            for item in result[:limit]:
                files.append({
                    "name": item.name,
                    "path": item.name,
                    "size": getattr(item, 'metadata', {}).get('size', 0),
                    "content_type": getattr(item, 'metadata', {}).get('mimetype', ''),
                    "last_modified": getattr(item, 'metadata', {}).get('lastModified', ''),
                })
            
            return files
            
        except Exception as e:
            logger.error(f"File listing failed: {str(e)}")
            return []
    
    async def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get information about a specific file.
        
        Args:
            file_path: Path to file in storage
            
        Returns:
            File information dictionary
        """
        try:
            # In Supabase, we need to list and filter
            files = await self.list_files(file_path)
            
            for file_info in files:
                if file_info['path'] == file_path:
                    return file_info
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_path}"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"File info retrieval failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File info retrieval failed: {str(e)}"
            )
    
    async def move_file(self, source_path: str, destination_path: str) -> bool:
        """
        Move a file within storage.
        
        Args:
            source_path: Current file path
            destination_path: New file path
            
        Returns:
            Success status
        """
        try:
            # Download and re-upload to new location
            content = await self.download_file(source_path)
            
            # Upload to new location
            result = self.supabase.storage.from_(self.bucket_name).upload(
                destination_path,
                content
            )
            
            # Delete original
            await self.delete_file(source_path)
            
            logger.info(f"File moved: {source_path} -> {destination_path}")
            return True
            
        except Exception as e:
            logger.error(f"File move failed: {str(e)}")
            return False
    
    async def copy_file(self, source_path: str, destination_path: str) -> bool:
        """
        Copy a file within storage.
        
        Args:
            source_path: Source file path
            destination_path: Destination file path
            
        Returns:
            Success status
        """
        try:
            # Download and upload to new location
            content = await self.download_file(source_path)
            
            result = self.supabase.storage.from_(self.bucket_name).upload(
                destination_path,
                content
            )
            
            logger.info(f"File copied: {source_path} -> {destination_path}")
            return True
            
        except Exception as e:
            logger.error(f"File copy failed: {str(e)}")
            return False
    
    async def create_directory(self, directory_path: str) -> bool:
        """
        Create a directory in storage (Supabase doesn't have real directories).
        
        Args:
            directory_path: Directory path to create
            
        Returns:
            Success status
        """
        try:
            # In Supabase, directories are virtual - just ensure path format
            # We can create a placeholder file to establish the directory structure
            placeholder_path = f"{directory_path.rstrip('/')}/.placeholder"
            
            result = self.supabase.storage.from_(self.bucket_name).upload(
                placeholder_path,
                b"directory_placeholder"
            )
            
            logger.info(f"Directory created: {directory_path}")
            return True
            
        except Exception as e:
            logger.error(f"Directory creation failed: {str(e)}")
            return False
    
    async def get_storage_usage(self) -> Dict[str, Any]:
        """
        Get storage usage statistics.
        
        Returns:
            Storage usage information
        """
        try:
            # Supabase doesn't provide direct storage usage via API
            # You would need to calculate this from file listings
            files = await self.list_files(limit=1000)  # Adjust limit as needed
            
            total_size = sum(file['size'] for file in files)
            file_count = len(files)
            
            return {
                "total_files": file_count,
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "bucket_name": self.bucket_name
            }
            
        except Exception as e:
            logger.error(f"Storage usage calculation failed: {str(e)}")
            return {
                "total_files": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "bucket_name": self.bucket_name
            }
    
    async def cleanup_old_files(self, older_than_days: int = 30) -> int:
        """
        Clean up files older than specified days.
        
        Args:
            older_than_days: Delete files older than this many days
            
        Returns:
            Number of files deleted
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=older_than_days)
            files = await self.list_files(limit=1000)
            
            deleted_count = 0
            for file_info in files:
                # Parse last modified time (format depends on Supabase response)
                last_modified_str = file_info.get('last_modified', '')
                if last_modified_str:
                    try:
                        last_modified = datetime.fromisoformat(last_modified_str.replace('Z', '+00:00'))
                        if last_modified < cutoff_time:
                            await self.delete_file(file_info['path'])
                            deleted_count += 1
                    except ValueError:
                        continue
            
            logger.info(f"Cleaned up {deleted_count} old files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"File cleanup failed: {str(e)}")
            return 0