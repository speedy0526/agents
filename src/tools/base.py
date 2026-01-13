"""
Minimal Agent Tools - Base
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ToolResult(BaseModel):
    """Tool execution result"""
    tool_name: str
    status: str
    result: Dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    summary: str = ""


class BaseTool(ABC):
    """Base class for all tools"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """Tool parameters schema"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute tool"""
        pass

    def success(self, result: Dict[str, Any], summary: str) -> ToolResult:
        """Create success result"""
        return ToolResult(
            tool_name=self.name,
            status="success",
            result=result,
            summary=summary
        )

    def error(self, error_msg: str, summary: str) -> ToolResult:
        """Create error result"""
        return ToolResult(
            tool_name=self.name,
            status="failed",
            error=error_msg,
            summary=summary
        )
