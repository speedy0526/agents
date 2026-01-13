"""
Context Engineering for Minimal Agent
Based on Manus principles: KV-cache friendly, external memory, attention guidance
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field


class ContextEntry(BaseModel):
    """Single context entry"""
    role: str = Field(description="Role: system, user, assistant, observation")
    content: str = Field(description="Content")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    entry_type: str = Field(default="message", description="Type: message, thought, tool_result, error")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ContextManager:
    """
    Context manager with KV-cache optimization principles

    Key principles from Manus:
    1. Stable prefixes (avoid variable timestamps)
    2. Append-only, no modifications (deterministic serialization)
    3. External memory (file system)
    4. Attention guidance (restatement of goals)
    5. Preserve errors for learning
    """

    def __init__(
        self,
        max_context_length: int = 8000,
        workspace_dir: str = "workspace"
    ):
        self.entries: List[ContextEntry] = []
        self.max_context_length = max_context_length
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(exist_ok=True)

        # External memory files
        self.session_file = self.workspace_dir / "session_context.json"
        self.goals_file = self.workspace_dir / "goals.md"
        self.errors_file = self.workspace_dir / "errors.md"

        # Load existing session if available
        self._load_session()

    def _load_session(self):
        """Load session from external memory"""
        if self.session_file.exists():
            try:
                data = json.loads(self.session_file.read_text(encoding="utf-8"))
                self.entries = [
                    ContextEntry.model_validate(entry)
                    for entry in data.get("entries", [])
                ]
                print(f"✓ Loaded {len(self.entries)} entries from session")
            except Exception as e:
                print(f"✗ Failed to load session: {e}")

    def _save_session(self):
        """Save session to external memory"""
        data = {
            "entries": [entry.model_dump() for entry in self.entries],
            "updated_at": datetime.now().isoformat()
        }
        self.session_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_system_prompt(self, content: str):
        """Add stable system prompt (KV-cache friendly)"""
        entry = ContextEntry(
            role="system",
            content=content,
            entry_type="system"
        )
        self.entries.insert(0, entry)  # System prompt always first

    def add_user_request(self, content: str):
        """Add user request"""
        entry = ContextEntry(
            role="user",
            content=content,
            entry_type="message"
        )
        self.entries.append(entry)
        self._save_session()

    def add_assistant_response(self, content: str):
        """Add assistant response"""
        entry = ContextEntry(
            role="assistant",
            content=content,
            entry_type="message"
        )
        self.entries.append(entry)
        self._save_session()

    def add_tool_result(self, tool_name: str, result: str, is_error: bool = False):
        """Add tool result (preserve errors for learning)"""
        entry_type = "error" if is_error else "tool_result"

        entry = ContextEntry(
            role="assistant",
            content=f"[{tool_name}] {result}",
            entry_type=entry_type,
            metadata={"tool_name": tool_name, "is_error": is_error}
        )
        self.entries.append(entry)

        # Also save to errors file for learning
        if is_error:
            self._log_error(tool_name, result)
        else:
            self._save_session()

    def add_thought(self, reasoning: str):
        """Add agent thought (internal reasoning)"""
        entry = ContextEntry(
            role="assistant",
            content=f"[THOUGHT] {reasoning}",
            entry_type="thought"
        )
        self.entries.append(entry)
        self._save_session()

    def _log_error(self, tool_name: str, error_msg: str):
        """Log error to external memory for learning"""
        timestamp = datetime.now().isoformat()
        error_entry = f"## Error - {timestamp}\n\n**Tool:** {tool_name}\n**Error:** {error_msg}\n\n"

        with open(self.errors_file, "a", encoding="utf-8") as f:
            f.write(error_entry)

    def set_goals(self, goals: List[str]):
        """Set current goals (attention guidance)"""
        content = "# Current Goals\n\n"
        for i, goal in enumerate(goals, 1):
            content += f"{i}. {goal}\n"

        self.goals_file.write_text(content, encoding="utf-8")
        print(f"✓ Updated goals: {len(goals)} items")

    def get_goals(self) -> str:
        """Get current goals for attention guidance"""
        if self.goals_file.exists():
            return self.goals_file.read_text(encoding="utf-8")
        return ""

    def compress_if_needed(self):
        """
        Compress context using external memory

        Strategy (KV-cache friendly):
        1. Keep system prompt (stable prefix)
        2. Keep recent entries (attention window)
        3. Move old entries to external memory (file system)
        4. Preserve goals (attention guidance)
        """
        if not self._needs_compression():
            return

        print(f"Context length {len(self.entries)} exceeds limit, compressing...")

        # Keep system prompt
        system_entries = [e for e in self.entries if e.entry_type == "system"]

        # Keep last N entries (recent attention window)
        recent_count = 10
        recent_entries = self.entries[-recent_count:] if len(self.entries) > recent_count else []

        # Archive old entries to file
        old_entries = self.entries[len(system_entries):-recent_count] if len(self.entries) > len(system_entries) + recent_count else []

        if old_entries:
            archive_file = self.workspace_dir / f"archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            archive_data = {
                "archived_at": datetime.now().isoformat(),
                "entries": [e.model_dump() for e in old_entries]
            }
            archive_file.write_text(json.dumps(archive_data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"✓ Archived {len(old_entries)} entries to {archive_file.name}")

        # Update context (append-only, no modification)
        self.entries = system_entries + recent_entries
        self._save_session()

    def _needs_compression(self) -> bool:
        """Check if context needs compression"""
        total_length = sum(len(e.content) for e in self.entries)
        return total_length > self.max_context_length

    def get_messages(self, include_goals: bool = True) -> List[Dict[str, str]]:
        """
        Get messages for LLM (KV-cache optimized)

        Principles:
        1. Stable system prompt (cacheable)
        2. Recent context (attention window)
        3. Goals at the end (attention guidance)
        """
        messages = []

        # System messages (stable prefix)
        for entry in self.entries:
            if entry.entry_type == "system":
                messages.append({"role": entry.role, "content": entry.content})

        # Recent messages (excluding system)
        for entry in self.entries:
            if entry.entry_type != "system":
                messages.append({"role": entry.role, "content": entry.content})

        # Add goals at the end (attention guidance)
        if include_goals:
            goals = self.get_goals()
            if goals:
                messages.append({
                    "role": "system",
                    "content": f"\n{goals}\n\nKeep these goals in mind."
                })

        return messages

    def get_summary(self) -> str:
        """Get context summary"""
        return f"""
Context Summary:
- Total entries: {len(self.entries)}
- Errors logged: {self.errors_file.stat().st_size if self.errors_file.exists() else 0} bytes
- Goals defined: {len(self.get_goals()) > 0}
- Workspace: {self.workspace_dir}
- Max length: {self.max_context_length} chars
- Current size: {sum(len(e.content) for e in self.entries)} chars
"""

    def clear(self):
        """Clear context (keep system prompt)"""
        system_entries = [e for e in self.entries if e.entry_type == "system"]
        self.entries = system_entries
        self._save_session()
        print("✓ Context cleared (system prompt preserved)")
