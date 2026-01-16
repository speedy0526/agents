"""
SubAgent Architecture
定义SubAgent基类和相关协议
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class SubAgentResult(BaseModel):
    """SubAgent执行结果的统一格式"""
    
    # 必需字段
    success: bool = Field(description="执行是否成功")
    
    # 基础信息
    result: Optional[Any] = Field(
        default=None,
        description="执行结果（可以是任意类型）"
    )
    summary: Optional[str] = Field(
        default=None,
        description="执行结果的简要总结"
    )
    error: Optional[str] = Field(
        default=None,
        description="错误信息"
    )
    
    # 统计和元数据
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="元数据（SubAgent类型、执行时间等）"
    )
    tokens_used: Optional[int] = Field(
        default=None,
        description="使用的token数"
    )
    execution_time: Optional[float] = Field(
        default=None,
        description="执行时间（秒）"
    )

class SubAgent(ABC):
    """SubAgent抽象基类"""
    
    @abstractmethod
    async def execute(self, command: str, parameters: Dict[str, Any]) -> SubAgentResult:
        """
        执行命令并返回结果
        
        Args:
            command: 命令名称
            parameters: 命令参数
        
        Returns:
            SubAgentResult
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """返回SubAgent的能力描述和参数schema"""
        pass
