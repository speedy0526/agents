"""
Skills Data Models
Define the structure for prompt-based skills
"""

from pydantic import BaseModel, Field, PrivateAttr
from typing import Dict, Any, Optional, List, Literal


class SkillFrontmatter(BaseModel):
    """
    Frontmatter of a SKILL.md file

    Contains metadata and configuration for a skill
    """
    name: str = Field(description="Unique skill identifier")
    description: str = Field(description="Brief description of what the skill does")
    version: str = Field(default="1.0.0", description="Skill version")
    allowed_tools: Optional[str] = Field(default=None, description="Comma-separated list of allowed tools")
    model: Optional[str] = Field(default=None, description="Preferred model for this skill")
    disable_model_invocation: bool = Field(default=False, description="If true, skill can only be manually invoked")


class Skill(BaseModel):
    """
    A skill definition loaded from SKILL.md

    Skills are prompt-based, not code-based. They extend Claude's capabilities
    through carefully crafted instructions and resource bindings.
    """
    # Metadata
    name: str
    description: str
    version: str = "1.0.0"

    # Configuration
    allowed_tools: List[str] = Field(default_factory=list)
    model: Optional[str] = None
    disable_model_invocation: bool = False

    # Content
    content: str = Field(description="Full markdown content of the skill (prompt instructions)")

    # Resources
    base_dir: str = Field(description="Base directory of the skill")
    scripts_dir: Optional[str] = Field(default=None, description="Path to scripts/ directory")
    references_dir: Optional[str] = Field(default=None, description="Path to references/ directory")
    assets_dir: Optional[str] = Field(default=None, description="Path to assets/ directory")

    # Resources (lazy loaded) - Private attributes in Pydantic V2
    _scripts: Optional[List[str]] = PrivateAttr(default=None)
    _references: Optional[List[str]] = PrivateAttr(default=None)
    _assets: Optional[List[str]] = PrivateAttr(default=None)

    @property
    def scripts(self) -> List[str]:
        """Get available scripts"""
        return self.__pydantic_private__.get('_scripts', [])

    @property
    def references(self) -> List[str]:
        """Get available references"""
        return self.__pydantic_private__.get('_references', [])

    @property
    def assets(self) -> List[str]:
        """Get available assets"""
        return self.__pydantic_private__.get('_assets', [])


class SkillInvocation(BaseModel):
    """
    Parameters for invoking a skill

    This represents the parameters passed when calling the Skill tool
    """
    command: str = Field(description="Skill name to invoke")


class SkillContext(BaseModel):
    """
    Context injected when a skill is invoked

    Contains both visible (to user) and hidden (to Claude) information
    """
    skill_name: str
    skill_description: str
    allowed_tools: List[str]
    model_preference: Optional[str] = None

    # User-visible metadata
    user_message: str = Field(description="Message visible to user")

    # Hidden full prompt (sent to Claude)
    skill_prompt: str = Field(description="Full skill prompt instructions")
    is_meta: bool = Field(default=True, description="Marked as meta for internal tracking")

    # Resources references
    available_scripts: List[str] = Field(default_factory=list)
    available_references: List[str] = Field(default_factory=list)
    available_assets: List[str] = Field(default_factory=list)


class SkillRegistry(BaseModel):
    """
    Registry of all available skills

    Built from scanning multiple sources:
    - User settings directory
    - Project settings directory
    - Plugin directories
    - Built-in skills
    """
    skills: Dict[str, Skill] = Field(default_factory=dict, description="Map of skill name to Skill object")

    def get_skill_names(self) -> List[str]:
        """Get list of all available skill names"""
        return list(self.skills.keys())

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get skill by name"""
        return self.skills.get(name)

    def add_skill(self, skill: Skill):
        """Add or update a skill in the registry"""
        self.skills[skill.name] = skill

    def remove_skill(self, name: str) -> bool:
        """Remove skill from registry"""
        if name in self.skills:
            del self.skills[name]
            return True
        return False
