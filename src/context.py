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
        workspace_dir: str = "workspace",
        auto_save: bool = True,
        min_save_interval: float = 0.5,
        session_id: Optional[str] = None
    ):
        self.entries: List[ContextEntry] = []
        self.max_context_length = max_context_length
        self.auto_save = auto_save
        self.min_save_interval = min_save_interval
        self._dirty = False
        self._last_save_time = 0.0
        self.session_id = session_id
        
        # Shared memory for SubAgent communication
        self.shared_memory: Dict[str, Any] = {}

        # Determine workspace directory based on session_id
        base_workspace_dir = Path(workspace_dir)
        if session_id:
            self.workspace_dir = base_workspace_dir / f"session_{session_id}"
        else:
            self.workspace_dir = base_workspace_dir
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

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

    def _save_session(self, force: bool = False):
        """Save session to external memory
        
        Args:
            force: If True, save immediately regardless of interval.
                   If False, respect min_save_interval.
        """
        import time
        current_time = time.time()
        
        # Check if we should skip save (not forced and within interval)
        if not force and self._last_save_time > 0:
            elapsed = current_time - self._last_save_time
            if elapsed < self.min_save_interval:
                # Skip save, but keep dirty flag
                return
        
        data = {
            "entries": [entry.model_dump() for entry in self.entries],
            "updated_at": datetime.now().isoformat()
        }
        self.session_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self._dirty = False
        self._last_save_time = current_time

    def save(self):
        """Force save session to external memory"""
        self._save_session(force=True)

    def add_system_prompt(self, content: str):
        """Add stable system prompt (KV-cache friendly)"""
        entry = ContextEntry(
            role="system",
            content=content,
            entry_type="system"
        )
        self.entries.insert(0, entry)  # System prompt always first
        self._dirty = True
        if self.auto_save:
            self._save_session()

    def add_user_request(self, content: str):
        """Add user request"""
        entry = ContextEntry(
            role="user",
            content=content,
            entry_type="message"
        )
        self.entries.append(entry)
        self._dirty = True
        if self.auto_save:
            self._save_session()

    def add_assistant_response(self, content: str):
        """Add assistant response"""
        entry = ContextEntry(
            role="assistant",
            content=content,
            entry_type="message"
        )
        self.entries.append(entry)
        self._dirty = True
        if self.auto_save:
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
        self._dirty = True

        # Also save to errors file for learning
        if is_error:
            self._log_error(tool_name, result)
        elif self.auto_save:
            self._save_session()

    def add_thought(self, reasoning: str):
        """Add agent thought (internal reasoning)"""
        entry = ContextEntry(
            role="assistant",
            content=f"[THOUGHT] {reasoning}",
            entry_type="thought"
        )
        self.entries.append(entry)
        self._dirty = True
        if self.auto_save:
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
        recent_count = 20
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
        self.save()

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

        # Recent messages (excluding system and thought)
        for entry in self.entries:
            if entry.entry_type != "system" and entry.entry_type != "thought":
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
        self.save()
        print("✓ Context cleared (system prompt preserved)")

    def cleanup_old_archives(self, days_to_keep: int = 7):
        """
        Delete archive files older than specified days.
        
        Args:
            days_to_keep: Number of days to keep archive files (default: 7)
        """
        import time
        cutoff_time = time.time() - (days_to_keep * 86400)
        archive_files = list(self.workspace_dir.glob("archive_*.json"))
        deleted_count = 0
        
        for archive_file in archive_files:
            try:
                if archive_file.stat().st_mtime < cutoff_time:
                    archive_file.unlink()
                    deleted_count += 1
            except Exception as e:
                print(f"✗ Failed to delete {archive_file.name}: {e}")
        
        if deleted_count > 0:
            print(f"✓ Cleaned up {deleted_count} old archive files")
        else:
            print("✓ No old archive files to clean up")
    
    # ========== Shared Memory Methods ==========
    
    def update_shared_memory(self, key: str, value: Any):
        """更新共享内存（用于SubAgent间通信）"""
        self.shared_memory[key] = value
        print(f"✓ Updated shared_memory: {key}")
    
    def get_shared_memory(self, key: str, default: Any = None) -> Any:
        """获取共享内存中的值"""
        return self.shared_memory.get(key, default)
    
    def get_snapshot(self) -> Dict[str, Any]:
        """获取Context快照（供SubAgent使用）"""
        # 获取用户请求（最后一条user消息）
        user_request = ""
        for entry in reversed(self.entries):
            if entry.role == "user" and entry.entry_type == "message":
                user_request = entry.content
                break
        
        return {
            "goals": self.get_goals(),
            "recent_entries": self.entries[-10:] if len(self.entries) > 10 else self.entries,
            "shared_memory": self.shared_memory.copy(),
            "user_request": user_request
        }
    
    def clear_shared_memory(self):
        """清空共享内存"""
        self.shared_memory.clear()
        print("✓ Shared memory cleared")
