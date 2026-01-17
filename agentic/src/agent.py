"""
Minimal Agent System
Core Agent with Model + Tools + Loop + Context Engineering + Skills
"""

import os
import uuid
import json
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .llm import LLMClient
from .context import ContextManager
from .skills import SkillManager
from .subagents import SubAgentResult, ToolSubAgent, SkillSubAgent, ChainSubAgent


class Thought(BaseModel):
    """Agent thought"""

    reasoning: str = Field(description="Current reasoning")
    next_action: str = Field(
        description="Next action: 'use_tool', 'use_skill', 'call_chain', 'think', 'respond_to_user', 'finish'"
    )
    tool_name: Optional[str] = Field(
        default=None, description="Tool to use (for use_tool)"
    )
    tool_parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Tool parameters (for use_tool)"
    )
    subagent_type: Optional[str] = Field(
        default=None,
        description="SubAgent type: 'tool', 'skill', 'chain' (for use_skill/call_chain)",
    )
    subagent_command: Optional[str] = Field(
        default=None, description="SubAgent command/skill name/chain definition"
    )


class MinimalAgent:
    """
    Minimal agent with model, tools, skills, loop, and context engineering

    Skills are prompt-based workflows managed by the SkillManager (meta-tool):
    - Skills are defined as SKILL.md files with prompt instructions
    - SkillManager is a tool that manages all available skills
    - When invoked, skills inject their prompts into the conversation
    - Skills follow Claude Agent Skills architecture
    """

    def __init__(
        self,
        tools: List[Any],
        skills_dirs: Optional[List[str]] = None,
        workspace_dir: str = "workspace",
    ):
        self.llm = LLMClient()
        self.workspace_dir = workspace_dir

        # Initialize tools
        self.tools = {tool.name: tool for tool in tools}

        # Initialize skill manager
        self.skill_manager = SkillManager(skills_dirs=skills_dirs)

        # Initialize context manager (don't add system prompt yet - will be added in run())
        self.context = ContextManager(
            max_context_length=20000, workspace_dir=workspace_dir
        )

    def get_system_prompt(self) -> str:
        """
        Get system prompt (stable for KV-cache)

        Includes:
        - Tool descriptions
        - SubAgent capabilities
        - Usage guidelines
        """
        prompt_parts = ["You are a helpful AI agent."]

        # Add tools
        if self.tools:
            prompt_parts.append("\n## Available Tools\n")
            for name, tool in self.tools.items():
                prompt_parts.append(f"- {name}: {tool.description}")

        # Add SubAgent capabilities
        prompt_parts.append(f"\n## Available SubAgents\n")
        prompt_parts.append(
            f"- skill: Execute specialized skills (research, pdf, etc.)"
        )
        prompt_parts.append(
            f"  Available skills: {', '.join(self.skill_manager.get_skill_names()) or 'None'}"
        )
        prompt_parts.append(f"- chain: Execute multiple steps in sequence")

        # Add guidelines
        prompt_parts.append(f"""

## Guidelines

1. Use tools and SubAgents to accomplish tasks efficiently.
2. **CRITICAL**: When you need to use a skill, set next_action='use_skill', subagent_type='skill', subagent_command='skill-name'
3. Example: To use the research skill, respond with:
   - next_action='use_skill'
   - subagent_type='skill'
   - subagent_command='research'
4. When you need to use a regular tool, set next_action='use_tool', tool_name='tool-name', tool_parameters={{...}}
5. When task is complete, set next_action to 'finish' and provide a final answer.
6. If a tool or SubAgent fails, try a different approach.
7. Learn from errors - they are part of context for improvement.
8. Use resources efficiently - avoid unnecessary calls.
9. Keep user's goals in mind throughout the task.

## Task Completion Rules

**IMPORTANT**: Only set next_action='finish' when you have ACTUALLY COMPLETED the user's request:
- If user asked for research: You must have performed searches and gathered findings
- If user asked to save a file: You must have saved the file with actual content
- If user asked for information: You must have retrieved and presented the information
- Simply activating a skill or tool does NOT mean the task is complete
- You must verify that tangible results have been produced before finishing

## Action Format

- For skills: Set next_action='use_skill', subagent_type='skill', subagent_command='skill-name'
- For tools: Set next_action='use_tool', tool_name='tool-name', tool_parameters={{...}}
- For chains: Set next_action='call_chain', subagent_type='chain', subagent_command='[...]'
- To finish: Set next_action='finish' and provide final answer
""")

        return "\n".join(prompt_parts)

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get tools schema for LLM (logit masking support)"""
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for name, tool in self.tools.items()
        ]

    async def think(self) -> Thought:
        """
        Generate thought using current context

        Manus principles:
        - Use messages from ContextManager (KV-cache friendly)
        - Include goals at end (attention guidance)
        - No filtering needed - SubAgent context is separate
        """
        messages = self.context.get_messages(include_goals=True)

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

        # Insert meta instruction at the beginning (highest priority)
        messages_with_instruction = [
            {"role": "system", "content": meta_instruction},
            *messages,
        ]

        # Use streaming for better user experience
        print(f"\n{'=' * 60}")
        print("🤔 Agent Thinking...")
        print(f"{'=' * 60}\n")

        response = await self.llm.chat(messages_with_instruction, stream=True)

        # Extract JSON from streaming response
        content = response["choices"][0]["message"]["content"]
        json_text = self.llm._extract_json(content)
        parsed = json.loads(json_text)
        parsed = self.llm._ensure_object(parsed)

        return Thought.model_validate(parsed)

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:  # noqa: ANN401
        """
        Execute tool and log to context

        Note: Skills are now handled by execute_subagent, not here.
        This method only handles direct tool execution.
        """
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        # Execute tool
        result = await tool.execute(**parameters)

        # Log to context (preserve errors for learning)
        self.context.add_tool_result(
            tool_name=tool_name,
            result=result.summary if result.status == "success" else result.error,
            is_error=result.status != "success",
        )

        return result

    async def execute_subagent(self, thought: Thought) -> SubAgentResult:
        """
        Execute SubAgent based on Thought

        Args:
            thought: Agent thought with subagent selection

        Returns:
            SubAgentResult
        """
        # Get Context snapshot (单向依赖：Agent → SubAgent)
        context_snapshot = self.context.get_snapshot()

        # Route to appropriate SubAgent
        if thought.next_action == "use_tool":
            # Use ToolSubAgent for tool execution
            subagent = ToolSubAgent(context_snapshot, self.tools)
            command = thought.tool_name
            parameters = thought.tool_parameters or {}

        elif thought.next_action == "use_skill":
            # Create new SkillSubAgent instance with snapshot (独立上下文)
            subagent = SkillSubAgent(
                agent_context_snapshot=context_snapshot,
                skill_manager=self.skill_manager,
                skill_name=thought.subagent_command,
            )
            command = thought.subagent_command
            parameters = {
                "tools_available": self.tools,  # 传递可用工具
                "user_request": context_snapshot.get("user_request", ""),
            }

        elif thought.next_action == "call_chain":
            # Create ChainSubAgent with snapshot
            subagent = ChainSubAgent(context_snapshot, self.subagents)
            command = thought.subagent_command
            parameters = {}

        else:
            # Not a SubAgent action
            return None

        # Execute SubAgent
        print(f"\n{'=' * 60}")
        print(f"🚀 Agent: Executing SubAgent")
        print(f"{'=' * 60}")
        print(f"   Type: {thought.next_action}")
        print(f"   Command: {command}")
        print(f"{'=' * 60}\n")

        result = await subagent.execute(command=command, parameters=parameters)

        # Add result summary to Agent context (不包含SubAgent内部细节）
        if result.success:
            # Format SkillResult if applicable
            if hasattr(result.result, "summary"):
                formatted = result.summary
            elif hasattr(result.result, "get_summary_or_confirmation"):
                # SkillResult
                skill_result = result.result
                formatted = skill_result.get_summary_or_confirmation()

                # Add file info if available
                if file_info := skill_result.get_file_info():
                    formatted += f"\nFile: {file_info}"

                # Add data info
                if skill_result.has_data():
                    if skill_result.items:
                        formatted += f"\nFound {len(skill_result.items)} items"
                    if skill_result.insights:
                        formatted += (
                            f"\nKey Insights: {'; '.join(skill_result.insights[:3])}"
                        )
            else:
                formatted = result.summary or "SubAgent executed successfully"

            self.context.add_assistant_response(formatted)

            # 检查任务是否完成，如果是则添加系统消息促使Agent结束
            if self._is_task_complete(result):
                self.context.add_system_prompt("""
### Task Completion Check

The previous action has produced tangible results (saved files, data, or findings). 
You should now review these results and determine if the user's original request has been fulfilled.

If the task is complete:
- Set next_action='finish'
- Provide a final summary of what was accomplished

If the task needs more work:
- Continue with next_action='use_tool' or 'use_skill'
- Explain what still needs to be done
""")

            # Update shared memory with SubAgent metadata（只保留关键信息）
            if result.metadata:
                for key, value in result.metadata.items():
                    if key not in [
                        "subagent_type",
                        "skill_name",
                        "tool_name",
                        "command",
                        "parameters",
                    ]:
                        self.context.update_shared_memory(f"subagent_{key}", value)
        else:
            # Log error
            self.context.add_assistant_response(f"SubAgent failed: {result.error}")

        return result

    def _is_task_complete(self, subagent_result: SubAgentResult) -> bool:
        """
        检查任务是否完成

        判断标准：
        - SkillResult 有 file_path（保存了文件）
        - SkillResult 有实际数据结果
        - 或者结果中明确标记为任务完成
        """
        if not subagent_result.success:
            return False

        result = subagent_result.result
        has_tangible_results = False

        # Check if result is SkillResult
        if hasattr(result, "file_path") and result.file_path:
            has_tangible_results = True

        if hasattr(result, "file_paths") and result.file_paths:
            has_tangible_results = True

        if hasattr(result, "has_data") and result.has_data():
            has_tangible_results = True

        if (
            hasattr(result, "confirmation")
            and "complete" in str(result.confirmation).lower()
        ):
            has_tangible_results = True

        # Update shared memory flag
        if has_tangible_results:
            self.context.update_shared_memory("has_tangible_results", True)

        return has_tangible_results

    async def run(self, user_request: str, max_steps: int = 10) -> str:
        """
        Run agent loop with context management

        Manus principles:
        - Add user request to context
        - Think -> Act -> Observe -> Repeat
        - Compress context when needed
        - Preserve system prompt (stable prefix)
        """
        # Generate unique session ID for this run
        session_id = uuid.uuid4().hex[:8]  # Short unique ID
        print(f"\n{'=' * 60}")
        print(f"Starting new session: {session_id}")
        print(f"Task: {user_request}")
        print(f"{'=' * 60}")

        # Create new context manager for this session
        self.context = ContextManager(
            max_context_length=20000,
            workspace_dir=self.workspace_dir,
            auto_save=True,
            min_save_interval=0.5,
            session_id=session_id,
        )

        # Add system prompt to new context
        self.context.add_system_prompt(self.get_system_prompt())
        self.context.save()

        # Add user request
        self.context.add_user_request(user_request)

        # Set initial goals from request
        self.context.set_goals([f"Complete: {user_request}"])

        print(f"Tools: {len(self.tools)} (including skill manager)")
        print(
            f"Available skills: {', '.join(self.skill_manager.get_skill_names()) or 'None'}"
        )
        print(self.context.get_summary())

        for step in range(max_steps):
            # Compress context if needed
            self.context.compress_if_needed()

            # Think
            thought = await self.think()
            self.context.add_thought(thought.reasoning)

            print(f"\n[Step {step + 1}] Thought: {thought.reasoning}")

            # Safety check: if too many steps without tangible results, prompt Agent to finish
            if step >= 5 and not self.context.shared_memory.get("has_tangible_results"):
                self.context.add_system_prompt(f"""
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
                self.context.add_assistant_response(thought.reasoning)
                return thought.reasoning

            # Check if should think more
            if thought.next_action == "think":
                print("  Continuing reasoning...")
                continue

            # Check if should respond to user
            if thought.next_action == "respond_to_user":
                self.context.add_assistant_response(thought.reasoning)
                return thought.reasoning

            # Execute SubAgent
            try:
                subagent_result = await self.execute_subagent(thought)

                if subagent_result is None:
                    # Not a SubAgent action
                    print("  Not a SubAgent action, skipping...")
                    continue

                # Log SubAgent execution
                print(f"  SubAgent: {thought.next_action}")
                print(f"  Result: {subagent_result.summary}")

            except Exception as e:
                # Log error to context (Manus: preserve errors)
                self.context.add_assistant_response(
                    f"SubAgent execution error: {str(e)}"
                )
                print(f"  SubAgent failed: {thought.next_action}")
                print(f"  Error: {e}")

        return "Maximum steps reached. Task incomplete."

    def get_context_summary(self) -> str:
        """Get current context summary"""
        return self.context.get_summary()

    def clear_context(self):
        """Clear context (keep system prompt)"""
        self.context.clear()
