"""
Skills System - Prompt-Based Meta-Tool Architecture

Based on Claude Agent Skills design principles:
- Prompt-based skills (not code-based)
- Meta-tool pattern (Skill tool manages all skills)
- Progressive disclosure
- Context modification
- Resource bindings (scripts, references, assets)
"""

from .models import (
    Skill,
    SkillFrontmatter,
    SkillInvocation,
    SkillContext,
    SkillRegistry,
)

from .loader import SkillLoader
from .manager import SkillManager
from .context import SkillContextManager

__all__ = [
    # Models
    "Skill",
    "SkillFrontmatter",
    "SkillInvocation",
    "SkillContext",
    "SkillRegistry",

    # Components
    "SkillLoader",
    "SkillManager",
    "SkillContextManager",
]
