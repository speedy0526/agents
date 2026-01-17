"""
Stream Manager - 适配 Agent.run() 为 WebSocket 流式输出
"""

import json
import time
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
        self._abort = False  # 中止标志

    def abort(self):
        """中止当前执行"""
        self._abort = True

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

    async def think_stream(self, agent: MinimalAgent) -> Thought:
        """
        流式执行 think 并实时推送到 WebSocket

        Args:
            agent: MinimalAgent 实例

        Returns:
            Thought 对象
        """
        messages = agent.context.get_messages(include_goals=True)

        # Build meta instruction for Thought generation
        meta_instruction = """<OUTPUT_FORMAT>
You must respond with JSON using ONLY these fields:

Required fields: reasoning, next_action, tool_name (optional), tool_parameters (optional), subagent_type (optional), subagent_command (optional)

Schema:
{
  "reasoning": "Your reasoning process",
  "next_action": "One of: use_tool, use_skill, call_chain, think, respond_to_user, finish",
  "tool_name": "Name of tool to use (if next_action='use_tool')",
  "tool_parameters": {"param1": "value1"},
  "subagent_type": "Type of SubAgent (skill, tool, chain)",
  "subagent_command": "Command for SubAgent"
}

CRITICAL RULES:
1. Your entire response must be a single JSON object
2. Use ONLY the exact field names listed above
3. Do NOT include any fields like 'query', 'search', 'answer', etc.
4. Do NOT wrap in markdown code blocks
5. Output nothing except the JSON object

Examples:
- To use a tool: {"reasoning": "I need to search", "next_action": "use_tool", "tool_name": "search_google", "tool_parameters": {"query": "Python"}}
- To use a skill: {"reasoning": "I need to research", "next_action": "use_skill", "subagent_type": "skill", "subagent_command": "research"}
- To finish: {"reasoning": "Task complete", "next_action": "finish"}
</OUTPUT_FORMAT>"""

        messages_with_instruction = [
            {"role": "system", "content": meta_instruction},
            *messages,
        ]

        # 使用 LLM 的流式 API
        full_content = ""
        start = time.time()

        # 发送思考开始事件
        await self.send_event("agent_thinking", "💭 Thinking...")

        try:
            # 使用现有的流式接口
            params = {"model": agent.llm.model, "messages": messages_with_instruction, "stream": True}
            stream = await agent.llm.client.chat.completions.create(**params)

            async for chunk in stream:
                # 检查中止标志
                if self._abort:
                    break

                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    # 实时发送思考内容
                    await self.send_event("agent_thinking", content)

            # 解析 JSON
            json_text = agent.llm._extract_json(full_content)
            parsed = json.loads(json_text)
            parsed = agent.llm._ensure_object(parsed)

            return Thought.model_validate(parsed)

        except Exception as e:
            duration = time.time() - start
            await self.send_event("error", f"Thinking failed: {e}")
            raise

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
        await self.send_event("agent_info", f"Ready. Tools: {len(agent.tools)}, Skills: {', '.join(agent.skill_manager.get_skill_names()) or 'None'}")

        for step in range(max_steps):
            # 检查中止标志
            if self._abort:
                await self.send_event("agent_info", "⚠️ 任务已被中止")
                return "Task aborted by user"

            # Compress context if needed
            agent.context.compress_if_needed()

            # Think with streaming
            thought = await self.think_stream(agent)
            agent.context.add_thought(thought.reasoning)

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
