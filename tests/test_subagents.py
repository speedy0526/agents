"""
测试SubAgent架构
"""

import pytest
from pydantic import BaseModel, Field
from src.subagents import (
    SubAgent,
    SubAgentResult,
    SkillResult
)
from src.context import ContextManager


# ===== Mock Tool =====
class MockTool(BaseModel):
    name: str = "test_tool"
    description: str = "A test tool"
    parameters: dict = {"type": "object", "properties": {}}
    
    async def __call__(self, **kwargs):
        """Execute tool"""
        return MockToolResult(
            status="success",
            summary=f"Executed with params: {kwargs}"
        )


class MockToolResult(BaseModel):
    status: str
    summary: str


# ===== Mock Skill Manager =====
class MockSkillManager:
    """Mock SkillManager for testing"""
    
    async def execute_skill(self, command: str, parameters: dict) -> SkillResult:
        """Execute mock skill"""
        if command == "test_skill":
            return SkillResult(
                success=True,
                confirmation="Test skill complete",
                summary="Test skill executed successfully",
                text_output="Test output",
                metadata={"skill": "test_skill"}
            )
        else:
            return SkillResult(
                success=False,
                summary=f"Unknown skill: {command}",
                errors=["Skill not found"]
            )
    
    def list_skills(self):
        return ["test_skill", "mock_skill"]
    
    def get_skill_names(self):
        return ["test_skill", "mock_skill"]


# ===== Test SubAgentResult =====
def test_sub_agent_result_creation():
    """测试SubAgentResult创建"""
    result = SubAgentResult(
        success=True,
        result={"key": "value"},
        summary="Test completed",
        metadata={"test": True}
    )
    
    assert result.success == True
    assert result.summary == "Test completed"
    assert result.result == {"key": "value"}


def test_sub_agent_result_failure():
    """测试SubAgentResult失败情况"""
    result = SubAgentResult(
        success=False,
        error="Test error",
        metadata={"error": True}
    )
    
    assert result.success == False
    assert result.error == "Test error"
    assert result.result is None


# ===== Test SkillResult =====
def test_skill_result_basic():
    """测试SkillResult基本功能"""
    result = SkillResult(
        success=True,
        confirmation="Test complete",
        summary="Test summary"
    )
    
    assert result.success == True
    assert result.confirmation == "Test complete"
    assert result.summary == "Test summary"
    assert result.get_summary_or_confirmation() == "Test summary"


def test_skill_result_with_file():
    """测试SkillResult包含文件信息"""
    result = SkillResult(
        success=True,
        file_path="/path/to/file.md",
        file_details={"word_count": 100}
    )
    
    file_info = result.get_file_info()
    assert file_info is not None
    assert file_info["file_path"] == "/path/to/file.md"
    assert file_info["word_count"] == 100


def test_skill_result_has_data():
    """测试SkillResult数据检查"""
    # 有数据
    result1 = SkillResult(
        success=True,
        items=[1, 2, 3]
    )
    assert result1.has_data() == True
    
    # 有insights
    result2 = SkillResult(
        success=True,
        insights=["insight1", "insight2"]
    )
    assert result2.has_data() == True
    
    # 无数据
    result3 = SkillResult(success=True)
    assert result3.has_data() == False


def test_skill_result_complete_success():
    """测试SkillResult完全成功"""
    # 完全成功
    result1 = SkillResult(success=True)
    assert result1.is_complete_success() == True
    
    # 有错误
    result2 = SkillResult(
        success=True,
        errors=["error1", "error2"]
    )
    assert result2.is_complete_success() == False
    
    # 失败
    result3 = SkillResult(
        success=False,
        errors=["error"]
    )
    assert result3.is_complete_success() == False


def test_skill_result_get_summary_or_confirmation():
    """测试get_summary_or_confirmation方法"""
    # 有summary
    result1 = SkillResult(
        success=True,
        summary="Test summary",
        confirmation="Test complete"
    )
    assert result1.get_summary_or_confirmation() == "Test summary"
    
    # 只有confirmation
    result2 = SkillResult(
        success=True,
        confirmation="Test complete"
    )
    assert result2.get_summary_or_confirmation() == "Test complete"
    
    # 都没有
    result3 = SkillResult(success=True)
    assert result3.get_summary_or_confirmation() == "Task completed"


# ===== Test ToolSubAgent =====
@pytest.mark.asyncio
async def test_tool_sub_agent_success():
    """测试ToolSubAgent成功执行"""
    context = ContextManager(workspace_dir="test_workspace")
    
    tool = MockTool()
    tools = {"test_tool": tool}
    
    from src.subagents.tool_subagent import ToolSubAgent
    subagent = ToolSubAgent(context, tools)
    
    result = await subagent.execute(
        command="test_tool",
        parameters={"param1": "value1"}
    )
    
    assert result.success == True
    assert result.summary == "Tool 'test_tool' executed successfully"
    assert result.metadata["tool_name"] == "test_tool"


@pytest.mark.asyncio
async def test_tool_sub_agent_not_found():
    """测试ToolSubAgent工具不存在"""
    context = ContextManager(workspace_dir="test_workspace")
    tools = {}
    
    from src.subagents.tool_subagent import ToolSubAgent
    subagent = ToolSubAgent(context, tools)
    
    result = await subagent.execute(
        command="nonexistent_tool",
        parameters={}
    )
    
    assert result.success == False
    assert "Tool not found" in result.error


# ===== Test SkillSubAgent =====
@pytest.mark.asyncio
async def test_skill_sub_agent_success():
    """测试SkillSubAgent成功执行"""
    context = ContextManager(workspace_dir="test_workspace")
    skill_manager = MockSkillManager()
    
    from src.subagents.skill_subagent import SkillSubAgent
    subagent = SkillSubAgent(context, skill_manager)
    
    result = await subagent.execute(
        command="test_skill",
        parameters={}
    )
    
    assert result.success == True
    assert result.summary == "Test skill complete"
    assert isinstance(result.result, SkillResult)
    assert result.result.confirmation == "Test skill complete"


@pytest.mark.asyncio
async def test_skill_sub_agent_failure():
    """测试SkillSubAgent失败执行"""
    context = ContextManager(workspace_dir="test_workspace")
    skill_manager = MockSkillManager()
    
    from src.subagents.skill_subagent import SkillSubAgent
    subagent = SkillSubAgent(context, skill_manager)
    
    result = await subagent.execute(
        command="unknown_skill",
        parameters={}
    )
    
    assert result.success == False
    assert isinstance(result.result, SkillResult)
    assert result.result.success == False


# ===== Test ContextManager Shared Memory =====
def test_context_shared_memory():
    """测试ContextManager的shared_memory功能"""
    context = ContextManager(workspace_dir="test_workspace")
    
    # 测试更新
    context.update_shared_memory("key1", "value1")
    assert context.get_shared_memory("key1") == "value1"
    
    # 测试默认值
    assert context.get_shared_memory("nonexistent", "default") == "default"
    
    # 测试覆盖
    context.update_shared_memory("key1", "value2")
    assert context.get_shared_memory("key1") == "value2"
    
    # 测试快照
    snapshot = context.get_snapshot()
    assert "shared_memory" in snapshot
    assert snapshot["shared_memory"]["key1"] == "value2"
    
    # 测试清空
    context.clear_shared_memory()
    assert context.get_shared_memory("key1") is None
    snapshot_after = context.get_snapshot()
    assert snapshot_after["shared_memory"] == {}


def test_context_snapshot_structure():
    """测试ContextSnapshot的结构"""
    context = ContextManager(workspace_dir="test_workspace")
    
    # 添加一些数据
    context.add_user_request("Test request")
    context.add_assistant_response("Test response")
    
    # 获取快照
    snapshot = context.get_snapshot()
    
    assert "goals" in snapshot
    assert "recent_entries" in snapshot
    assert "shared_memory" in snapshot
    assert len(snapshot["recent_entries"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
