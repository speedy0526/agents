"""
Minimal Agent Tools - File
"""

from pathlib import Path
from .base import BaseTool, ToolResult


class FileReadTool(BaseTool):
    """Read file content"""

    @property
    def name(self) -> str:
        return "file_read"

    @property
    def description(self) -> str:
        return "Read content from a file"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the file"
                }
            },
            "required": ["filepath"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        """Execute file read"""
        try:
            filepath = kwargs.get("filepath", "")
            if not filepath:
                return self.error("Missing filepath", "Filepath required")

            path = Path(filepath)
            if not path.exists():
                return self.error("File not found", f"File not found: {filepath}")

            content = path.read_text(encoding="utf-8")

            return self.success(
                {"filepath": filepath, "content": content},
                f"Read {len(content)} characters from {filepath}"
            )

        except Exception as e:
            return self.error(str(e), f"Read failed: {str(e)}")


class FileWriteTool(BaseTool):
    """Write content to file"""

    @property
    def name(self) -> str:
        return "file_write"

    @property
    def description(self) -> str:
        return "Write content to a file"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the file"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write"
                }
            },
            "required": ["filepath", "content"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        """Execute file write"""
        try:
            filepath = kwargs.get("filepath", "")
            content = kwargs.get("content", "")

            if not filepath:
                return self.error("Missing filepath", "Filepath required")

            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

            return self.success(
                {"filepath": filepath, "size": len(content)},
                f"Wrote {len(content)} characters to {filepath}"
            )

        except Exception as e:
            return self.error(str(e), f"Write failed: {str(e)}")
