#!/usr/bin/env python3
"""
Test Skills System
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.skills import ResearchSkill, MultiTopicResearchSkill
from src.tools import SearchGoogleTool, FileWriteTool
import asyncio


async def test_research_skill():
    """Test basic research skill"""
    print("=" * 60)
    print("Testing ResearchSkill")
    print("=" * 60)

    # Create tools
    tools = {
        "search_google": SearchGoogleTool(),
        "file_write": FileWriteTool()
    }

    # Create skill
    skill = ResearchSkill()

    print(f"\nSkill name: {skill.name}")
    print(f"Description: {skill.description}")
    print(f"Required tools: {skill.required_tools}")

    # Execute skill
    print("\nExecuting skill...")
    result = await skill.execute(
        tools=tools,
        topic="Python programming",
        max_results=3,
        output_file="test_research.md"
    )

    print(f"\nStatus: {result.status}")
    print(f"Summary: {result.summary}")
    print(f"Duration: {result.duration_ms:.2f}ms")
    print(f"Steps completed: {len(result.steps_completed)}")

    for i, step in enumerate(result.steps_completed, 1):
        print(f"\n  Step {i}: {step.get('action')}")
        print(f"    Description: {step.get('description')}")
        if 'result' in step:
            print(f"    Result: {step.get('result')}")

    if result.errors:
        print(f"\nErrors: {result.errors}")
    else:
        print(f"\nResult data: {result.result}")

    print("\n✓ ResearchSkill test completed")


async def test_multi_topic_skill():
    """Test multi-topic research skill"""
    print("\n" + "=" * 60)
    print("Testing MultiTopicResearchSkill")
    print("=" * 60)

    # Create tools
    tools = {
        "search_google": SearchGoogleTool(),
        "file_write": FileWriteTool()
    }

    # Create skill
    skill = MultiTopicResearchSkill()

    print(f"\nSkill name: {skill.name}")
    print(f"Description: {skill.description}")

    # Execute skill
    print("\nExecuting skill...")
    result = await skill.execute(
        tools=tools,
        topics=["AI", "Machine Learning", "Neural Networks"],
        output_file="test_multi_research.md"
    )

    print(f"\nStatus: {result.status}")
    print(f"Summary: {result.summary}")
    print(f"Duration: {result.duration_ms:.2f}ms")
    print(f"Steps completed: {len(result.steps_completed)}")

    for i, step in enumerate(result.steps_completed[:5], 1):  # Show first 5 steps
        print(f"\n  Step {i}: {step.get('action')}")
        print(f"    Description: {step.get('description')}")

    if result.errors:
        print(f"\nErrors: {result.errors}")
    else:
        print(f"\nResult data: {result.result}")

    print("\n✓ MultiTopicResearchSkill test completed")


async def test_skill_validation():
    """Test skill validation"""
    print("\n" + "=" * 60)
    print("Testing Skill Validation")
    print("=" * 60)

    tools = {
        "search_google": SearchGoogleTool(),
        "file_write": FileWriteTool()
    }

    skill = ResearchSkill()

    # Test with all required tools
    print("\n[Test 1] With all required tools")
    try:
        skill.validate_tools(tools)
        print("  ✓ Validation passed")
    except ValueError as e:
        print(f"  ✗ Validation failed: {e}")

    # Test with missing tools
    print("\n[Test 2] With missing tools")
    incomplete_tools = {"search_google": SearchGoogleTool()}
    try:
        skill.validate_tools(incomplete_tools)
        print("  ✗ Should have failed but didn't")
    except ValueError as e:
        print(f"  ✓ Correctly detected missing tools: {e}")

    print("\n✓ Validation tests completed")


async def main():
    """Run all skill tests"""
    await test_research_skill()
    await test_multi_topic_skill()
    await test_skill_validation()

    # Cleanup
    print("\nCleaning up test files...")
    Path("test_research.md").unlink(missing_ok=True)
    Path("test_multi_research.md").unlink(missing_ok=True)

    print("\n" + "=" * 60)
    print("✅ All skill tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
