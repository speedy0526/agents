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
        return "Read content from a file,file_path is the path to read the file, containing directory and filename"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to read the file, containing directory and filename"}
            },
            "required": ["file_path"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        """Execute file read"""
        try:
            file_path = kwargs.get("file_path", "")
            if not file_path:
                return self.error("Missing file_path", "file_path required")

            path = Path(file_path)
            if not path.exists():
                return self.error("File not found", f"File not found: {file_path}")

            content = path.read_text(encoding="utf-8")

            return self.success(
                {"file_path": file_path, "content": content},
                f"Read {len(content)} characters from {file_path}",
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
        return "Write content to a file,file_path is required, file_path is the path to write the file, containing directory and filename"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to write the file, containing directory and filename"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["file_path", "content"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        """Execute file write"""
        try:
            file_path = kwargs.get("file_path", "")
            content = kwargs.get("content", "")

            if not file_path:
                return self.error("Missing file_path", "file_path required")

            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

            # Print save location and success message
            print(f"\n{'=' * 60}")
            print(f"✓ File saved successfully")
            print(f"  Directory: {path.parent.absolute()}")
            print(f"  Filename: {path.name}")
            print(f"  Size: {len(content)} characters")
            print(f"{'=' * 60}\n")

            return self.success(
                {"file_path": str(path.absolute()), "size": len(content)},
                f"Wrote {len(content)} characters to {file_path}",
            )

        except Exception as e:
            return self.error(str(e), f"Write failed: {str(e)}")
