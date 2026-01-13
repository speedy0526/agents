"""
Minimal Agent System
Core Agent with Model + Tools + Loop + Context Engineering + Skills
"""

import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .llm import LLMClient
from .context import ContextManager


class Thought(BaseModel):
    """Agent thought"""
    reasoning: str = Field(description="Current reasoning")
    next_action: str = Field(description="Next action: 'use_tool', 'use_skill', or 'finish'")
    tool_name: Optional[str] = Field(default=None, description="Tool to use")
    tool_parameters: Optional[Dict[str, Any]] = Field(default=None, description="Tool parameters")
    skill_name: Optional[str] = Field(default=None, description="Skill to use")
    skill_parameters: Optional[Dict[str, Any]] = Field(default=None, description="Skill parameters")


class MinimalAgent:
    """
    Minimal agent with model, tools, skills, loop, and context engineering

    Skills are higher-level abstractions that:
    - Combine multiple tools
    - Execute multi-step workflows
    - Provide clear input/output contracts
    """

    def __init__(
        self,
        tools: List[Any],
        skills: Optional[List[Any]] = None,
        workspace_dir: str = "workspace"
    ):
        self.llm = LLMClient()
        self.tools = {tool.name: tool for tool in tools}
        self.skills = {skill.name: skill for skill in (skills or [])}
        self.context = ContextManager(max_context_length=8000, workspace_dir=workspace_dir)

        # Initialize with system prompt
        self.context.add_system_prompt(self.get_system_prompt())
        self.context._save_session()

    def get_system_prompt(self) -> str:
        """
        Get system prompt (stable for KV-cache)

        Includes:
        - Tool descriptions
        - Skill descriptions
        - Usage guidelines
        """
        prompt_parts = ["You are a helpful AI agent."]

        # Add tools
        if self.tools:
            prompt_parts.append("\n## Available Tools\n")
            tools_desc = "\n".join([
                f"- {name}: {tool.description}"
                for name, tool in self.tools.items()
            ])
            prompt_parts.append(tools_desc)

        # Add skills
        if self.skills:
            prompt_parts.append("\n## Available Skills\n")
            prompt_parts.append("Skills are higher-level operations that combine multiple tools:\n")
            skills_desc = "\n".join([
                f"- {name}: {skill.description}\n  Required tools: {', '.join(skill.required_tools)}"
                for name, skill in self.skills.items()
            ])
            prompt_parts.append(skills_desc)

        # Add guidelines
        prompt_parts.append(f"""

## Guidelines

1. Prefer using skills when they match your task - they're optimized for common workflows.
2. When you need to use a tool, respond with tool name and parameters.
3. When you need to use a skill, respond with skill name and parameters.
4. When task is complete, set next_action to 'finish' and provide a final answer.
5. If a tool or skill fails, try a different approach.
6. Learn from errors - they are part of context for improvement.
7. Use tools and skills efficiently - avoid unnecessary calls.
8. Keep user's goals in mind throughout the task.

## Action Format

- For tools: Set next_action='use_tool', specify tool_name and tool_parameters
- For skills: Set next_action='use_skill', specify skill_name and skill_parameters
- To finish: Set next_action='finish' and provide final answer
""")

        return "\n".join(prompt_parts)

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get tools schema for LLM (logit masking support)"""
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            }
            for name, tool in self.tools.items()
        ]

    def get_skills_schema(self) -> List[Dict[str, Any]]:
        """Get skills schema for LLM"""
        return [
            {
                "type": "function",
                "function": {
                    "name": f"skill_{name}",
                    "description": f"[SKILL] {skill.description}\nRequired tools: {', '.join(skill.required_tools)}",
                    "parameters": skill.parameters
                }
            }
            for name, skill in self.skills.items()
        ]

    async def think(self) -> Thought:
        """
        Generate thought using current context

        Manus principles:
        - Use messages from ContextManager (KV-cache friendly)
        - Include goals at end (attention guidance)
        """
        messages = self.context.get_messages(include_goals=True)

        response = await self.llm.generate_structured(messages, Thought)
        return response

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:  # noqa: ANN401
        """Execute tool and log to context"""
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        result = await tool.execute(**parameters)

        # Log to context (preserve errors for learning)
        self.context.add_tool_result(
            tool_name=tool_name,
            result=result.summary if result.status == "success" else result.error,
            is_error=result.status != "success"
        )

        return result

    async def execute_skill(self, skill_name: str, parameters: Dict[str, Any]):  # noqa: ANN401
        """Execute skill and log to context"""
        skill = self.skills.get(skill_name)
        if not skill:
            raise ValueError(f"Skill not found: {skill_name}")

        # Validate required tools
        missing_tools = set(skill.required_tools) - set(self.tools.keys())
        if missing_tools:
            raise ValueError(f"Skill '{skill_name}' requires tools: {missing_tools}")

        result = await skill.execute(tools=self.tools, **parameters)

        # Log skill execution to context
        self.context.add_assistant_response(
            f"Executed skill '{skill_name}'\n"
            f"Status: {result.status}\n"
            f"Steps completed: {len(result.steps_completed)}\n"
            f"Summary: {result.summary}"
        )

        if result.errors:
            for error in result.errors:
                self.context.add_tool_result(
                    tool_name=f"skill_{skill_name}",
                    result=error,
                    is_error=True
                )

        return result

    async def run(self, user_request: str, max_steps: int = 10) -> str:
        """
        Run agent loop with context management

        Manus principles:
        - Add user request to context
        - Think -> Act -> Observe -> Repeat
        - Compress context when needed
        - Preserve system prompt (stable prefix)
        """
        # Add user request
        self.context.add_user_request(user_request)

        # Set initial goals from request
        self.context.set_goals([f"Complete: {user_request}"])

        print(f"\n{'='*60}")
        print(f"Task: {user_request}")
        print(f"{'='*60}")
        print(f"Tools: {len(self.tools)}, Skills: {len(self.skills)}")
        print(self.context.get_summary())

        for step in range(max_steps):
            # Compress context if needed
            self.context.compress_if_needed()

            # Think
            thought = await self.think()
            self.context.add_thought(thought.reasoning)

            print(f"\n[Step {step + 1}] Thought: {thought.reasoning}")

            # Check if finished
            if thought.next_action == "finish":
                self.context.add_assistant_response(thought.reasoning)
                return thought.reasoning

            # Execute tool
            if thought.next_action == "use_tool":
                if thought.tool_name and thought.tool_parameters:
                    try:
                        result = await self.execute_tool(thought.tool_name, thought.tool_parameters)
                        print(f"  Tool: {thought.tool_name}")
                        print(f"  Result: {result.summary}")
                    except Exception as e:
                        # Log error to context (Manus: preserve errors)
                        self.context.add_tool_result(
                            tool_name=thought.tool_name,
                            result=str(e),
                            is_error=True
                        )
                        print(f"  Tool failed: {thought.tool_name}")
                        print(f"  Error: {e}")

            # Execute skill
            elif thought.next_action == "use_skill":
                if thought.skill_name and thought.skill_parameters:
                    try:
                        result = await self.execute_skill(thought.skill_name, thought.skill_parameters)
                        print(f"  Skill: {thought.skill_name}")
                        print(f"  Status: {result.status}")
                        print(f"  Summary: {result.summary}")
                        print(f"  Steps: {len(result.steps_completed)}")
                        if result.duration_ms:
                            print(f"  Duration: {result.duration_ms:.2f}ms")
                    except Exception as e:
                        # Log error to context
                        self.context.add_tool_result(
                            tool_name=f"skill_{thought.skill_name}",
                            result=str(e),
                            is_error=True
                        )
                        print(f"  Skill failed: {thought.skill_name}")
                        print(f"  Error: {e}")

        return "Maximum steps reached. Task incomplete."

    def get_context_summary(self) -> str:
        """Get current context summary"""
        return self.context.get_summary()

    def clear_context(self):
        """Clear context (keep system prompt)"""
        self.context.clear()
