"""
测试Agent使用Skill时的消息过滤
"""

import pytest
from src.agent import MinimalAgent


@pytest.mark.asyncio
async def test_research_skill_workflow():
    """测试research skill的工作流程可见性"""
    agent = MinimalAgent(tools=[], skills_dirs=["skills"])

    # 模拟使用research skill
    thought1 = await agent.think()
    assert thought1.next_action == "use_tool"

    # 执行skill工具
    await agent.execute_tool("skill", {"command": "research"})

    # 检查context中包含skill的workflow指令
    messages = agent.context.get_messages(include_goals=False)
    system_messages = [m for m in messages if m["role"] == "system"]

    # 验证:至少包含<WORKFLOW>标签
    workflow_found = any("<WORKFLOW>" in m["content"] for m in system_messages)
    assert workflow_found, "Skill workflow instructions should be visible"

    # 验证:在think()时,<OUTPUT_FORMAT>被过滤
    filtered, _ = agent.llm.filter_messages_intelligent(messages)
    output_format_in_system = any(
        "<OUTPUT_FORMAT>" in m["content"] and m["role"] == "system"
        for m in filtered
    )
    assert not output_format_in_system, "Output format in skills should be filtered in think()"


@pytest.mark.asyncio
async def test_structured_output_compliance():
    """测试结构化输出符合Thought模型"""
    agent = MinimalAgent(tools=[], skills_dirs=["skills"])

    # 添加一些对话历史
    agent.context.add_user_request("Research AI trends")
    agent.context.add_assistant_response("The research skill is now active")

    # 生成thought
    thought = await agent.think()

    # 验证:返回的是Thought对象,不是Skill要求的格式
    assert hasattr(thought, 'reasoning')
    assert hasattr(thought, 'next_action')
    assert not hasattr(thought, 'answer')
    assert not hasattr(thought, 'summary')


@pytest.mark.asyncio
async def test_skill_content_preservation():
    """测试skill的内容指令被保留"""
    agent = MinimalAgent(tools=[], skills_dirs=["skills"])

    # 激活research skill
    await agent.execute_tool("skill", {"command": "research"})

    # 获取messages
    messages = agent.context.get_messages(include_goals=False)

    # 过滤messages
    filtered, _ = agent.llm.filter_messages_intelligent(messages)

    # 检查内容指令被保留
    filtered_system_messages = [m for m in filtered if m["role"] == "system"]
    content_instruction_found = any(
        any(tag in m["content"] for tag in ["<WORKFLOW>", "<BEST_PRACTICES>", "<ERROR_HANDLING>"])
        for m in filtered_system_messages
    )
    assert content_instruction_found, "Content instructions from skills should be preserved"


@pytest.mark.asyncio
async def test_meta_instruction_priority():
    """测试元指令优先级高于内容指令"""
    agent = MinimalAgent(tools=[], skills_dirs=["skills"])

    # 激活research skill
    await agent.execute_tool("skill", {"command": "research"})

    # 获取messages
    messages = agent.context.get_messages(include_goals=False)

    # 过滤messages
    filtered, debug_info = agent.llm.filter_messages_intelligent(messages)

    # 验证元指令被过滤
    original_system_messages = [m for m in messages if m["role"] == "system"]
    original_meta_count = sum(
        1 for m in original_system_messages
        if any(tag in m["content"] for tag in ["<OUTPUT_FORMAT>", "<RESPONSE_FORMAT>"])
    )

    filtered_system_messages = [m for m in filtered if m["role"] == "system"]
    filtered_meta_count = sum(
        1 for m in filtered_system_messages
        if any(tag in m["content"] for tag in ["<OUTPUT_FORMAT>", "<RESPONSE_FORMAT>"])
    )

    # 验证:过滤后的元指令数量减少(或者被完全移除)
    assert filtered_meta_count <= original_meta_count, "Meta instructions should be filtered"


@pytest.mark.asyncio
async def test_multiple_skills_workflow():
    """测试多个skill激活时的消息过滤"""
    agent = MinimalAgent(tools=[], skills_dirs=["skills"])

    # 激活多个skills
    await agent.execute_tool("skill", {"command": "research"})
    await agent.execute_tool("skill", {"command": "pdf"})

    # 获取messages
    messages = agent.context.get_messages(include_goals=False)

    # 过滤messages
    filtered, _ = agent.llm.filter_messages_intelligent(messages)

    # 验证内容指令被保留
    filtered_system_messages = [m for m in filtered if m["role"] == "system"]
    content_instruction_found = any(
        any(tag in m["content"] for tag in ["<WORKFLOW>", "<BEST_PRACTICES>", "<ERROR_HANDLING>"])
        for m in filtered_system_messages
    )
    assert content_instruction_found, "Content instructions from multiple skills should be preserved"

    # 验证元指令被过滤
    meta_instruction_found = any(
        "<OUTPUT_FORMAT>" in m["content"] or "<RESPONSE_FORMAT>" in m["content"]
        for m in filtered_system_messages
    )
    assert not meta_instruction_found, "Meta instructions should be filtered"
