"""
Chain SubAgent
负责协调多个SubAgent的执行链 - 拥有独立上下文
"""

import json
from typing import Dict, Any, Optional, TYPE_CHECKING
from .base import SubAgent, SubAgentResult

if TYPE_CHECKING:
    from . import SubAgent as SubAgentType


class ChainSubAgent(SubAgent):
    """执行链SubAgent - 协调多个SubAgent - 独立上下文"""
    
    def __init__(
        self,
        agent_context_snapshot: Optional[Dict[str, Any]] = None,
        subagents: Optional[Dict[str, 'SubAgentType']] = None
    ):
        """
        初始化ChainSubAgent
        
        Args:
            agent_context_snapshot: Agent上下文的快照
            subagents: 可用的SubAgent字典
        """
        # 创建独立的ContextManager（不调用super().__init__）
        from ..context import ContextManager
        self.context = ContextManager()
        
        self.subagents = subagents or {}
    
    async def execute(self, command: str, parameters: Dict[str, Any]) -> SubAgentResult:
        """
        执行SubAgent链
        
        Args:
            command: 链定义（JSON数组）
            parameters: 初始参数
        
        Returns:
            SubAgentResult（汇总所有步骤的结果）
        """
        import time
        start_time = time.time()
        
        # 解析链步骤
        try:
            if isinstance(command, str):
                steps = json.loads(command)
            else:
                steps = command
        except json.JSONDecodeError as e:
            return SubAgentResult(
                success=False,
                result=None,
                summary="Invalid chain definition",
                error=f"Failed to parse chain JSON: {str(e)}",
                metadata={"command": command}
            )
        
        if not isinstance(steps, list):
            return SubAgentResult(
                success=False,
                result=None,
                summary="Invalid chain format",
                error="Chain must be a list of steps",
                metadata={"command": command}
            )
        
        results = []
        current_input = parameters
        
        # 执行每个步骤
        for i, step in enumerate(steps, 1):
            subagent_type = step.get("type")  # tool/skill/chain
            
            # 动态创建SubAgent（每个步骤都有独立上下文）
            if subagent_type == "tool":
                from .tool_subagent import ToolSubAgent
                subagent = ToolSubAgent(self.context.get_snapshot(), self.subagents.get('tools', {}))
            elif subagent_type == "skill":
                from .skill_subagent import SkillSubAgent
                # 注意：这里需要传递skill_manager，实际实现需要调整
                # 暂时简化
                continue
            elif subagent_type == "chain":
                from .chain_subagent import ChainSubAgent
                subagent = ChainSubAgent(self.context.get_snapshot(), self.subagents)
            else:
                subagent = None
            
            if not subagent:
                return SubAgentResult(
                    success=False,
                    result=None,
                    summary=f"SubAgent not found at step {i}",
                    error=f"SubAgent type '{subagent_type}' not found",
                    metadata={
                        "step_index": i,
                        "step": step,
                        "command": command
                    }
                )
            
            try:
                # 执行SubAgent
                result = await subagent.execute(
                    command=step["command"],
                    parameters=current_input
                )
                
                if not result.success:
                    return SubAgentResult(
                        success=False,
                        result=None,
                        summary=f"Step {i} failed",
                        error=f"Step failed: {result.error}",
                        metadata={
                            "step_index": i,
                            "step": step,
                            "subagent_error": result.error
                        }
                    )
                
                results.append(result)
                
                # 将当前结果作为下一步的输入
                current_input = {"previous_result": result.result}
                
            except Exception as e:
                return SubAgentResult(
                    success=False,
                    result=None,
                    summary=f"Exception at step {i}",
                    error=str(e),
                    metadata={
                        "step_index": i,
                        "step": step,
                        "error_type": type(e).__name__
                    }
                )
        
        execution_time = time.time() - start_time
        
        # 汇总所有步骤的结果
        total_tokens = sum(r.tokens_used or 0 for r in results)
        total_time = sum(r.execution_time or 0 for r in results)
        
        return SubAgentResult(
            success=True,
            result={
                "steps": [r.result for r in results],
                "step_count": len(results),
                "summary": "Chain executed successfully"
            },
            summary=f"Chain completed: {len(results)} steps executed",
            metadata={
                "subagent_type": "chain",
                "total_steps": len(results),
                "total_tokens": total_tokens,
                "total_execution_time": total_time
            },
            tokens_used=total_tokens,
            execution_time=execution_time
        )
    
    def get_schema(self) -> Dict[str, Any]:
        """返回Chain SubAgent的能力描述"""
        return {
            "type": "chain_subagent",
            "description": "Execute multiple SubAgents in sequence",
            "parameters": {
                "command": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["tool", "skill", "chain"]
                            },
                            "command": {
                                "type": "string",
                                "description": "Command to execute"
                            },
                            "parameters": {
                                "type": "object",
                                "description": "Parameters for the command"
                            }
                        }
                    }
                },
                "parameters": {
                    "type": "object",
                    "description": "Initial parameters for first step"
                }
            },
            "available_subagents": list(self.subagents.keys()) if self.subagents else []
        }
