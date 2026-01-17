"""
Skill Loader
Loads and parses SKILL.md files to create Skill objects
"""

import os
import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
import re

from .models import Skill, SkillFrontmatter


class SkillLoader:
    """
    Load skills from SKILL.md files

    Supports loading from multiple sources:
    - User skills directory
    - Project skills directory
    - Built-in skills
    - Plugin directories
    """

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir).absolute()

    def load_skill(self, skill_path: str) -> Optional[Skill]:
        """
        Load a single skill from a SKILL.md file

        Args:
            skill_path: Path to the directory containing SKILL.md

        Returns:
            Skill object or None if loading fails
        """
        skill_dir = Path(skill_path)
        skill_file = skill_dir / "SKILL.md"

        if not skill_file.exists():
            return None

        try:
            # Read the SKILL.md file
            with open(skill_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse frontmatter
            frontmatter, markdown_content = self._parse_frontmatter(content)

            if not frontmatter:
                return None

            # Create Skill object
            skill = Skill(
                name=frontmatter.name,
                description=frontmatter.description,
                version=frontmatter.version,
                allowed_tools=self._parse_tools(frontmatter.allowed_tools),
                model=frontmatter.model,
                disable_model_invocation=frontmatter.disable_model_invocation,
                content=markdown_content,
                base_dir=str(skill_dir),
                scripts_dir=str(skill_dir / "scripts") if (skill_dir / "scripts").exists() else None,
                references_dir=str(skill_dir / "references") if (skill_dir / "references").exists() else None,
                assets_dir=str(skill_dir / "assets") if (skill_dir / "assets").exists() else None,
            )

            # Load resource listings
            if skill.scripts_dir:
                skill._scripts = self._list_files(skill.scripts_dir, [".py", ".sh"])
            if skill.references_dir:
                skill._references = self._list_files(skill.references_dir, [".md", ".txt", ".pdf"])
            if skill.assets_dir:
                skill._assets = self._list_files(skill.assets_dir)

            return skill

        except Exception as e:
            print(f"Error loading skill from {skill_path}: {e}")
            return None

    def load_skills_from_directory(self, directory: str) -> List[Skill]:
        """
        Load all skills from a directory

        Each subdirectory containing a SKILL.md file is treated as a skill

        Args:
            directory: Root directory containing skill subdirectories

        Returns:
            List of loaded Skill objects
        """
        skills = []
        skill_root = Path(directory)

        if not skill_root.exists():
            return skills

        # Scan for subdirectories containing SKILL.md
        for item in skill_root.iterdir():
            if item.is_dir():
                skill_file = item / "SKILL.md"
                if skill_file.exists():
                    skill = self.load_skill(str(item))
                    if skill:
                        skills.append(skill)

        return skills

    def _parse_frontmatter(self, content: str) -> tuple[Optional[SkillFrontmatter], str]:
        """
        Parse YAML frontmatter from SKILL.md content

        Args:
            content: Full content of SKILL.md file

        Returns:
            Tuple of (SkillFrontmatter or None, markdown_content)
        """
        # Check for YAML frontmatter (between --- lines)
        frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if not match:
            return None, content

        frontmatter_yaml = match.group(1)
        markdown_content = match.group(2).strip()

        try:
            frontmatter_data = yaml.safe_load(frontmatter_yaml)
            if isinstance(frontmatter_data, dict):
                return SkillFrontmatter(**frontmatter_data), markdown_content
        except Exception as e:
            print(f"Error parsing frontmatter YAML: {e}")

        return None, content

    def _parse_tools(self, tools_str: Optional[str]) -> List[str]:
        """
        Parse allowed_tools from comma-separated string

        Args:
            tools_str: Comma-separated list of tools or None

        Returns:
            List of tool names
        """
        if not tools_str:
            return []

        return [tool.strip() for tool in tools_str.split(",") if tool.strip()]

    def _list_files(self, directory: str, extensions: Optional[List[str]] = None) -> List[str]:
        """
        List files in a directory with optional extension filter

        Args:
            directory: Directory path
            extensions: Optional list of file extensions to filter

        Returns:
            List of file paths relative to the directory
        """
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return []

            files = []
            for file_path in dir_path.iterdir():
                if file_path.is_file():
                    if extensions:
                        if file_path.suffix in extensions:
                            files.append(file_path.name)
                    else:
                        files.append(file_path.name)

            return sorted(files)

        except Exception:
            return []

    def load_multiple_sources(
        self,
        user_skills_dir: Optional[str] = None,
        project_skills_dir: Optional[str] = None,
        builtin_skills_dir: Optional[str] = None
    ) -> List[Skill]:
        """
        Load skills from multiple sources

        Args:
            user_skills_dir: User-specific skills directory
            project_skills_dir: Project-specific skills directory
            builtin_skills_dir: Built-in skills directory

        Returns:
            List of all loaded Skill objects
        """
        all_skills = []

        # Load from user skills
        if user_skills_dir:
            all_skills.extend(self.load_skills_from_directory(user_skills_dir))

        # Load from project skills
        if project_skills_dir:
            all_skills.extend(self.load_skills_from_directory(project_skills_dir))

        # Load from built-in skills
        if builtin_skills_dir:
            all_skills.extend(self.load_skills_from_directory(builtin_skills_dir))

        return all_skills
