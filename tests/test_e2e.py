"""
端到端测试:完整的agent工作流
"""

import pytest
import os
from src.agent import MinimalAgent


@pytest.mark.asyncio
async def test_research_workflow_end_to_end():
    """测试完整的research工作流"""
    agent = MinimalAgent(
        tools=[],
        skills_dirs=["skills"],
        workspace_dir="test_workspace"
    )

    # 执行research任务
    result = await agent.run("Research recent developments in generative AI", max_steps=5)

    # 验证:任务成功完成
    assert "complete" in result.lower() or "finish" in result.lower()

    # 验证:生成了研究文件
    research_files = [
        f for f in os.listdir("test_workspace")
        if f.endswith('.md') and 'research' in f.lower()
    ]
    assert len(research_files) > 0, "Research file should be created"

    # 清理
    for f in research_files:
        os.remove(os.path.join("test_workspace", f))


@pytest.mark.asyncio
async def test_skill_activation_and_deactivation():
    """测试skill的激活和停用流程"""
    agent = MinimalAgent(tools=[], skills_dirs=["skills"], workspace_dir="test_workspace")

    # 初始状态:没有active skills
    initial_messages = agent.context.get_messages(include_goals=False)
    initial_system_messages = [m for m in initial_messages if m["role"] == "system"]
    initial_has_workflow = any("<WORKFLOW>" in m["content"] for m in initial_system_messages)
    assert not initial_has_workflow, "No workflow should be present initially"

    # 激活research skill
    await agent.execute_tool("skill", {"command": "research"})

    # 验证:workflow被添加
    after_activation = agent.context.get_messages(include_goals=False)
    after_system_messages = [m for m in after_activation if m["role"] == "system"]
    has_workflow = any("<WORKFLOW>" in m["content"] for m in after_system_messages)
    assert has_workflow, "Workflow should be present after skill activation"


@pytest.mark.asyncio
async def test_structured_output_format_compliance():
    """测试端到端场景下的结构化输出格式合规性"""
    agent = MinimalAgent(tools=[], skills_dirs=["skills"], workspace_dir="test_workspace")

    # 添加用户请求
    agent.context.add_user_request("Test task")

    # 生成多个thoughts
    thoughts = []
    for _ in range(3):
        thought = await agent.think()
        thoughts.append(thought)

    # 验证所有thoughts都符合Thought模型
    for thought in thoughts:
        assert hasattr(thought, 'reasoning'), "Each thought should have reasoning"
        assert hasattr(thought, 'next_action'), "Each thought should have next_action"
        assert not hasattr(thought, 'answer'), "Thought should not have answer field"
        assert not hasattr(thought, 'summary'), "Thought should not have summary field"


@pytest.mark.asyncio
async def test_message_filtering_in_real_scenario():
    """测试真实场景下的消息过滤"""
    agent = MinimalAgent(tools=[], skills_dirs=["skills"], workspace_dir="test_workspace")

    # 模拟真实的对话流程
    agent.context.add_user_request("Research AI trends")
    thought1 = await agent.think()
    assert thought1.next_action == "use_tool"

    await agent.execute_tool("skill", {"command": "research"})

    agent.context.add_assistant_response("The research skill is now active")

    # 再次生成thought
    thought2 = await agent.think()

    # 验证:thought2符合Thought模型
    assert hasattr(thought2, 'reasoning')
    assert hasattr(thought2, 'next_action')

    # 验证:消息过滤正确
    messages = agent.context.get_messages(include_goals=False)
    filtered, _ = agent.llm.filter_messages_intelligent(messages)

    # 检查过滤后的messages
    filtered_system_messages = [m for m in filtered if m["role"] == "system"]
    has_workflow = any("<WORKFLOW>" in m["content"] for m in filtered_system_messages)
    has_output_format = any("<OUTPUT_FORMAT>" in m["content"] for m in filtered_system_messages)

    assert has_workflow, "Workflow should be preserved"
    assert not has_output_format, "Output format should be filtered"


@pytest.mark.asyncio
async def test_integration_with_context_goals():
    """测试与context goals的集成"""
    agent = MinimalAgent(
        tools=[],
        skills_dirs=["skills"],
        workspace_dir="test_workspace"
    )

    # 添加goals
    agent.context.set_goals([
        "Research AI trends",
        "Compile findings",
        "Save to markdown"
    ])

    # 激活skill
    await agent.execute_tool("skill", {"command": "research"})

    # 获取包含goals的messages
    messages_with_goals = agent.context.get_messages(include_goals=True)
    messages_without_goals = agent.context.get_messages(include_goals=False)

    # 验证:包含goals的messages更长
    assert len(messages_with_goals) > len(messages_without_goals)

    # 过滤messages
    filtered, _ = agent.llm.filter_messages_intelligent(messages_with_goals)

    # 验证:goals被保留(它们不是system消息)
    non_system_messages = [m for m in filtered if m["role"] != "system"]
    assert len(non_system_messages) > 0, "Non-system messages (including goals) should be preserved"


@pytest.mark.skip(reason="Requires actual API calls, marked as slow test")
@pytest.mark.asyncio
async def test_full_research_workflow_with_api():
    """完整的研究工作流测试(需要API调用,标记为慢测试)"""
    agent = MinimalAgent(
        tools=[],
        skills_dirs=["skills"],
        workspace_dir="test_workspace"
    )

    # 执行完整的研究任务
    result = await agent.run(
        "Research recent developments in machine learning",
        max_steps=10
    )

    # 验证结果
    assert result is not None
    assert isinstance(result, str)

    # 验证生成的文件
    research_files = [
        f for f in os.listdir("test_workspace")
        if f.endswith('.md') and 'research' in f.lower()
    ]
    if len(research_files) > 0:
        # 清理
        for f in research_files:
            os.remove(os.path.join("test_workspace", f))
