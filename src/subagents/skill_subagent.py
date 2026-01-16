"""
Skill SubAgent
负责执行Skill - 拥有独立上下文
"""

from typing import Dict, Any, TYPE_CHECKING
from .base import SubAgent, SubAgentResult
from .skill_result import SkillResult

if TYPE_CHECKING:
    from ..skills import SkillManager


class SkillSubAgent(SubAgent):
    """Skill执行SubAgent - 独立上下文"""
    
    def __init__(
        self,
        agent_context_snapshot: Dict[str, Any],
        skill_manager: 'SkillManager',
        skill_name: str
    ):
        """
        初始化SkillSubAgent
        
        Args:
            agent_context_snapshot: Agent上下文的快照
            skill_manager: Skill管理器
            skill_name: 要执行的skill名称
        """
        # 从快照中提取user_request
        self.user_request = agent_context_snapshot.get('user_request', '')
        
        # 创建独立的ContextManager（不调用super().__init__）
        from ..context import ContextManager
        self.context = ContextManager()
        
        self.skill_manager = skill_manager
        self.skill_name = skill_name
        
        # 加载并注入skill prompt到自己的上下文
        self._load_skill_prompt()
    
    def _load_skill_prompt(self):
        """加载skill prompt并注入到SubAgent的独立上下文"""
        # 获取skill
        skill = self.skill_manager.get_skill(self.skill_name)
        if not skill:
            raise ValueError(f"Skill not found: {self.skill_name}")
        
        # 获取可用的tools（从Agent的tools_available）
        # 注意：这里需要从parameters传递tools_available
        # 或者SubAgent初始化时传入
        # 暂时使用空字典，execute时会处理
        tools_available = getattr(self, '_tools_available', {})
        
        # 获取skill prompt
        from ..skills.context import SkillContextManager
        skill_context_manager = SkillContextManager()
        
        context_messages = skill_context_manager.get_context_messages(
            skill=skill,
            user_request=self.user_request,
            tools_available=tools_available
        )
        
        # 注入到SubAgent自己的上下文（不是Agent的上下文）
        if context_messages:
            for msg in context_messages:
                if msg.get("meta"):
                    # Hidden skill prompt
                    self.context.add_system_prompt(msg["content"])
                else:
                    # User-visible message
                    self.context.add_assistant_response(msg["content"])
    
    async def execute(self, command: str, parameters: Dict[str, Any]) -> SubAgentResult:
        """
        执行Skill
        
        Args:
            command: Skill命令（应该与skill_name一致）
            parameters: Skill参数（包含tools_available等）
        
        Returns:
            SubAgentResult
        """
        import time
        start_time = time.time()
        
        try:
            # 存储tools_available供_load_skill_prompt使用
            tools_available = parameters.get('tools_available', {})
            self._tools_available = tools_available
            
            # 重新加载skill prompt（这次有tools_available）
            self._load_skill_prompt()
            
            # 执行Skill（使用skill_manager）
            skill_result: SkillResult = await self.skill_manager.execute_skill(
                command=command,
                parameters=parameters
            )
            
            execution_time = time.time() - start_time
            
            # 包装为SubAgentResult
            return SubAgentResult(
                success=skill_result.success,
                result=skill_result,
                summary=skill_result.get_summary_or_confirmation(),
                error=None if skill_result.success else skill_result.get_summary_or_confirmation(),
                metadata={
                    "subagent_type": "skill",
                    "skill_name": command,
                    "parameters": parameters,
                    "skill_result_type": "SkillResult"
                },
                tokens_used=skill_result.tokens_used,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            
            # 创建失败的SkillResult
            failed_result = SkillResult(
                success=False,
                confirmation=f"Skill execution failed: {command}",
                summary=f"Error: {str(e)}",
                errors=[str(e)]
            )
            
            return SubAgentResult(
                success=False,
                result=failed_result,
                summary=f"Skill '{command}' execution failed",
                error=str(e),
                metadata={
                    "subagent_type": "skill",
                    "skill_name": command,
                    "parameters": parameters,
                    "error_type": type(e).__name__
                },
                execution_time=execution_time
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """返回可用Skills列表"""
        return {
            "type": "skill_subagent",
            "skills": self.skill_manager.get_skill_names()
        }
