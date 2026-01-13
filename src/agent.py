"""
Minimal Agent System
Core Agent with Model + Tools + Loop + Context Engineering + Skills
"""

import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .llm import LLMClient
from .context import ContextManager
from .skills import SkillManager


class Thought(BaseModel):
    """Agent thought"""
    reasoning: str = Field(description="Current reasoning")
    next_action: str = Field(description="Next action: 'use_tool' or 'finish'")
    tool_name: Optional[str] = Field(default=None, description="Tool to use")
    tool_parameters: Optional[Dict[str, Any]] = Field(default=None, description="Tool parameters")


class MinimalAgent:
    """
    Minimal agent with model, tools, skills, loop, and context engineering

    Skills are prompt-based workflows managed by the SkillManager (meta-tool):
    - Skills are defined as SKILL.md files with prompt instructions
    - SkillManager is a tool that manages all available skills
    - When invoked, skills inject their prompts into the conversation
    - Skills follow Claude Agent Skills architecture
    """

    def __init__(
        self,
        tools: List[Any],
        skills_dirs: Optional[List[str]] = None,
        workspace_dir: str = "workspace"
    ):
        self.llm = LLMClient()

        # Initialize tools
        self.tools = {tool.name: tool for tool in tools}

        # Initialize skill manager (meta-tool)
        self.skill_manager = SkillManager(skills_dirs=skills_dirs)

        # Add skill manager as a tool
        self.tools["skill"] = self.skill_manager

        # Initialize context manager
        self.context = ContextManager(max_context_length=8000, workspace_dir=workspace_dir)

        # Initialize with system prompt
        self.context.add_system_prompt(self.get_system_prompt())
        self.context._save_session()

    def get_system_prompt(self) -> str:
        """
        Get system prompt (stable for KV-cache)

        Includes:
        - Tool descriptions (including Skill tool)
        - Usage guidelines
        """
        prompt_parts = ["You are a helpful AI agent."]

        # Add tools (including skill as a tool)
        if self.tools:
            prompt_parts.append("\n## Available Tools\n")
            for name, tool in self.tools.items():
                if name == "skill":
                    # Special formatting for skill tool to emphasize it's the way to access skills
                    prompt_parts.append(f"- {name}: {tool.description}")
                    prompt_parts.append(f"  IMPORTANT: To use a skill, call the 'skill' tool with the skill name as the 'command' parameter.")
                    prompt_parts.append(f"  Available skills: {', '.join(self.skill_manager.get_skill_names()) or 'None'}")
                else:
                    prompt_parts.append(f"- {name}: {tool.description}")

        # Add guidelines
        prompt_parts.append(f"""

## Guidelines

1. Use tools to accomplish tasks efficiently.
2. **CRITICAL**: Skills (like 'research', 'pdf') are NOT direct tools. You must call the 'skill' tool with command='skill-name' to use them.
3. Example: To use the research skill, set next_action='use_tool', tool_name='skill', tool_parameters={{'command': 'research'}}
4. When you need to use a regular tool, respond with tool name and parameters.
5. When task is complete, set next_action to 'finish' and provide a final answer.
6. If a tool fails, try a different approach.
7. Learn from errors - they are part of context for improvement.
8. Use tools efficiently - avoid unnecessary calls.
9. Keep user's goals in mind throughout the task.

## Action Format

- For skills: Set next_action='use_tool', tool_name='skill', tool_parameters={{'command': 'skill-name'}}
- For regular tools: Set next_action='use_tool', specify tool_name and tool_parameters
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
        """
        Execute tool and log to context

        Special handling for 'skill' tool:
        - Invokes skill manager to get context messages
        - Injects messages into conversation
        - Does NOT complete immediately, continues loop with enhanced context
        """
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        # Special handling for skill tool
        if tool_name == "skill":
            command = parameters.get("command")
            if not command:
                raise ValueError("Skill tool requires 'command' parameter")

            # Get current user request from context
            # Use entries to get the last user message
            user_entry = next(
                (e for e in reversed(self.context.entries) if e.role == "user"),
                None
            )
            user_request = user_entry.content if user_entry else ""

            # Invoke skill to get context messages
            context_messages, error = self.skill_manager.invoke(
                command=command,
                user_request=user_request,
                tools_available=self.tools
            )

            if error:
                # Log skill invocation error
                self.context.add_tool_result(
                    tool_name=tool_name,
                    result=error,
                    is_error=True
                )
                raise ValueError(error)

            # Inject skill context messages into conversation
            if context_messages:
                for msg in context_messages:
                    if msg.get("meta"):
                        # Hidden message (skill prompt)
                        self.context.add_system_prompt(msg["content"])
                    else:
                        # User-visible message
                        self.context.add_assistant_response(msg["content"])

            # Return early - skill injection doesn't complete the tool call
            # The agent will continue in the enhanced context
            return None

        # Normal tool execution
        result = await tool.execute(**parameters)

        # Log to context (preserve errors for learning)
        self.context.add_tool_result(
            tool_name=tool_name,
            result=result.summary if result.status == "success" else result.error,
            is_error=result.status != "success"
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
        print(f"Tools: {len(self.tools)} (including skill manager)")
        print(f"Available skills: {', '.join(self.skill_manager.get_skill_names()) or 'None'}")
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
                        if result is not None:
                            # Skip logging for skill tool (returns None)
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

        return "Maximum steps reached. Task incomplete."

    def get_context_summary(self) -> str:
        """Get current context summary"""
        return self.context.get_summary()

    def clear_context(self):
        """Clear context (keep system prompt)"""
        self.context.clear()
