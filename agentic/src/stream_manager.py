"""
Stream Manager - 适配 Agent.run() 为 WebSocket 流式输出
"""

import json
import uuid
from typing import Dict, Any, Optional
from fastapi import WebSocket

from .agent import MinimalAgent, Thought


class StreamManager:
    """
    流式输出管理器，将 Agent 执行过程实时推送到 WebSocket
    
    支持的事件类型：
    - user_message: 用户消息
    - agent_thinking: Agent 思考过程
    - agent_action: Agent 执行动作
    - agent_result: 执行结果
    - agent_complete: 任务完成
    - error: 错误信息
    """

    def __init__(self, websocket: WebSocket, session_id: str):
        """
        初始化 StreamManager
        
        Args:
            websocket: WebSocket 连接
            session_id: 会话 ID
        """
        self.websocket = websocket
        self.session_id = session_id

    async def send_event(self, event_type: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        发送事件到 WebSocket
        
        Args:
            event_type: 事件类型
            content: 事件内容
            metadata: 额外元数据
        """
        message = {
            "event": event_type,
            "content": content,
            "metadata": metadata or {},
            "session_id": self.session_id,
            "timestamp": self._get_timestamp()
        }
        try:
            await self.websocket.send_json(message)
        except Exception as e:
            print(f"WebSocket send error: {e}")

    @staticmethod
    def _get_timestamp() -> str:
        """获取当前时间戳"""
        import datetime
        return datetime.datetime.now().isoformat()

    async def stream_agent_run(self, agent: MinimalAgent, user_request: str, max_steps: int = 10):
        """
        执行 Agent 并流式输出事件到 WebSocket
        
        修改自 MinimalAgent.run()，在关键步骤插入 WebSocket 推送逻辑
        
        Args:
            agent: MinimalAgent 实例
            user_request: 用户请求
            max_steps: 最大执行步数
        """
        # 发送用户消息事件
        await self.send_event("user_message", user_request)

        # Generate unique session ID for this run
        session_id = uuid.uuid4().hex[:8]

        # Create new context manager for this session
        agent.context = agent.context.__class__(
            max_context_length=20000,
            workspace_dir=agent.workspace_dir,
            auto_save=True,
            min_save_interval=0.5,
            session_id=session_id,
        )

        # Add system prompt to new context
        agent.context.add_system_prompt(agent.get_system_prompt())
        agent.context.save()

        # Add user request
        agent.context.add_user_request(user_request)

        # Set initial goals from request
        agent.context.set_goals([f"Complete: {user_request}"])

        # 发送初始信息
        await self.send_event("agent_info", {
            "tools_count": len(agent.tools),
            "available_skills": ', '.join(agent.skill_manager.get_skill_names()) or 'None',
            "context_summary": agent.context.get_summary()
        })

        for step in range(max_steps):
            # Compress context if needed
            agent.context.compress_if_needed()

            # Think
            thought = await agent.think()
            agent.context.add_thought(thought.reasoning)

            # 发送思考事件
            await self.send_event(
                "agent_thinking",
                thought.reasoning,
                {"step": step + 1}
            )

            # Safety check
            if step >= 5 and not agent.context.shared_memory.get("has_tangible_results"):
                agent.context.add_system_prompt(f"""
### Progress Check

You have taken {step + 1} steps but haven't produced tangible results yet.
Consider if you should:
1. Actually execute the tools/skills to produce results, OR
2. Set next_action='finish' if the task is somehow complete, OR  
3. Respond to user asking for clarification

Remember: Activating a skill or tool is not the same as completing the task.
""")

            # Check if finished
            if thought.next_action == "finish":
                agent.context.add_assistant_response(thought.reasoning)
                await self.send_event("agent_complete", thought.reasoning)
                return thought.reasoning

            # Check if should think more
            if thought.next_action == "think":
                await self.send_event("agent_thinking", "Continuing reasoning...")
                continue

            # Check if should respond to user
            if thought.next_action == "respond_to_user":
                agent.context.add_assistant_response(thought.reasoning)
                await self.send_event("agent_result", thought.reasoning)
                return thought.reasoning

            # Execute SubAgent
            try:
                # 发送动作事件
                await self.send_event(
                    "agent_action",
                    f"Executing: {thought.next_action}",
                    {
                        "action_type": thought.next_action,
                        "tool_name": thought.tool_name,
                        "subagent_type": thought.subagent_type,
                        "subagent_command": thought.subagent_command
                    }
                )

                subagent_result = await agent.execute_subagent(thought)

                if subagent_result is None:
                    # Not a SubAgent action
                    await self.send_event("agent_thinking", "Not a SubAgent action, skipping...")
                    continue

                # 发送结果事件
                await self.send_event(
                    "agent_result",
                    subagent_result.summary or "SubAgent executed successfully",
                    {
                        "success": subagent_result.success,
                        "error": subagent_result.error,
                        "metadata": subagent_result.metadata
                    }
                )

            except Exception as e:
                # Log error to context
                agent.context.add_assistant_response(
                    f"SubAgent execution error: {str(e)}"
                )
                # 发送错误事件
                await self.send_event("error", f"SubAgent execution error: {str(e)}")

        return "Maximum steps reached. Task incomplete."
