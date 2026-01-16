"""
Skill Manager (Meta-Tool)
Manages all skills as a single tool

This is the "Skill" tool (capital S) that manages all individual skills.
Based on Claude Agent Skills architecture.
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path

from .models import Skill, SkillRegistry
from .loader import SkillLoader
from .context import SkillContextManager
from ..subagents.skill_result import SkillResult


class SkillManager:
    """
    Skill Manager - The meta-tool that manages all skills

    This is a tool that:
    - Appears in the tools list as "Skill"
    - Manages a registry of all available skills
    - Handles skill invocation and context injection
    - Implements progressive disclosure

    Architecture:
    - Discovers skills from multiple sources (user, project, built-in)
    - Provides skill descriptions to LLM for matching
    - Injects skill prompts when invoked
    - Manages tool permissions per skill
    """

    def __init__(
        self,
        skills_dirs: Optional[List[str]] = None,
        builtin_skills_dir: Optional[str] = None,
    ):
        """
        Initialize skill manager

        Args:
            skills_dirs: List of directories to scan for skills
            builtin_skills_dir: Directory containing built-in skills
        """
        self.loader = SkillLoader()
        self.context_manager = SkillContextManager()
        self.registry = SkillRegistry()

        # Default skill directories
        self.skills_dirs = skills_dirs or [
            str(Path.cwd() / "skills"),  # Project skills
            str(Path.home() / ".agent" / "skills"),  # User skills
        ]

        # Built-in skills directory
        self.builtin_skills_dir = builtin_skills_dir

        # Load all skills
        self._load_all_skills()

    @property
    def name(self) -> str:
        """Tool name (appears in tools list)"""
        return "skill"

    @property
    def description(self) -> str:
        """
        Tool description (shown to LLM for matching)

        Includes list of available skills with brief descriptions
        """
        skill_list = []
        for skill_name, skill in self.registry.skills.items():
            # Format: skill_name: description [tools: tool1, tool2]
            tools_info = ""
            if skill.allowed_tools:
                tools_info = f" [tools: {', '.join(skill.allowed_tools)}]"
            skill_list.append(f"  - {skill_name}: {skill.description}{tools_info}")

        if not skill_list:
            return "Manage specialized workflows (no skills loaded)"

        return f"""Manage specialized workflows that combine multiple tools.

Available skills:
{chr(10).join(skill_list)}

When you need to use a skill, call this tool with the skill name as the 'command' parameter."""

    @property
    def parameters(self) -> Dict[str, Any]:
        """Tool parameters schema"""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": f"Skill name to invoke. Available skills: {', '.join(self.registry.get_skill_names())}",
                }
            },
            "required": ["command"],
        }

    def _load_all_skills(self):
        """Load skills from all configured directories"""
        # Load from project and user directories
        for skills_dir in self.skills_dirs:
            skills = self.loader.load_skills_from_directory(skills_dir)
            for skill in skills:
                self.registry.add_skill(skill)

        # Load from built-in directory
        if self.builtin_skills_dir:
            skills = self.loader.load_skills_from_directory(self.builtin_skills_dir)
            for skill in skills:
                self.registry.add_skill(skill)

        print(f"Loaded {len(self.registry.skills)} skills:")
        for skill_name in self.registry.get_skill_names():
            print(f"  - {skill_name}")

    def get_skill_names(self) -> List[str]:
        """Get list of all available skill names"""
        return self.registry.get_skill_names()

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get skill by name"""
        return self.registry.get_skill(name)

    def can_invoke_skill(self, skill_name: str) -> bool:
        """
        Check if a skill can be invoked

        Skills with disable_model_invocation: true can only be manually invoked
        """
        skill = self.get_skill(skill_name)
        if not skill:
            return False

        return not skill.disable_model_invocation

    def invoke(
        self, command: str, user_request: str, tools_available: Dict[str, Any]
    ) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Invoke a skill

        This is called when the LLM decides to use a skill.

        Args:
            command: Skill name to invoke
            user_request: Original user request
            tools_available: Available tools

        Returns:
            Tuple of (context_messages, error)
            - context_messages: List of messages to inject (2 messages)
            - error: Error message if invocation failed
        """
        # Get the skill
        skill = self.get_skill(command)
        if not skill:
            return None, f"Skill not found: {command}"

        # Check if skill can be invoked by model
        if skill.disable_model_invocation:
            return (
                None,
                f"Skill '{command}' cannot be invoked by model (manual invocation only)",
            )

        # Filter tools based on skill's allowed_tools
        filtered_tools = self.context_manager.filter_allowed_tools(
            skill, tools_available
        )

        # Validate required tools are available
        missing_tools = set(skill.allowed_tools) - set(filtered_tools.keys())
        if missing_tools:
            return (
                None,
                f"Skill '{command}' requires tools that are not available: {missing_tools}",
            )

        # Create context messages
        context_messages = self.context_manager.get_context_messages(
            skill, user_request, filtered_tools
        )

        return context_messages, None

    async def execute_skill(
        self, command: str, parameters: Dict[str, Any]
    ) -> SkillResult:
        """
        Execute a skill by running an LLM loop with skill prompt

        This method implements the actual skill execution logic:
        1. Load skill prompt from SKILL.md
        2. Create a mini-agent that follows the skill's workflow
        3. Execute tool calls as directed by the skill
        4. Return results when skill completes

        Args:
            command: Skill name to execute
            parameters: Skill parameters (tools_available, user_request)

        Returns:
            SkillResult with execution results
        """
        from ..llm import LLMClient
        from ..context import ContextManager
        from datetime import datetime

        # Get skill
        skill = self.get_skill(command)
        if not skill:
            return SkillResult(
                success=False,
                confirmation=f"Skill not found: {command}",
                summary=f"Skill '{command}' not available",
            )

        user_request = parameters.get("user_request", "")
        tools_available = parameters.get("tools_available", {})

        # Filter tools based on skill's allowed_tools
        filtered_tools = self.context_manager.filter_allowed_tools(
            skill, tools_available
        )

        # Validate required tools
        missing_tools = set(skill.allowed_tools) - set(filtered_tools.keys())
        if missing_tools:
            return SkillResult(
                success=False,
                confirmation=f"Missing required tools",
                summary=f"Skill '{command}' requires tools that are not available: {missing_tools}",
                errors=[f"Missing tool: {t}" for t in missing_tools],
            )

        print(f"\n{'=' * 60}")
        print(f"🎯 Skill Execution: {command}")
        print(f"{'=' * 60}")
        print(f"   Request: {user_request}")
        print(f"   Available tools: {list(filtered_tools.keys())}")
        print(f"{'=' * 60}\n")

        # Create a context for skill execution
        context = ContextManager(
            max_context_length=20000,
            workspace_dir="workspace",
            auto_save=False,  # Don't save skill-specific context to disk
        )

        # Add skill prompt as system message
        context.add_system_prompt(skill.content)

        # Add context variables 
        context_vars = f"""
---
## Context Variables

Base directory: {skill.base_dir}
User request: {user_request}
Available tools: {", ".join(filtered_tools.keys())}

Analyze the task and use available tools to complete it.Use the available tools as needed to fulfill the user's request.

## Task Completion

You should complete the task by:
1. Using the available tools to gather information or perform actions
2. Producing tangible results (saving files, collecting data, compiling reports)
3. When finished with tangible results, clearly indicate completion

Do NOT continue indefinitely. Once you have:
- Saved a file with content, OR
- Gathered and compiled information, OR
- Otherwise fulfilled the user's request

Then clearly state: "Task complete" or similar.
"""
        context.add_system_prompt(context_vars)

        # Initialize result tracking
        tool_calls = []
        outputs = []
        files_saved = []
        errors = []
        execution_steps = 0
        max_skill_steps = 20  # Prevent infinite loops

        llm = LLMClient()
        start_time = datetime.now()

        # Skill execution loop
        while execution_steps < max_skill_steps:
            execution_steps += 1

            # Get messages (system prompt + tool results)
            messages = context.get_messages(include_goals=False)

            # Prompt LLM with skill instructions
            try:
                print(f"\n{'=' * 60}")
                print(f"🤖 Skill Step {execution_steps}")
                print(f"{'=' * 60}")

                # Use streaming for skill LLM calls
                print(f"\n💭 Skill AI Thinking...")
                response = await llm.chat(messages, stream=True)
                
                # Handle streaming response (returns dict with choices key)
                if isinstance(response, dict):
                    response_text = response["choices"][0]["message"]["content"]
                else:
                    # Non-streaming response (for backward compatibility)
                    response_text = response.choices[0].message.content
                
                print(f"\n🎯 AI Response: {response_text[:200]}...")
                print(f"{'=' * 60}\n")

                # Add AI response to context
                context.add_assistant_response(response_text)

                # Check if skill indicates completion
                if self._is_skill_complete(response_text):
                    print(f"✅ Skill '{command}' completed")
                    break

                # Extract and execute tool calls from response
                # This is a simplified extraction - in production, use proper tool calling
                tool_calls_made = await self._execute_skill_tools(
                    response_text, filtered_tools, context
                )

                if tool_calls_made:
                    tool_calls.extend(tool_calls_made)
                    # Check if we produced tangible results (files, data)
                    for call in tool_calls_made:
                        if call.get("tool_name") == "file_write" and call.get(
                            "success"
                        ):
                            files_saved.append(
                                call.get("result", {}).get("filepath", "")
                            )
                else:
                    # No tool calls made, might be asking for more thinking
                    # or indicating completion
                    if self._is_skill_complete(response_text):
                        print(f"✅ Skill '{command}' completed")
                        break
                    # Continue to next iteration (AI will call tools next)

            except Exception as e:
                error_msg = f"Step {execution_steps}: {str(e)}"
                errors.append(error_msg)
                print(f"❌ {error_msg}")

                # If too many errors, abort
                if len(errors) >= 3:
                    break

        # Compile final result
        execution_time = (datetime.now() - start_time).total_seconds()

        # Determine success
        success = len(errors) < 3 and (len(files_saved) > 0 or len(outputs) > 0)

        return SkillResult(
            success=success,
            confirmation=f"Skill '{command}' execution {'complete' if success else 'failed'}",
            summary=self._generate_skill_summary(
                command, tool_calls, files_saved, errors
            ),
            details=f"Executed {len(tool_calls)} tool calls in {execution_steps} steps",
            items=tool_calls,
            file_paths=files_saved if files_saved else None,
            count=len(tool_calls),
            tokens_used=None,  # Would need to track from llm calls
            metadata={
                "skill_name": command,
                "user_request": user_request,
                "execution_steps": execution_steps,
                "tool_calls": len(tool_calls),
                "files_created": len(files_saved),
            },
            errors=errors if errors else None,
        )

    def _is_skill_complete(self, response: str) -> bool:
        """Check if skill response indicates completion"""
        completion_indicators = [
            "task complete",
            "workflow complete",
            "skill complete",
            "finished",
            "done",
            "completed successfully",
            "file saved",
            "report generated",
        ]
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in completion_indicators)

    async def _execute_skill_tools(
        self, response: str, tools: Dict[str, Any], context: "ContextManager"
    ) -> List[Dict[str, Any]]:
        """
        Extract and execute tool calls from AI response

        This is a simplified implementation that uses regex to find tool calls.
        Production implementation should use structured tool calling.

        Args:
            response: AI response text
            tools: Available tools dictionary
            context: Context manager to add results to

        Returns:
            List of executed tool call records
        """
        import re
        from json import JSONDecodeError

        tool_calls = []

        # Try to extract tool calls using common patterns
        # Pattern 1: "Use tool_name" or "Calling tool_name"
        tool_patterns = [
            r"calling\s+(\w+)\s*\(",
            r"use\s+(\w+)\s+with",
            r"execute\s+(\w+)",
            r"calling\s+the\s+(\w+)\s+tool",
            r"(file_write|search_google)\(",
        ]

        for pattern in tool_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                tool_name = match.group(1).strip()

                # Try to extract parameters
                # Look for JSON-like structure after the tool name
                param_pattern = r"\{.*?\}"
                param_match = re.search(
                    param_pattern, response[match.end() : match.end() + 200]
                )

                parameters = {}
                if param_match:
                    try:
                        import json

                        parameters = json.loads(param_match.group(0))
                    except (JSONDecodeError, json.JSONDecodeError):
                        # Fallback: try to find filepath parameter
                        filepath_match = re.search(
                            r'filepath["\s:]+\s*["\']([^"\']+)["\']',
                            response,
                            re.IGNORECASE,
                        )
                        if filepath_match:
                            parameters["filepath"] = filepath_match.group(1)

                # Execute tool if available
                if tool_name in tools:
                    try:
                        result = await tools[tool_name].execute(**parameters)
                        result_obj = {
                            "tool_name": tool_name,
                            "parameters": parameters,
                            "success": True,
                            "result": {
                                "summary": result.summary
                                if hasattr(result, "summary")
                                else str(result),
                                "status": result.status
                                if hasattr(result, "status")
                                else "success",
                            },
                        }

                        # Add tool result to context
                        context.add_tool_result(
                            tool_name=tool_name,
                            result=result.summary
                            if hasattr(result, "summary")
                            else str(result),
                            is_error=hasattr(result, "status")
                            and result.status != "success",
                        )

                        tool_calls.append(result_obj)
                        print(f"✅ Tool '{tool_name}' executed")

                    except Exception as e:
                        error_record = {
                            "tool_name": tool_name,
                            "parameters": parameters,
                            "success": False,
                            "error": str(e),
                        }
                        tool_calls.append(error_record)
                        print(f"❌ Tool '{tool_name}' failed: {e}")

                # Break after first tool call to avoid duplicate processing
                break

        return tool_calls

    def _generate_skill_summary(
        self,
        skill_name: str,
        tool_calls: List[Dict[str, Any]],
        files_saved: List[str],
        errors: List[str],
    ) -> str:
        """Generate a summary of skill execution"""
        parts = [f"Skill '{skill_name}' execution"]

        if files_saved:
            parts.append(
                f"\n✓ Created {len(files_saved)} file(s): {', '.join(files_saved)}"
            )

        if tool_calls:
            successful = sum(1 for c in tool_calls if c.get("success"))
            parts.append(
                f"\n✓ Executed {successful}/{len(tool_calls)} tool calls successfully"
            )

        if errors:
            parts.append(f"\n✗ Encountered {len(errors)} errors")

        return "\n".join(parts)

    def get_all_skills_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all skills

        Useful for debugging and listing
        """
        skills_info = []

        for skill_name, skill in self.registry.skills.items():
            info = {
                "name": skill.name,
                "description": skill.description,
                "version": skill.version,
                "allowed_tools": skill.allowed_tools,
                "model": skill.model,
                "disable_model_invocation": skill.disable_model_invocation,
                "base_dir": skill.base_dir,
                "has_scripts": bool(skill.scripts),
                "has_references": bool(skill.references),
                "has_assets": bool(skill.assets),
            }
            skills_info.append(info)

        return skills_info

    def reload_skills(self):
        """
        Reload all skills from disk

        Useful when skills are added/modified
        """
        self.registry = SkillRegistry()
        self._load_all_skills()
