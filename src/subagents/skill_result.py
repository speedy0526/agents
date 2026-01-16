"""
Unified SkillResult
定义统一的Skill执行结果格式
"""

from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field


class SkillResult(BaseModel):
    """统一的Skill执行结果"""
    
    # ========== 必需字段 ==========
    success: bool = Field(
        description="执行是否成功"
    )
    
    # ========== 基础信息字段 ==========
    confirmation: Optional[str] = Field(
        default=None,
        description="完成确认信息，如'Research complete'"
    )
    
    summary: Optional[str] = Field(
        default=None,
        description="执行结果的简要总结"
    )
    
    details: Optional[str] = Field(
        default=None,
        description="执行结果的详细信息"
    )
    
    # ========== 数据输出字段 ==========
    data: Optional[Any] = Field(
        default=None,
        description="原始数据输出（可以是任意类型）"
    )
    
    structured_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="结构化的数据输出（JSON格式）"
    )
    
    text_output: Optional[str] = Field(
        default=None,
        description="文本输出（提取的文本、生成的内容等）"
    )
    
    # ========== 列表输出字段 ==========
    items: Optional[List[Any]] = Field(
        default=None,
        description="列表输出（搜索结果、文件列表等）"
    )
    
    insights: Optional[List[str]] = Field(
        default=None,
        description="关键发现或洞察列表"
    )
    
    errors: Optional[List[str]] = Field(
        default=None,
        description="错误信息列表（如果是部分成功）"
    )
    
    # ========== 文件相关字段 ==========
    file_path: Optional[str] = Field(
        default=None,
        description="生成的文件路径"
    )
    
    file_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="文件详情（字数、页数、大小等）"
    )
    
    file_paths: Optional[List[str]] = Field(
        default=None,
        description="生成的多个文件路径"
    )
    
    # ========== 统计信息字段 ==========
    count: Optional[int] = Field(
        default=None,
        description="数量统计（结果数、处理条数等）"
    )
    
    rows_processed: Optional[int] = Field(
        default=None,
        description="处理的行数（Excel、CSV等）"
    )
    
    tokens_used: Optional[int] = Field(
        default=None,
        description="使用的token数（如果涉及LLM调用）"
    )
    
    # ========== 扩展字段 ==========
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="自定义元数据（任意扩展信息）"
    )
    
    extra: Optional[Dict[str, Any]] = Field(
        default=None,
        description="额外信息（未来扩展）"
    )
 
    execution_time: Optional[float] = Field(
        default=None,
        description="执行时间（秒）"
    )
    
    # ========== 辅助方法 ==========
    def get_summary_or_confirmation(self) -> str:
        """获取总结或确认信息"""
        if self.summary:
            return self.summary
        if self.confirmation:
            return self.confirmation
        if self.details:
            return self.details
        return "Task completed"
    
    def get_file_info(self) -> Optional[Dict[str, Any]]:
        """获取文件信息（如果有）"""
        if self.file_path:
            info = {"file_path": self.file_path}
            if self.file_details:
                info.update(self.file_details)
            return info
        if self.file_paths:
            info = {"file_paths": self.file_paths}
            if self.file_details:
                info.update(self.file_details)
            return info
        return None
    
    def has_data(self) -> bool:
        """是否有数据输出"""
        return any([
            self.data is not None,
            self.structured_data is not None,
            self.text_output is not None,
            self.items is not None,
            self.insights is not None
        ])
    
    def is_complete_success(self) -> bool:
        """是否完全成功（无错误）"""
        return self.success and not self.errors
