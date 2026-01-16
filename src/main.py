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

    
    # Example 4: Test SubAgent skill execution
    print("\n" + "="*60)
    print("Test 4: SubAgent Skill Execution")
    print("="*60)
    print("Demonstrating how Agent uses SubAgent to execute skills...")
    print("\nThe agent will:")
    print("1. Recognize the need for research")
    print("2. Decide to use the 'skill' SubAgent with command='research'")
    print("3. Create SkillSubAgent with independent context")
    print("4. SkillSubAgent loads research skill prompt to its own context")
    print("5. SkillSubAgent executes in isolation")
    print("6. Agent receives result summary, context remains clean")

    result = await agent.run(
        "Search for information about 'minimal agent architecture' and compile a report",
        max_steps=10
    )
    print(f"\nResult: {result}")

    # Clear context for next example
    agent.clear_context()
 

if __name__ == "__main__":
    asyncio.run(main())
