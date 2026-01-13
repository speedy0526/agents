"""
Skills System
Higher-level abstractions that combine multiple tools for complex tasks
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class SkillResult(BaseModel):
    """Skill execution result"""
    skill_name: str
    status: str = Field(description="'success' or 'failed'")
    result: Dict[str, Any] = Field(default_factory=dict)
    steps_completed: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    summary: str = ""
    duration_ms: Optional[float] = None


class Skill(ABC):
    """
    Base class for all skills

    Skills are higher-level abstractions that:
    - Combine multiple tools
    - Execute multi-step workflows
    - Provide clear input/output contracts
    - Can be reused and composed
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Skill name (should follow pattern: category_task)"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """What this skill does"""
        pass

    @property
    @abstractmethod
    def required_tools(self) -> List[str]:
        """List of tool names required by this skill"""
        pass

    @property
    def parameters(self) -> Dict[str, Any]:
        """Skill input parameters schema"""
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    @abstractmethod
    async def execute(self, tools: Dict[str, Any], **kwargs) -> SkillResult:
        """
        Execute the skill

        Args:
            tools: Dictionary of available tool instances
            **kwargs: Skill parameters

        Returns:
            SkillResult: Execution result with steps and errors
        """
        pass

    def _create_success_result(
        self,
        result: Dict[str, Any],
        steps: List[Dict[str, Any]],
        summary: str,
        duration_ms: float
    ) -> SkillResult:
        """Create successful skill result"""
        return SkillResult(
            skill_name=self.name,
            status="success",
            result=result,
            steps_completed=steps,
            summary=summary,
            duration_ms=duration_ms
        )

    def _create_error_result(
        self,
        errors: List[str],
        steps: List[Dict[str, Any]],
        summary: str,
        duration_ms: float
    ) -> SkillResult:
        """Create failed skill result"""
        return SkillResult(
            skill_name=self.name,
            status="failed",
            errors=errors,
            steps_completed=steps,
            summary=summary,
            duration_ms=duration_ms
        )

    def validate_tools(self, tools: Dict[str, Any]) -> bool:
        """Validate that required tools are available"""
        missing_tools = set(self.required_tools) - set(tools.keys())
        if missing_tools:
            raise ValueError(f"Missing required tools for {self.name}: {missing_tools}")
        return True
