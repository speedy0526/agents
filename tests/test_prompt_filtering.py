"""
测试智能消息过滤功能
"""

import pytest
from src.llm import LLMClient
from src.prompt_tags import META_INSTRUCTION_TAGS, CONTENT_INSTRUCTION_TAGS


def test_filter_messages_with_meta_only():
    """测试只包含元指令的消息"""
    llm = LLMClient()

    messages = [
        {"role": "system", "content": "You are helpful."},
        {
            "role": "system",
            "content": """<WORKFLOW>
Step 1: Do this
Step 2: Do that
</WORKFLOW>

<OUTPUT_FORMAT>
Answer: string
Summary: string
</OUTPUT_FORMAT>"""
        },
        {"role": "user", "content": "Help me"},
    ]

    filtered, debug_info = llm.filter_messages_intelligent(messages)

    # 验证:第一条system完整保留
    assert filtered[0]["content"] == "You are helpful."

    # 验证:第二条system只保留WORKFLOW,移除OUTPUT_FORMAT
    assert "<WORKFLOW>" in filtered[1]["content"]
    assert "<OUTPUT_FORMAT>" not in filtered[1]["content"]

    # 验证:user消息保留
    assert filtered[2]["content"] == "Help me"


def test_filter_messages_no_content_instructions():
    """测试没有内容指令的消息"""
    llm = LLMClient()

    messages = [
        {"role": "system", "content": "You are helpful."},
        {
            "role": "system",
            "content": """<OUTPUT_FORMAT>
Answer: string
</OUTPUT_FORMAT>"""
        },
    ]

    filtered, _ = llm.filter_messages_intelligent(messages)

    # 验证:只有第一条system保留
    assert len(filtered) == 1
    assert filtered[0]["content"] == "You are helpful."


def test_extract_content_instructions():
    """测试内容指令提取"""
    llm = LLMClient()

    content = """<WORKFLOW>
Step 1: Search
Step 2: Compile
</WORKFLOW>

<OUTPUT_FORMAT>
Answer: string
Summary: string
</OUTPUT_FORMAT>

<CONTEXT_INFO>
User: John
Task: Research
</CONTEXT_INFO>"""

    result = llm._extract_content_instructions(content)

    # 验证:只保留WORKFLOW和CONTEXT_INFO
    assert "<WORKFLOW>" in result
    assert "<CONTEXT_INFO>" in result
    assert "<OUTPUT_FORMAT>" not in result


def test_contains_tags():
    """测试标签检测"""
    llm = LLMClient()

    # 测试包含元指令标签
    content_with_meta = """<OUTPUT_FORMAT>
Answer: string
</OUTPUT_FORMAT>"""
    assert llm._contains_tags(content_with_meta, META_INSTRUCTION_TAGS) == True
    assert llm._contains_tags(content_with_meta, CONTENT_INSTRUCTION_TAGS) == False

    # 测试包含内容指令标签
    content_with_workflow = """<WORKFLOW>
Step 1: Do this
</WORKFLOW>"""
    assert llm._contains_tags(content_with_workflow, META_INSTRUCTION_TAGS) == False
    assert llm._contains_tags(content_with_workflow, CONTENT_INSTRUCTION_TAGS) == True


def test_filter_multiple_system_messages():
    """测试多个system消息的过滤"""
    llm = LLMClient()

    messages = [
        {"role": "system", "content": "System 1"},
        {
            "role": "system",
            "content": """<WORKFLOW>
Step 1: Do this
</WORKFLOW>

<OUTPUT_FORMAT>
Answer: string
</OUTPUT_FORMAT>"""
        },
        {
            "role": "system",
            "content": """<BEST_PRACTICES>
1. Be helpful
2. Be concise
</BEST_PRACTICES>"""
        },
        {"role": "user", "content": "Hello"},
    ]

    filtered, debug_info = llm.filter_messages_intelligent(messages)

    # 验证:第一条system完整保留
    assert filtered[0]["content"] == "System 1"

    # 验证:第二条system只保留WORKFLOW
    assert "<WORKFLOW>" in filtered[1]["content"]
    assert "<OUTPUT_FORMAT>" not in filtered[1]["content"]

    # 验证:第三条system保留BEST_PRACTICES
    assert "<BEST_PRACTICES>" in filtered[2]["content"]

    # 验证:user消息保留
    assert filtered[3]["content"] == "Hello"


def test_filter_empty_content_instruction():
    """测试内容指令提取后为空的情况"""
    llm = LLMClient()

    messages = [
        {"role": "system", "content": "System 1"},
        {
            "role": "system",
            "content": """<OUTPUT_FORMAT>
Answer: string
</OUTPUT_FORMAT>

<RESPONSE_FORMAT>
Just text
</RESPONSE_FORMAT>"""
        },
        {"role": "user", "content": "Hello"},
    ]

    filtered, debug_info = llm.filter_messages_intelligent(messages)

    # 验证:只有第一条system保留,第二条system被完全过滤(没有内容指令)
    assert len(filtered) == 2
    assert filtered[0]["content"] == "System 1"
    assert filtered[1]["content"] == "Hello"
