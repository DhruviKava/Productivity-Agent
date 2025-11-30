"""
MCP (Model Context Protocol) tools for file operations.
Provides file read/write capabilities to agents.

FEATURE COVERED: MCP Tools
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.utils.config import Config
from src.observability.logger import setup_logger

logger = setup_logger("mcp_tools")


class MCP:
    """
    MCP server for file operations.
    Allows agents to read and write files safely.
    
    This implements the MCP requirement from the course.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Config.OUTPUTS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info("mcp_file_tool_initialized", base_dir=str(self.base_dir))
    
    def read_file(self, filename: str) -> Dict[str, Any]:
        """
        Read a file and return its contents.
        
        MCP Tool Specification:
        - Tool Name: read_file
        - Input: filename (string)
        - Output: file contents or error
        
        Usage by agent:
            result = mcp_tool.read_file("removed_tasksjson")
        """
        filepath = self.base_dir / filename
        
        logger.info("mcp_read_file", filename=filename)
        
        try:
            if not filepath.exists():
                return {
                    "success": False,
                    "error": f"File not found: {filename}"
                }
            
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Try to parse as JSON
            try:
                data = json.loads(content)
                return {
                    "success": True,
                    "filename": filename,
                    "content": data,
                    "content_type": "json"
                }
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "filename": filename,
                    "content": content,
                    "content_type": "text"
                }
        
        except Exception as e:
            logger.error("mcp_read_error", filename=filename, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def write_file(
        self,
        filename: str,
        content: Any,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Write content to a file.
        
        MCP Tool Specification:
        - Tool Name: write_file
        - Inputs: filename, content, format
        - Output: success status and filepath
        
        Usage by agent:
            result = mcp_tool.write_file("schedule.json", schedule_data)
        """
        filepath = self.base_dir / filename
        
        logger.info("mcp_write_file", filename=filename, format=format)
        
        try:
            if format == "json":
                with open(filepath, 'w') as f:
                    json.dump(content, f, indent=2, default=str)
            else:
                with open(filepath, 'w') as f:
                    f.write(str(content))
            
            return {
                "success": True,
                "filename": filename,
                "filepath": str(filepath),
                "bytes_written": filepath.stat().st_size
            }
        
        except Exception as e:
            logger.error("mcp_write_error", filename=filename, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_files(self, pattern: str = "*") -> Dict[str, Any]:
        """
        List files in the output directory.
        
        MCP Tool Specification:
        - Tool Name: list_files
        - Input: pattern (optional)
        - Output: list of files
        """
        logger.info("mcp_list_files", pattern=pattern)
        
        try:
            files = list(self.base_dir.glob(pattern))
            
            file_info = [
                {
                    "name": f.name,
                    "size_bytes": f.stat().st_size,
                    "modified": datetime.fromtimestamp(
                        f.stat().st_mtime
                    ).isoformat()
                }
                for f in files if f.is_file()
            ]
            
            return {
                "success": True,
                "files": file_info,
                "count": len(file_info)
            }
        
        except Exception as e:
            logger.error("mcp_list_error", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_file(self, filename: str) -> Dict[str, Any]:
        """
        Delete a file.
        
        MCP Tool Specification:
        - Tool Name: delete_file
        - Input: filename
        - Output: success status
        """
        filepath = self.base_dir / filename
        
        logger.info("mcp_delete_file", filename=filename)
        
        try:
            if filepath.exists():
                filepath.unlink()
                return {
                    "success": True,
                    "message": f"Deleted {filename}"
                }
            else:
                return {
                    "success": False,
                    "error": f"File not found: {filename}"
                }
        
        except Exception as e:
            logger.error("mcp_delete_error", filename=filename, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }


# Global MCP tool instance
_mcp_tool = MCP()

def get_mcp_tool() -> MCP:
    """Get the global MCP tool instance"""
    return _mcp_tool