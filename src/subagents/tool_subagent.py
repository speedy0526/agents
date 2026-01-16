"""
Tool SubAgent
负责执行工具调用 - 拥有独立上下文
"""

from typing import Dict, Any, Optional
from .base import SubAgent, SubAgentResult


class ToolSubAgent(SubAgent):
    """工具执行SubAgent - 独立上下文"""
    
    def __init__(
        self,
        agent_context_snapshot: Optional[Dict[str, Any]] = None,
        tools: Optional[Dict[str, Any]] = None
    ):
        """
        初始化ToolSubAgent
        
        Args:
            agent_context_snapshot: Agent上下文的快照
            tools: 可用工具字典
        """
        # 创建独立的ContextManager（不调用super().__init__）
        from ..context import ContextManager
        import uuid

        # 使用唯一的 session_id 让每个 SubAgent 有独立的 session
        session_id = f"tool_{uuid.uuid4().hex[:8]}"
        self.context = ContextManager(auto_save=False, session_id=session_id)
        
        self.tools = tools or {}
    
    async def execute(self, command: str, parameters: Dict[str, Any]) -> SubAgentResult:
        """
        执行工具调用
        
        Args:
            command: 工具名称
            parameters: 工具参数
        
        Returns:
            SubAgentResult
        """
        import time
        import json
        start_time = time.time()
        
        tool = self.tools.get(command)
        if not tool:
            print(f"\n❌ Tool not found: {command}")
            print(f"   Available tools: {list(self.tools.keys())}")
            return SubAgentResult(
                success=False,
                result=None,
                summary=f"Tool not found: {command}",
                error=f"Tool not found: {command}",
                metadata={"command": command, "parameters": parameters}
            )
        
        # Print tool execution details
        print(f"\n{'='*60}")
        print(f"🛠️  Tool SubAgent: Executing Tool")
        print(f"{'='*60}")
        print(f"   Tool Name: {command}")
        print(f"   Parameters: {json.dumps(parameters, indent=4, ensure_ascii=False)}")
        print(f"{'='*60}")
        
        try:
            # 执行工具（调用 execute 方法）
            result = await tool.execute(**parameters)
            
            execution_time = time.time() - start_time
            
            # Print success result
            print(f"✅ Tool Execution Success")
            print(f"   Result: {result}")
            print(f"   Execution Time: {execution_time:.2f}s")
            print(f"{'='*60}\n")
            
            return SubAgentResult(
                success=True,
                result=result,
                summary=f"Tool '{command}' executed successfully",
                metadata={
                    "subagent_type": "tool",
                    "tool_name": command,
                    "parameters": parameters
                },
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Print error details
            print(f"❌ Tool Execution Failed")
            print(f"   Error: {str(e)}")
            print(f"   Error Type: {type(e).__name__}")
            print(f"{'='*60}\n")
            
            return SubAgentResult(
                success=False,
                result=None,
                summary=f"Tool '{command}' execution failed",
                error=str(e),
                metadata={
                    "subagent_type": "tool",
                    "tool_name": command,
                    "parameters": parameters,
                    "error_type": type(e).__name__
                },
                execution_time=execution_time
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """返回工具列表和schema"""
        return {
            "type": "tool_subagent",
            "tools": {
                name: {
                    "description": tool.description,
                    "parameters": tool.model_json_schema() if hasattr(tool, 'model_json_schema') else {}
                }
                for name, tool in self.tools.items()
            }
        }
