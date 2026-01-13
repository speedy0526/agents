# Context Engineering for Minimal Agent

Based on Manus principles, this system implements advanced context management for efficient, scalable AI agents.

## Core Principles

### 1. KV-Cache Optimization
- **Stable System Prompt**: System messages are kept at the beginning for cacheability
- **Append-Only**: Context is only appended to, never modified (deterministic serialization)
- **Compression**: Old entries are archived to external memory, preserving recent context

### 2. External Memory
- **File System**: Used as "infinite context" for persistent storage
- **Workspace**: Contains session data, goals, error logs, and archives
- **Reversible Compression**: Archived data can be restored if needed

### 3. Attention Guidance
- **Goals Tracking**: Current goals are added at the end of context to guide model attention
- **Dynamic Updates**: Goals can be updated during long tasks
- **Priority Focus**: Keeps the model focused on user objectives

### 4. Error Preservation
- **Learning from Errors**: Failed tool calls are preserved in context
- **Error Logs**: Errors are logged to external memory for analysis
- **Self-Correction**: Model can use error history to adjust behavior

### 5. Tool Management
- **Masking Instead of Removal**: Tools are never removed from context to avoid cache invalidation
- **Stable Descriptions**: Tool descriptions remain constant
- **Prefix-Based Naming**: Tools use consistent prefixes for potential logit masking

## Architecture

```
ContextManager
├── Session Context
│   ├── System messages (stable prefix)
│   ├── User/Assistant messages
│   ├── Tool results and thoughts
│   └── Goals (attention guidance)
├── External Memory
│   ├── session_context.json (persistent context)
│   ├── goals.md (current objectives)
│   ├── errors.md (learning history)
│   └── archive_*.json (archived entries)
└── Compression
    ├── Keep system prompt (stable)
    ├── Keep recent entries (attention window)
    └── Archive old entries (external memory)
```

## Usage

### Basic Usage

```python
from src.agent import MinimalAgent
from src.tools import SearchGoogleTool, FileReadTool, FileWriteTool

# Create agent with context management
agent = MinimalAgent(
    tools=[SearchGoogleTool(), FileReadTool(), FileWriteTool()],
    workspace_dir="workspace"
)

# Run with automatic context management
result = await agent.run("Search for Python tutorials and save to file")
```

### Manual Context Control

```python
# View context summary
print(agent.get_context_summary())

# Clear context (keep system prompt)
agent.clear_context()

# Access context manager directly
agent.context.set_goals([
    "Goal 1: Complete task",
    "Goal 2: Ensure accuracy"
])

# Compress manually if needed
agent.context.compress_if_needed()
```

## Context Lifecycle

```
1. Initialization
   └─ Load existing session from workspace/
   └─ Add stable system prompt

2. Task Start
   ├─ Add user request to context
   ├─ Set initial goals
   └─ Display context summary

3. Loop (per step)
   ├─ Compress if needed
   ├─ Think (using context + goals)
   ├─ Add thought to context
   ├─ Execute tool
   ├─ Add tool result (or error) to context
   └─ Check completion

4. Completion
   ├─ Add final response to context
   ├─ Save session to external memory
   └─ Return result
```

## Performance Benefits

### KV-Cache Hit Rate
- **High**: System prompt and recent entries are consistently cached
- **Stable**: No timestamp variations or modifications to invalidate cache
- **Efficient**: Only new content needs recomputation

### Memory Efficiency
- **Context Window**: Fixed size (default: 8000 chars)
- **External Memory**: Unlimited storage in file system
- **Smart Archival**: Old data is moved, not deleted

### Cost Reduction
- **Reduced Input**: Compressed context means fewer tokens
- **Better Caching**: Higher cache hit rates lower compute costs
- **Efficient Loops**: Fewer unnecessary tool calls

## Workspace Structure

```
workspace/
├── session_context.json     # Current session state
├── goals.md                # Active objectives
├── errors.md               # Error history (for learning)
└── archive_*.json          # Compressed context snapshots
```

## Best Practices

### 1. Stable Prompts
```python
# Good: Stable system prompt
system_prompt = "You are a helpful AI agent..."

# Bad: Dynamic elements that change frequently
system_prompt = f"Current time: {datetime.now()}..."
```

### 2. Incremental Updates
```python
# Good: Append to context
context.add_user_request("New task")

# Bad: Modify existing entries
context.entries[0].content = "Modified..."
```

### 3. Goal Management
```python
# Good: Set clear, actionable goals
agent.context.set_goals([
    "Search for information",
    "Summarize findings",
    "Save to file"
])

# Good: Update goals as task progresses
agent.context.set_goals([
    "Complete remaining tasks",
    "Finalize report"
])
```

### 4. Error Handling
```python
# Good: Preserve errors for learning
if result.status == "failed":
    context.add_tool_result(
        tool_name="search",
        result=str(e),
        is_error=True  # Preserved in context and error log
    )

# Bad: Hide errors
if result.status == "failed":
    context.add_tool_result(tool_name="search", result="Nothing to see here")
```

## Comparison: Before vs After

### Before (Simple History)
```python
history = [
    {"role": "user", "content": "task"},
    {"role": "assistant", "content": "response 1"},
    {"role": "assistant", "content": "response 2"},
    # ... grows unbounded
]
```

**Issues:**
- No compression mechanism
- Errors are hidden or lost
- No attention guidance
- Poor cache utilization

### After (Context Engineering)
```python
ContextManager
├── System prompt (stable, cached)
├── Recent entries (10 most recent)
├── Goals (attention guidance)
├── External memory (workspace/)
│   ├── Archived entries (reversible)
│   ├── Error logs (learning)
│   └── Session persistence
```

**Benefits:**
- Automatic compression
- Error preservation
- Attention guidance
- Better cache hit rates

## References

This implementation is inspired by Manus's blog post:
https://manus.im/zh-cn/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus

Key takeaways:
- Context engineering is experimental science
- Iterate and measure
- Focus on KV-cache optimization
- Use external memory wisely
- Preserve errors for learning
- Guide attention with goals
