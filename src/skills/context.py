"""
Skill Context Manager
Handles context injection when invoking skills
"""

from typing import Dict, Any, Optional, List
from pathlib import Path

from .models import Skill, SkillContext


class SkillContextManager:
    """
    Manage context injection for skill invocation

    Based on Claude Skills principles:
    - Progressive disclosure: only show needed information
    - Context modification: inject instructions dynamically
    - Separate user-visible vs hidden content
    """

    def __init__(self):
        pass

    def create_skill_context(
        self,
        skill: Skill,
        user_request: str,
        tools_available: Dict[str, Any]
    ) -> SkillContext:
        """
        Create context for skill invocation

        This context will be injected into the conversation as:
        1. User-visible message (meta information)
        2. Hidden message (full skill prompt, is_meta: true)

        Args:
            skill: The skill being invoked
            user_request: The original user request
            tools_available: Dictionary of available tools

        Returns:
            SkillContext object ready for injection
        """
        # User-visible message (minimal information)
        user_message = self._create_user_message(skill, user_request)

        # Hidden full prompt (detailed instructions)
        skill_prompt = self._create_skill_prompt(skill, user_request, tools_available)

        # Create context
        context = SkillContext(
            skill_name=skill.name,
            skill_description=skill.description,
            allowed_tools=skill.allowed_tools,
            model_preference=skill.model,
            user_message=user_message,
            skill_prompt=skill_prompt,
            is_meta=True,
            available_scripts=skill._scripts or [],
            available_references=skill._references or [],
            available_assets=skill._assets or [],
        )

        return context

    def _create_user_message(self, skill: Skill, user_request: str) -> str:
        """
        Create user-visible message

        This is what the user sees in the conversation.
        Minimal information to avoid overwhelming the user.

        Args:
            skill: The skill being invoked
            user_request: Original user request

        Returns:
            User-visible message
        """
        parts = [
            f"The {skill.name} skill is now active.",
        ]

        if skill._scripts:
            parts.append(f"Available scripts: {', '.join(skill._scripts)}")

        return " ".join(parts)

    def _create_skill_prompt(
        self,
        skill: Skill,
        user_request: str,
        tools_available: Dict[str, Any]
    ) -> str:
        """
        Create full skill prompt for Claude

        This is hidden from the user but sent to Claude.
        Contains detailed instructions and context.

        Args:
            skill: The skill being invoked
            user_request: Original user request
            tools_available: Available tools

        Returns:
            Full skill prompt
        """
        prompt_parts = []

        # Add skill content (the core instructions)
        prompt_parts.append(skill.content)

        # Add context variables
        prompt_parts.append("\n---\n")
        prompt_parts.append("## Context\n")
        prompt_parts.append(f"Base directory: {skill.base_dir}\n")
        prompt_parts.append(f"User request: {user_request}\n")

        # Add available tools
        if skill.allowed_tools:
            prompt_parts.append("\n## Available Tools\n")
            for tool_name in skill.allowed_tools:
                if tool_name in tools_available:
                    tool = tools_available[tool_name]
                    prompt_parts.append(f"- {tool_name}: {tool.description}\n")
                else:
                    prompt_parts.append(f"- {tool_name}: (not available)\n")

        # Add resource references
        if skill._scripts:
            prompt_parts.append("\n## Available Scripts\n")
            prompt_parts.append("You can execute scripts in the scripts/ directory using the Bash tool.\n")
            prompt_parts.append(f"Scripts: {', '.join(skill._scripts)}\n")

        if skill._references:
            prompt_parts.append("\n## Available References\n")
            prompt_parts.append("You can read reference files using the Read tool.\n")
            prompt_parts.append(f"References: {', '.join(skill._references)}\n")

        if skill._assets:
            prompt_parts.append("\n## Available Assets\n")
            prompt_parts.append(f"Assets: {', '.join(skill._assets)}\n")

        return "".join(prompt_parts)

    def load_reference_content(self, skill: Skill, reference_name: str) -> Optional[str]:
        """
        Load content from a reference file

        Used when the skill needs to load detailed documentation

        Args:
            skill: The skill
            reference_name: Name of the reference file

        Returns:
            File content or None
        """
        if not skill.references_dir:
            return None

        ref_path = Path(skill.references_dir) / reference_name

        try:
            with open(ref_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None

    def get_asset_path(self, skill: Skill, asset_name: str) -> Optional[str]:
        """
        Get path to an asset file

        Assets are referenced but not loaded into context

        Args:
            skill: The skill
            asset_name: Name of the asset file

        Returns:
            Absolute path to asset or None
        """
        if not skill.assets_dir:
            return None

        asset_path = Path(skill.assets_dir) / asset_name

        if asset_path.exists():
            return str(asset_path.absolute())

        return None

    def filter_allowed_tools(
        self,
        skill: Skill,
        tools_available: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Filter available tools based on skill's allowed_tools

        Implements the principle of least privilege

        Args:
            skill: The skill
            tools_available: All available tools

        Returns:
            Filtered dictionary of allowed tools
        """
        if not skill.allowed_tools:
            # If no restriction, return all tools
            return tools_available

        filtered_tools = {}
        for tool_name in skill.allowed_tools:
            if tool_name in tools_available:
                filtered_tools[tool_name] = tools_available[tool_name]

        return filtered_tools

    def get_context_messages(
        self,
        skill: Skill,
        user_request: str,
        tools_available: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Get messages to inject into the conversation

        Returns two messages:
        1. User-visible message (meta: false)
        2. Hidden skill prompt (meta: true, is_meta: true)

        Args:
            skill: The skill
            user_request: Original user request
            tools_available: Available tools

        Returns:
            List of message dictionaries
        """
        context = self.create_skill_context(skill, user_request, tools_available)

        messages = [
            {
                "role": "user",
                "content": context.user_message,
                "meta": False,
            },
            {
                "role": "user",
                "content": context.skill_prompt,
                "meta": True,
                "is_meta": True,
            }
        ]

        return messages
