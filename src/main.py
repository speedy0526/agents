"""
Minimal Agent System - Main Entry Point
Model + Tools + Skills + Loop + Context Engineering
"""

import asyncio
from .agent import MinimalAgent
from .tools import SearchGoogleTool, FileReadTool, FileWriteTool
from .skills import ResearchSkill, MultiTopicResearchSkill


async def main():
    """Run minimal agent with skills"""

    # Create tools
    tools = [
        SearchGoogleTool(),
        FileReadTool(),
        FileWriteTool()
    ]

    # Create skills
    skills = [
        ResearchSkill(),
        MultiTopicResearchSkill()
    ]

    # Create agent with tools and skills
    agent = MinimalAgent(
        tools=tools,
        skills=skills
    )

    # Example 1: Use skill directly
    print("\n" + "="*60)
    print("Example 1: Research a single topic using skill")
    print("="*60)
    result = await agent.run("Research 'artificial intelligence' and save findings", max_steps=5)
    print(f"\nResult: {result}")

    # Clear context for next example
    agent.clear_context()

    # Example 2: Research multiple topics
    print("\n" + "="*60)
    print("Example 2: Research multiple topics")
    print("="*60)
    result = await agent.run(
        "Research these topics: 'machine learning', 'neural networks', 'deep learning'",
        max_steps=8
    )
    print(f"\nResult: {result}")


if __name__ == "__main__":
    asyncio.run(main())
