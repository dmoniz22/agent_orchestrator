"""File system tools for reading and writing files."""

from pathlib import Path
from typing import Any
import os

from src.skills.base import (
    BaseTool,
    ToolDangerLevel,
    ToolParameter,
    ToolResult,
    ToolSchema,
)
from src.core.exceptions import ToolExecutionError
from src.core.logging import get_logger

logger = get_logger(__name__)


class FileReadTool(BaseTool):
    """Tool for reading files."""
    
    def __init__(self, allowed_paths: list[str] | None = None) -> None:
        """Initialize file read tool.
        
        Args:
            allowed_paths: List of allowed path prefixes for security.
        """
        super().__init__(
            tool_id="file.read",
            name="File Read",
            description="Read contents of a file",
            danger_level=ToolDangerLevel.SAFE,
            timeout_seconds=10
        )
        self.allowed_paths = [Path(p).resolve() for p in (allowed_paths or [])]
    
    async def execute(
        self,
        path: str,
        limit_lines: int | None = None
    ) -> ToolResult:
        """Read file contents.
        
        Args:
            path: File path to read.
            limit_lines: Optional line limit.
            
        Returns:
            Tool result with file contents.
        """
        logger.info(
            "Reading file",
            tool_id=self.tool_id,
            path=path
        )
        
        try:
            file_path = Path(path).resolve()
            
            # Security check
            if not self._is_allowed_path(file_path):
                return ToolResult(
                    success=False,
                    error=f"Access denied: {path}",
                    metadata={"path": str(file_path)}
                )
            
            # Check if file exists
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    error=f"File not found: {path}",
                    metadata={"path": str(file_path)}
                )
            
            # Check if it's a file
            if not file_path.is_file():
                return ToolResult(
                    success=False,
                    error=f"Not a file: {path}",
                    metadata={"path": str(file_path)}
                )
            
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                if limit_lines:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= limit_lines:
                            break
                        lines.append(line)
                    content = ''.join(lines)
                    truncated = True
                else:
                    content = f.read()
                    truncated = False
            
            return ToolResult(
                success=True,
                result={
                    "path": str(file_path),
                    "content": content,
                    "size_bytes": len(content.encode('utf-8')),
                    "truncated": truncated
                },
                metadata={
                    "path": str(file_path),
                    "lines_read": content.count('\n') + 1
                }
            )
            
        except UnicodeDecodeError:
            return ToolResult(
                success=False,
                error=f"File is not text-readable: {path}",
                metadata={"path": path}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to read file: {e}",
                metadata={"path": path}
            )
    
    def _is_allowed_path(self, path: Path) -> bool:
        """Check if path is within allowed directories.
        
        Args:
            path: Path to check.
            
        Returns:
            True if path is allowed.
        """
        if not self.allowed_paths:
            # Allow all paths if no restrictions
            return True
        
        # Check if path is under any allowed path
        for allowed in self.allowed_paths:
            try:
                path.relative_to(allowed)
                return True
            except ValueError:
                continue
        
        return False
    
    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            name=self.name,
            description=self.description,
            danger_level=self.danger_level,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to read",
                    required=True
                ),
                ToolParameter(
                    name="limit_lines",
                    type="integer",
                    description="Maximum number of lines to read (optional)",
                    required=False
                )
            ]
        )


class FileWriteTool(BaseTool):
    """Tool for writing files."""
    
    def __init__(self, allowed_paths: list[str] | None = None) -> None:
        """Initialize file write tool.
        
        Args:
            allowed_paths: List of allowed path prefixes for security.
        """
        super().__init__(
            tool_id="file.write",
            name="File Write",
            description="Write content to a file",
            danger_level=ToolDangerLevel.DESTRUCTIVE,
            timeout_seconds=10
        )
        self.allowed_paths = [Path(p).resolve() for p in (allowed_paths or [])]
    
    async def execute(
        self,
        path: str,
        content: str,
        append: bool = False
    ) -> ToolResult:
        """Write content to file.
        
        Args:
            path: File path to write.
            content: Content to write.
            append: Whether to append or overwrite.
            
        Returns:
            Tool result with write status.
        """
        logger.info(
            "Writing file",
            tool_id=self.tool_id,
            path=path,
            append=append
        )
        
        try:
            file_path = Path(path).resolve()
            
            # Security check
            if not self._is_allowed_path(file_path):
                return ToolResult(
                    success=False,
                    error=f"Access denied: {path}",
                    metadata={"path": str(file_path)}
                )
            
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            mode = 'a' if append else 'w'
            with open(file_path, mode, encoding='utf-8') as f:
                f.write(content)
            
            return ToolResult(
                success=True,
                result={
                    "path": str(file_path),
                    "bytes_written": len(content.encode('utf-8')),
                    "mode": "append" if append else "write"
                },
                metadata={
                    "path": str(file_path),
                    "append": append
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to write file: {e}",
                metadata={"path": path}
            )
    
    def _is_allowed_path(self, path: Path) -> bool:
        """Check if path is within allowed directories.
        
        Args:
            path: Path to check.
            
        Returns:
            True if path is allowed.
        """
        if not self.allowed_paths:
            # Allow all paths if no restrictions
            return True
        
        # Check if path is under any allowed path
        for allowed in self.allowed_paths:
            try:
                path.relative_to(allowed)
                return True
            except ValueError:
                continue
        
        return False
    
    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            name=self.name,
            description=self.description,
            danger_level=self.danger_level,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to write",
                    required=True
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write to the file",
                    required=True
                ),
                ToolParameter(
                    name="append",
                    type="boolean",
                    description="Whether to append to existing file (default: false)",
                    required=False,
                    default=False
                )
            ]
        )
