"""
Skill Manager (Meta-Tool)
Manages all skills as a single tool

This is the "Skill" tool (capital S) that manages all individual skills.
Based on Claude Agent Skills architecture.
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path

from .models import Skill, SkillRegistry, SkillInvocation
from .loader import SkillLoader
from .context import SkillContextManager


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
        builtin_skills_dir: Optional[str] = None
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
            "required": ["command"]
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
        self,
        command: str,
        user_request: str,
        tools_available: Dict[str, Any]
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
            return None, f"Skill '{command}' cannot be invoked by model (manual invocation only)"

        # Filter tools based on skill's allowed_tools
        filtered_tools = self.context_manager.filter_allowed_tools(skill, tools_available)

        # Validate required tools are available
        missing_tools = set(skill.allowed_tools) - set(filtered_tools.keys())
        if missing_tools:
            return None, f"Skill '{command}' requires tools that are not available: {missing_tools}"

        # Create context messages
        context_messages = self.context_manager.get_context_messages(
            skill, user_request, filtered_tools
        )

        return context_messages, None

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
                "has_scripts": bool(skill._scripts),
                "has_references": bool(skill._references),
                "has_assets": bool(skill._assets),
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
