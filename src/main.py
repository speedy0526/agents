"""
Minimal Agent System - Main Entry Point
Model + Tools + Skills + Loop + Context Engineering + Agent-SubAgent Architecture
"""

import asyncio
from pathlib import Path
from .agent import MinimalAgent
from .tools import SearchGoogleTool, FileReadTool, FileWriteTool


async def main():
    """Run minimal agent with Agent-SubAgent architecture"""

    # Get project root directory
    project_root = Path(__file__).parent.parent.absolute()

    # Define skills directories
    skills_dirs = [
        str(project_root / "skills"),  # Project skills
    ]

    # Create tools
    tools = [
        SearchGoogleTool(),
        FileReadTool(),
        FileWriteTool()
    ]

    # Create agent with tools and skills directories
    agent = MinimalAgent(
        tools=tools,
        skills_dirs=skills_dirs
    )

    # Display available skills
    print("\n" + "="*60)
    print("Available Skills")
    print("="*60)
    for skill_name in agent.skill_manager.get_skill_names():
        skill = agent.skill_manager.get_skill(skill_name)
        print(f"  • {skill_name}: {skill.description}")
        print(f"    Required tools: {', '.join(skill.allowed_tools) or 'None'}")

    result = await agent.run(
        "Perform structured decision research about 'digit product 2.0' and compile a report",
        max_steps=50
    )

    print(f"\nResult: {result}")

    # Clear context for next example
    agent.clear_context()
 

if __name__ == "__main__":
    asyncio.run(main())
