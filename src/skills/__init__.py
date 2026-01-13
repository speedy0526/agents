"""
Skills System
High-level abstractions combining multiple tools
"""

from .base import Skill, SkillResult
from .research import ResearchSkill, MultiTopicResearchSkill

__all__ = [
    "Skill",
    "SkillResult",
    "ResearchSkill",
    "MultiTopicResearchSkill",
]
