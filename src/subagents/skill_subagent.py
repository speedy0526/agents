"""
Skill SubAgent
负责执行Skill - 拥有独立上下文
"""

from typing import Dict, Any, TYPE_CHECKING, List
from .base import SubAgent, SubAgentResult
from .skill_result import SkillResult
from datetime import datetime

if TYPE_CHECKING:
    from ..skills import SkillManager


class SkillSubAgent(SubAgent):
    """Skill执行SubAgent - 独立上下文，运行完整的LLM循环"""

    def __init__(
        self,
        agent_context_snapshot: Dict[str, Any],
        skill_manager: "SkillManager",
        skill_name: str,
    ):
        """
        初始化SkillSubAgent

        Args:
            agent_context_snapshot: Agent上下文的快照
            skill_manager: Skill管理器
            skill_name: 要执行的skill名称
        """
        # 从快照中提取user_request
        self.user_request = agent_context_snapshot.get("user_request", "")

        # 保存 skill_name（在生成 session_id 之前）
        self.skill_manager = skill_manager
        self.skill_name = skill_name

        # 创建独立的ContextManager（不调用super().__init__）
        from ..context import ContextManager

        # 使用唯一的 session_id 避免 session 文件冲突
        import uuid

        session_id = f"skill_{self.skill_name}_{uuid.uuid4().hex[:8]}"

        self.context = ContextManager(auto_save=False, session_id=session_id)

    async def execute(self, command: str, parameters: Dict[str, Any]) -> SubAgentResult:
        """
        执行Skill - 使用自己的context运行完整的LLM循环

        Args:
            command: Skill命令（应该与skill_name一致）
            parameters: Skill参数（包含tools_available等）

        Returns:
            SubAgentResult
        """
        from ..llm import LLMClient

        # 获取skill
        skill = self.skill_manager.get_skill(command)
        if not skill:
            failed_result = SkillResult(
                success=False,
                confirmation=f"Skill not found: {command}",
                summary=f"Skill '{command}' not available",
            )
            return SubAgentResult(
                success=False,
                result=failed_result,
                summary=f"Skill '{command}' not available",
                error=f"Skill '{command}' not available",
                metadata={
                    "subagent_type": "skill",
                    "skill_name": command,
                    "parameters": parameters,
                },
            )

        user_request = parameters.get("user_request", self.user_request)
        tools_available = parameters.get("tools_available", {})

        # Filter tools based on skill's allowed_tools
        from ..skills.context import SkillContextManager

        skill_context_manager = SkillContextManager()
        filtered_tools = skill_context_manager.filter_allowed_tools(
            skill, tools_available
        )

        # Validate required tools
        missing_tools = set(skill.allowed_tools) - set(filtered_tools.keys())
        if missing_tools:
            failed_result = SkillResult(
                success=False,
                confirmation=f"Missing required tools",
                summary=f"Skill '{command}' requires tools that are not available: {missing_tools}",
                errors=[f"Missing tool: {t}" for t in missing_tools],
            )
            return SubAgentResult(
                success=False,
                result=failed_result,
                summary=f"Missing required tools for skill '{command}'",
                error=f"Missing tools: {missing_tools}",
                metadata={
                    "subagent_type": "skill",
                    "skill_name": command,
                    "parameters": parameters,
                },
            )

        print(f"\n{'=' * 60}")
        print(f"🎯 Skill Execution: {command}")
        print(f"{'=' * 60}")
        print(f"   Request: {user_request}")
        print(f"   Available tools: {list(filtered_tools.keys())}")
        print(f"{'=' * 60}\n")

        # Initialize context
        self._init_skill_context(skill, user_request, filtered_tools)

        # Initialize result tracking
        tool_calls = []
        outputs = []
        files_saved = []
        errors = []
        execution_steps = 0
        max_skill_steps = 20  # Prevent infinite loops

        llm = LLMClient()
        start_time = datetime.now()

        # Skill execution loop
        while execution_steps < max_skill_steps:
            execution_steps += 1

            # Get messages (system prompt + tool results)
            messages = self.context.get_messages(include_goals=False)

            # Prompt LLM with skill instructions
            try:
                print(f"\n{'=' * 60}")
                print(f"🤖 Skill Step {execution_steps}")
                print(f"{'=' * 60}")

                # Use streaming for skill LLM calls
                print("\n💭 Skill AI Thinking...")
                response = await llm.chat(messages=messages, stream=True)
                response_text = response["choices"][0]["message"]["content"]
                if not response_text:
                    continue

                print(f"\n🎯 AI Response: {response_text[:200]}...")
                print(f"{'=' * 60}\n")

                # Add AI response to context
                self.context.add_assistant_response(response_text)

                # Check if skill indicates completion
                if self._is_skill_complete(response_text):
                    print(f"✅ Skill '{command}' completed")
                    break

                # Extract and execute tool calls from response
                tool_calls_made = await self._execute_skill_tools(
                    response_text, filtered_tools, self.context
                )

                if tool_calls_made:
                    tool_calls.extend(tool_calls_made)
                    # Check if we produced tangible results (files, data)
                    for call in tool_calls_made:
                        if call.get("tool_name") == "file_write" and call.get(
                            "success"
                        ):
                            files_saved.append(
                                call.get("result", {}).get("filepath", "")
                            )
                else:
                    # No tool calls made, might be asking for more thinking
                    # or indicating completion
                    if self._is_skill_complete(response_text):
                        print(f"✅ Skill '{command}' completed")
                        break
                    # Continue to next iteration (AI will call tools next)

            except Exception as e:
                error_msg = f"Step {execution_steps}: {str(e)}"
                errors.append(error_msg)
                print(f"❌ {error_msg}")

                # If too many errors, abort
                if len(errors) >= 3:
                    break

        # Compile final result
        execution_time = (datetime.now() - start_time).total_seconds()

        # Determine success
        success = len(errors) < 3 and (len(files_saved) > 0 or len(outputs) > 0)

        skill_result = SkillResult(
            success=success,
            confirmation=f"Skill '{command}' execution {'complete' if success else 'failed'}",
            summary=self._generate_skill_summary(
                command, tool_calls, files_saved, errors
            ),
            details=f"Executed {len(tool_calls)} tool calls in {execution_steps} steps",
            items=tool_calls,
            file_paths=files_saved if files_saved else None,
            count=len(tool_calls),
            tokens_used=None,  # Would need to track from llm calls
            metadata={
                "skill_name": command,
                "user_request": user_request,
                "execution_steps": execution_steps,
                "tool_calls": len(tool_calls),
                "files_created": len(files_saved),
            },
            errors=errors if errors else None,
            execution_time=execution_time,
        )

        return SubAgentResult(
            success=success,
            result=skill_result,
            summary=skill_result.get_summary_or_confirmation(),
            error=None if success else skill_result.get_summary_or_confirmation(),
            metadata={
                "subagent_type": "skill",
                "skill_name": command,
                "parameters": parameters,
                "skill_result_type": "SkillResult",
            },
            tokens_used=skill_result.tokens_used,
            execution_time=execution_time,
        )

    def _init_skill_context(
        self, skill: "Skill", user_request: str, tools_available: Dict[str, Any]
    ):
        """
        Initialize skill context with skill prompt and user request

        Args:
            skill: Skill object
            user_request: User's request
            tools_available: Available tools for the skill
        """
        from ..skills.context import SkillContextManager

        skill_context_manager = SkillContextManager()

        # Load skill context messages
        context_messages = skill_context_manager.get_context_messages(
            skill=skill, user_request=user_request, tools_available=tools_available
        )

        # Add messages to SubAgent's context
        if context_messages:
            for msg in context_messages:
                if msg.get("meta"):
                    # Hidden skill prompt - add as system prompt
                    self.context.add_system_prompt(msg["content"])
                # Skip user-visible messages (meta: false) - they're just for display
                else:
                    self.context.add_user_request(msg["content"])
        # Add task completion guidance
        task_completion = """
## Task Completion

You should complete the task by:
1. Using the available tools to gather information or perform actions
2. Producing tangible results (saving files, collecting data, compiling reports)
3. When finished with tangible results, clearly indicate completion

Do NOT continue indefinitely. Once you have:
- Saved a file with content, OR
- Gathered and compiled information, OR
- Otherwise fulfilled the user's request

Then clearly state: "Task complete" or similar.
"""
        self.context.add_system_prompt(task_completion)

    def _is_skill_complete(self, response: str) -> bool:
        """Check if skill response indicates completion"""
        completion_indicators = [
            "task complete",
            "workflow complete",
            "skill complete",
            "finished",
            "done",
            "completed successfully",
            "file saved",
            "report generated",
        ]
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in completion_indicators)

    async def _execute_skill_tools(
        self, response: str, tools: Dict[str, Any], context
    ) -> List[Dict[str, Any]]:
        """
        Extract and execute tool calls from AI response

        Args:
            response: AI response text
            tools: Available tools dictionary
            context: Context manager to add results to

        Returns:
            List of executed tool call records
        """
        import re
        from json import JSONDecodeError

        tool_calls = []

        # Try to extract tool calls using common patterns
        tool_patterns = [
            r"calling\s+(\w+)\s*\(",
            r"use\s+(\w+)\s+with",
            r"execute\s+(\w+)",
            r"calling\s+the\s+(\w+)\s+tool",
            r"(file_write|search_google)\(",
        ]

        for pattern in tool_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                tool_name = match.group(1).strip()

                # Try to extract parameters
                param_pattern = r"\{.*?\}"
                param_match = re.search(
                    param_pattern, response[match.end() : match.end() + 200]
                )

                parameters = {}
                if param_match:
                    try:
                        import json

                        parameters = json.loads(param_match.group(0))
                    except (JSONDecodeError, json.JSONDecodeError):
                        # Fallback: try to find filepath parameter
                        filepath_match = re.search(
                            r'filepath["\s:]+\s*["\']([^"\']+)["\']',
                            response,
                            re.IGNORECASE,
                        )
                        if filepath_match:
                            parameters["filepath"] = filepath_match.group(1)

                # Execute tool if available
                if tool_name in tools:
                    try:
                        result = await tools[tool_name].execute(**parameters)
                        result_obj = {
                            "tool_name": tool_name,
                            "parameters": parameters,
                            "success": True,
                            "result": {
                                "summary": result.summary
                                if hasattr(result, "summary")
                                else str(result),
                                "status": result.status
                                if hasattr(result, "status")
                                else "success",
                            },
                        }

                        # Add tool result to context
                        context.add_tool_result(
                            tool_name=tool_name,
                            result=result.summary
                            if hasattr(result, "summary")
                            else str(result),
                            is_error=hasattr(result, "status")
                            and result.status != "success",
                        )

                        tool_calls.append(result_obj)
                        print(f"✅ Tool '{tool_name}' executed")

                    except Exception as e:
                        error_record = {
                            "tool_name": tool_name,
                            "parameters": parameters,
                            "success": False,
                            "error": str(e),
                        }
                        tool_calls.append(error_record)
                        print(f"❌ Tool '{tool_name}' failed: {e}")

                # Break after first tool call to avoid duplicate processing
                break

        return tool_calls

    def _generate_skill_summary(
        self,
        skill_name: str,
        tool_calls: List[Dict[str, Any]],
        files_saved: List[str],
        errors: List[str],
    ) -> str:
        """Generate a summary of skill execution"""
        parts = [f"Skill '{skill_name}' execution"]

        if files_saved:
            parts.append(
                f"\n✓ Created {len(files_saved)} file(s): {', '.join(files_saved)}"
            )

        if tool_calls:
            successful = sum(1 for c in tool_calls if c.get("success"))
            parts.append(
                f"\n✓ Executed {successful}/{len(tool_calls)} tool calls successfully"
            )

        if errors:
            parts.append(f"\n✗ Encountered {len(errors)} errors")

        return "\n".join(parts)

    def get_schema(self) -> Dict[str, Any]:
        """返回可用Skills列表"""
        return {
            "type": "skill_subagent",
            "skills": self.skill_manager.get_skill_names(),
        }
