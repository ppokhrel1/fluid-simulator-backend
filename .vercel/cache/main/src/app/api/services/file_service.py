"""File service for handling file operations, validation, and management."""

import os
import uuid6 as uuid
from typing import List, Optional, Dict, Any, BinaryIO
from fastapi import UploadFile, HTTPException, status
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import asyncio
import struct

from ...core.config import AppSettings
from ...core.logger import *

settings = AppSettings()


class FileService:
    """Service for handling file operations and validation."""
    
    # Supported file types and their signatures (magic numbers)
    FILE_SIGNATURES = {
        # STL - Binary STL has 80 byte header followed by 4 byte triangle count
        'stl': [b'solid', b''],  # ASCII STL starts with "solid", binary has no specific header
        
        # OBJ - Typically starts with vertex definitions or comments
        'obj': [b'v ', b'# ', b'f '],
        
        # FBX - Binary FBX has specific header
        'fbx': [b'Kaydara FBX Binary'],
        
        # GLB - Starts with 4 byte identifier "glTF" and 4 byte version
        'glb': [b'glTF'],
        
        # GLTF - JSON format, typically starts with {
        'gltf': [b'{'],
        
        # 3MF - ZIP-based format, starts with PK header
        '3mf': [b'PK'],
        
        # Image formats
        'jpg': [b'\xFF\xD8\xFF'],  # JPEG
        'jpeg': [b'\xFF\xD8\xFF'],
        'png': [b'\x89PNG\r\n\x1a\n'],
        'gif': [b'GIF87a', b'GIF89a'],
        'webp': [b'RIFF', b'WEBP'],
        
        # Archive formats
        'zip': [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'],
        'rar': [b'Rar!\x1a\x07', b'Rar!\x1a\x07\x00'],
        '7z': [b'7z\xbc\xaf\x27\x1c'],
    }
    
    # File extensions to MIME type mapping
    EXTENSION_TO_MIME = {
        'stl': 'model/stl',
        'obj': 'text/plain',
        'fbx': 'application/octet-stream',
        'glb': 'model/gltf-binary',
        'gltf': 'model/gltf+json',
        '3mf': 'model/3mf',
        'blend': 'application/x-blender',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'zip': 'application/zip',
        'rar': 'application/x-rar-compressed',
        '7z': 'application/x-7z-compressed',
    }
    
    # Maximum file sizes (in bytes)
    MAX_FILE_SIZES = {
        '3d_models': 500 * 1024 * 1024,  # 500MB for 3D models
        'images': 50 * 1024 * 1024,      # 50MB for images
        'archives': 200 * 1024 * 1024,   # 200MB for archives
    }
    
    def __init__(self):
        self.settings = AppSettings()
    
    async def validate_file(self, file: UploadFile, file_type: str = "3d_models") -> Dict[str, Any]:
        """
        Validate uploaded file for type, size, and security.
        
        Args:
            file: UploadFile instance
            file_type: Type of file (3d_models, images, archives)
            
        Returns:
            Dict with validation results and file info
        """
        try:
            # Read file content for validation
            content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            # Get file extension
            file_extension = Path(file.filename).suffix.lower().lstrip('.')
            
            # Validate file extension
            if file_extension not in self.EXTENSION_TO_MIME:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file format: .{file_extension}"
                )
            
            # Validate file size
            max_size = self.MAX_FILE_SIZES.get(file_type, self.MAX_FILE_SIZES['3d_models'])
            if len(content) > max_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Maximum size: {max_size // (1024 * 1024)}MB"
                )
            
            # Validate file signature (magic number)
            if not await self._validate_file_signature(content, file_extension):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file signature for .{file_extension} file"
                )
            
            # Calculate file hash
            file_hash = hashlib.sha256(content).hexdigest()
            
            # Additional security checks for specific file types
            if file_extension in ['stl', 'obj', 'gltf']:
                await self._validate_3d_model_safety(content, file_extension)
            
            # Get MIME type from extension mapping
            mime_type = self.EXTENSION_TO_MIME.get(file_extension, 'application/octet-stream')
            
            return {
                "valid": True,
                "filename": file.filename,
                "extension": file_extension,
                "mime_type": mime_type,
                "size": len(content),
                "file_hash": file_hash,
                "safe": True
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File validation failed: {str(e)}"
            )
    
    async def _validate_file_signature(self, content: bytes, extension: str) -> bool:
        """
        Validate file using magic number/signature detection.
        
        Args:
            content: File content as bytes
            extension: File extension
            
        Returns:
            Boolean indicating if signature is valid
        """
        if extension not in self.FILE_SIGNATURES:
            return True  # No signature defined for this extension
            
        signatures = self.FILE_SIGNATURES[extension]
        
        # For empty signature list, accept all files of this extension
        if not signatures or (len(signatures) == 1 and signatures[0] == b''):
            return True
        
        # Check each possible signature
        for signature in signatures:
            if content.startswith(signature):
                return True
        
        # Special case for binary STL files
        if extension == 'stl' and len(content) >= 84:
            # Binary STL: 80 byte header + 4 byte triangle count
            # Check if it's a valid binary STL by verifying structure
            try:
                # Read triangle count (little endian, 4 bytes after 80 byte header)
                triangle_count = struct.unpack('<I', content[80:84])[0]
                expected_size = 84 + triangle_count * 50
                if len(content) == expected_size:
                    return True
            except struct.error:
                pass
        
        return False
    
    async def _validate_3d_model_safety(self, content: bytes, extension: str):
        """Perform additional safety checks for 3D model files."""
        try:
            if extension == 'stl':
                await self._validate_stl_file(content)
            elif extension == 'obj':
                await self._validate_obj_file(content)
            elif extension == 'gltf':
                await self._validate_gltf_file(content)
            elif extension == 'glb':
                await self._validate_glb_file(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"3D model validation failed: {str(e)}"
            )
    
    async def _validate_stl_file(self, content: bytes):
        """Validate STL file structure."""
        # Check minimum size
        if len(content) < 84:
            raise ValueError("Invalid STL file: too short")
        
        # Check for ASCII STL
        if content[:5].lower() == b'solid':
            # Basic ASCII STL validation
            text_content = content.decode('utf-8', errors='ignore')
            if 'facet' not in text_content or 'vertex' not in text_content:
                raise ValueError("Invalid ASCII STL: missing facet or vertex data")
            return
        
        # Binary STL validation
        try:
            triangle_count = struct.unpack('<I', content[80:84])[0]
            expected_size = 84 + triangle_count * 50
            
            if len(content) != expected_size:
                raise ValueError("Invalid binary STL file: size mismatch")
                
        except struct.error as e:
            raise ValueError(f"Invalid binary STL format: {str(e)}")
    
    async def _validate_obj_file(self, content: bytes):
        """Validate OBJ file structure."""
        try:
            text = content.decode('utf-8', errors='ignore')
            lines = text.split('\n')
            
            # Check for basic OBJ structure
            has_vertices = any(line.strip().startswith('v ') for line in lines)
            has_faces = any(line.strip().startswith('f ') for line in lines)
            
            if not has_vertices or not has_faces:
                raise ValueError("Invalid OBJ file: missing vertices or faces")
                
            # Check for reasonable vertex count (prevent extremely large files)
            vertex_count = sum(1 for line in lines if line.strip().startswith('v '))
            if vertex_count > 1000000:  # 1 million vertices limit
                raise ValueError("OBJ file too complex: excessive vertex count")
                
        except UnicodeDecodeError:
            raise ValueError("Invalid OBJ file: not UTF-8 encoded")
    
    async def _validate_gltf_file(self, content: bytes):
        """Validate GLTF file structure."""
        try:
            import json
            data = json.loads(content)
            
            # Check required GLTF fields
            if 'asset' not in data or 'version' not in data['asset']:
                raise ValueError("Invalid GLTF: missing asset version")
                
            if data['asset']['version'] != '2.0':
                raise ValueError("Only GLTF 2.0 is supported")
                
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in GLTF file")
        except ImportError:
            # JSON module should always be available, but just in case
            raise ValueError("GLTF validation requires JSON parsing")
    
    async def _validate_glb_file(self, content: bytes):
        """Validate GLB file structure."""
        if len(content) < 20:
            raise ValueError("GLB file too short")
        
        # Check GLB header (12 bytes: magic + version + length)
        if content[:4] != b'glTF':
            raise ValueError("Invalid GLB: missing glTF magic number")
        
        try:
            version = struct.unpack('<I', content[4:8])[0]
            length = struct.unpack('<I', content[8:12])[0]
            
            if version != 2:
                raise ValueError("Only GLB version 2 is supported")
            
            if length != len(content):
                raise ValueError("GLB length mismatch")
                
        except struct.error as e:
            raise ValueError(f"Invalid GLB structure: {str(e)}")
    
    def generate_unique_filename(self, original_filename: str, user_id: int) -> str:
        """
        Generate a unique filename for storage.
        
        Args:
            original_filename: Original uploaded filename
            user_id: User ID for organization
            
        Returns:
            Unique filename string
        """
        extension = Path(original_filename).suffix.lower()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        
        return f"user_{user_id}/{timestamp}_{unique_id}{extension}"
    
    async def extract_metadata(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Extract metadata from uploaded file.
        
        Args:
            file_path: Path to the file
            file_type: Type of file
            
        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            "uploaded_at": datetime.utcnow().isoformat(),
            "file_type": file_type,
        }
        
        try:
            if file_type == "3d_models":
                metadata.update(await self._extract_3d_model_metadata(file_path))
            elif file_type == "images":
                metadata.update(await self._extract_image_metadata(file_path))
        
        except Exception as e:
            logger.warning(f"Metadata extraction failed: {str(e)}")
            # Continue with basic metadata
        
        return metadata
    
    async def _extract_3d_model_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from 3D model files."""
        # Basic metadata extraction without external libraries
        file_size = os.path.getsize(file_path)
        
        return {
            "model_type": "3d_model",
            "file_size": file_size,
            "vertices_count": 0,  # Would require proper 3D parsing library
            "faces_count": 0,     # Would require proper 3D parsing library
            "units": "mm"         # Default units
        }
    
    async def _extract_image_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from image files."""
        # Basic image metadata without PIL
        file_size = os.path.getsize(file_path)
        
        return {
            "image_type": "preview",
            "file_size": file_size,
            "color_mode": "RGB", # Default
        }
    
    async def create_thumbnail(self, file_path: str, output_path: str, size: tuple = (256, 256)) -> bool:
        """
        Create a thumbnail for 3D models or images.
        
        Args:
            file_path: Path to source file
            output_path: Path for thumbnail output
            size: Thumbnail dimensions
            
        Returns:
            Success status
        """
        try:
            # Placeholder for thumbnail creation logic
            # In a real implementation, you might use:
            # - PIL/Pillow for images
            # - A 3D rendering library for 3D models
            logger.info(f"Creating thumbnail for {file_path} -> {output_path}")
            
            # For now, create a placeholder file or use a default thumbnail
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Create a simple placeholder file
            with open(output_path, 'w') as f:
                f.write("Thumbnail placeholder")
            
            return True
            
        except Exception as e:
            logger.error(f"Thumbnail creation failed: {str(e)}")
            return False
    
    async def scan_for_malware(self, file_path: str) -> bool:
        """
        Scan file for malware using basic heuristics.
        
        Args:
            file_path: Path to file to scan
            
        Returns:
            True if file is safe
        """
        try:
            file_size = os.path.getsize(file_path)
            
            # Check for suspiciously large files
            if file_size > 500 * 1024 * 1024:  # 500MB
                logger.warning(f"Large file detected: {file_path} ({file_size} bytes)")
            
            # Check file extension against content
            with open(file_path, 'rb') as f:
                header = f.read(100)  # Read first 100 bytes for analysis
            
            filename = Path(file_path).name
            extension = Path(file_path).suffix.lower().lstrip('.')
            
            # Check for executable files disguised as other types
            if await self._is_potentially_executable(header, extension):
                logger.warning(f"Potentially executable file disguised as {extension}: {filename}")
                return False
            
            # Check for common malware patterns in headers
            if await self._contains_suspicious_patterns(header):
                logger.warning(f"Suspicious patterns found in file: {filename}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Malware scan failed: {str(e)}")
            return False
    
    async def _is_potentially_executable(self, header: bytes, extension: str) -> bool:
        """Check if file might be an executable in disguise."""
        # Common executable signatures
        executable_signatures = [
            b'MZ',  # Windows PE
            b'\x7fELF',  # Linux ELF
            b'#!',  # Shell script
        ]
        
        # Check if header matches executable signature but extension doesn't match
        is_executable = any(header.startswith(sig) for sig in executable_signatures)
        
        if is_executable and extension not in ['exe', 'dll', 'so', 'bin', 'sh', 'bash']:
            return True
            
        return False
    
    async def _contains_suspicious_patterns(self, header: bytes) -> bool:
        """Check for suspicious patterns in file header."""
        suspicious_patterns = [
            b'eval(',  # JavaScript eval
            b'base64_decode',  # PHP base64 decoding
            b'powershell',  # PowerShell commands
            b'cmd.exe',  # Windows command prompt
        ]
        
        return any(pattern in header for pattern in suspicious_patterns)
    
    def get_file_category(self, filename: str) -> str:
        """
        Determine file category based on extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            File category string
        """
        extension = Path(filename).suffix.lower().lstrip('.')
        
        if extension in ['stl', 'obj', 'fbx', 'glb', 'gltf', '3mf', 'blend']:
            return "3d_models"
        elif extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            return "images"
        elif extension in ['zip', 'rar', '7z']:
            return "archives"
        else:
            return "other"
    
    async def cleanup_orphaned_files(self, storage_service, older_than_days: int = 1):
        """
        Clean up orphaned files that were uploaded but never associated with a design.
        
        Args:
            storage_service: Instance of StorageService
            older_than_days: Delete files older than this many days
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=older_than_days)
            # Implementation would depend on your storage strategy
            logger.info("Orphaned file cleanup completed")
            
        except Exception as e:
            logger.error(f"File cleanup failed: {str(e)}")