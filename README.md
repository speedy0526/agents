# Minimal Agent System

A minimal AI agent with Model + Tools + Skills + Loop + Context Engineering + Agent-SubAgent Architecture, based on Manus principles.

## Features

- **Model**: LLM integration (OpenAI-compatible)
- **Tools**: Search and file operations
- **Skills**: High-level workflows combining multiple tools (Prompt-Based)
- **SubAgents**: Independent execution contexts for skills and chains
- **Loop**: Simple reasoning-action loop
- **Context Engineering**: KV-cache optimization, external memory, attention guidance

## Installation

```bash
python3 -m pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and set your API key:

```bash
cp .env.example .env
# Edit .env with your API key
```

## Usage

```bash
python3 -m src.main
```

## Project Structure

```
src/
├── agent.py          # Core agent: Model + Tools + Skills + Loop + Context
├── llm.py            # LLM client with streaming and retry logic
├── context.py        # Context manager with KV-cache optimization
├── main.py           # Entry point
├── skills/           # Prompt-Based Skills system
│   ├── models.py     # Skill data models
│   ├── loader.py     # Skill loader from SKILL.md files
│   ├── manager.py    # Skill manager (meta-tool)
│   └── context.py    # Skill context management
├── subagents/        # Agent-SubAgent architecture
│   ├── base.py       # SubAgent base class
│   ├── skill_subagent.py    # Skill execution
│   ├── tool_subagent.py     # Tool execution
│   ├── chain_subagent.py    # Chain execution
│   └── skill_result.py      # Skill result model
└── tools/
    ├── base.py       # Tool base class
    ├── search_tools.py    # Web search (DuckDuckGo)
    └── file_tools.py     # File operations

skills/                 # Skill definitions (SKILL.md)
├── research/          # Web research skill
├── planning-with-files/  # File-based planning skill
├── structured-decision-research/  # Decision research skill
└── pdf/              # PDF processing skill
```

## Architecture Overview

### 1. **LLM Client** (`src/llm.py`)

Pure LLM client focused on API communication only.

**Core Features**:
- Structured output generation (JSON format)
- Streaming response support with real-time output
- Retry mechanism with exponential backoff
- Rate limit handling
- JSON extraction with multiple strategies
- Concurrent request control (semaphore)

**Key Methods**:
- `chat()`: Send chat completion request
- `_stream_chat()`: Handle streaming responses
- `generate_structured()`: Generate structured output matching Pydantic models
- `_extract_json()`: Extract JSON from text (direct, markdown, balanced braces)

**Configuration** (via `.env`):
```
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_CONCURRENT=1
OPENAI_MAX_RETRIES=3
OPENAI_BASE_DELAY=1.0
```

### 2. **Tools System** (`src/tools/`)

Extensible tool system with base class and concrete implementations.

**BaseTool** (`base.py`):
- Abstract base class defining tool interface
- `ToolResult` encapsulates execution results
- Factory methods: `success()` and `error()`

**Available Tools**:
- `SearchGoogleTool`: Web search via DuckDuckGo (free, no API key)
- `FileReadTool`: Read file content
- `FileWriteTool`: Write content to files

**Tool Interface**:
```python
class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """Tool parameters schema"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute tool"""
        pass
```

### 3. **Skills System** (`src/skills/`)

**Prompt-Based Meta-Tool Architecture** based on Claude Agent Skills design principles.

**Core Components**:

**SkillLoader** (`loader.py`):
- Loads skills from directories
- Parses `SKILL.md` files with frontmatter
- Extracts metadata (name, version, allowed tools, etc.)

**SkillManager** (`manager.py`):
- Acts as "meta-tool" managing all skills
- Provides skill descriptions to LLM for matching
- Handles skill invocation and context injection
- Implements progressive disclosure

**SkillContextManager** (`context.py`):
- Manages skill-specific context
- Filters available tools based on skill's `allowed-tools`
- Generates context messages (system prompt + user request)

**Skill Definition Format** (SKILL.md):
```yaml
---
name: research
description: Research a topic on the web...
version: 1.0.0
allowed-tools: search_google, file_write
---

# Research Skill
You are a research assistant...

## <WORKFLOW> Research Workflow

Follow this step-by-step process:

### Step 1: Search for Information
Use `search_google` tool...

### Step 2: Compile Findings
Process search results...

### Step 3: Format as Markdown
Create a well-structured markdown document...

### Step 4: Save to File
Use `file_write` tool...

## <BEST_PRACTICES> Research Guidelines
...

## <ERROR_HANDLING> What to Do If...
...

## Examples
...
```

**Available Skills**:
- `research`: Web research and save as Markdown
- `planning-with-files`: File-based planning with templates
- `structured-decision-research`: Structured decision-making research
- `pdf`: PDF processing and analysis

**Tools vs Skills**:
- **Tools**: Single-purpose operations (e.g., "read file")
- **Skills**: Multi-step workflows (e.g., "research and save report")

### 4. **SubAgents** (`src/subagents/`)

**Agent-SubAgent Architecture** with strict separation of concerns.

**SubAgent** (`base.py`):
- Abstract base class defining `execute()` protocol
- `SubAgentResult` unified result format
- Each SubAgent has **independent context**

**Concrete Implementations**:

**SkillSubAgent** (`skill_subagent.py`):
- Receives Agent context snapshot (read-only)
- Creates independent `ContextManager`
- Loads skill prompt into its own context
- Runs complete LLM loop to execute skill
- Returns `SkillResult`

**ToolSubAgent** (`tool_subagent.py`):
- Executes direct tool calls
- Wraps tool results as `SubAgentResult`

**ChainSubAgent** (`chain_subagent.py`):
- Executes multiple steps in sequence
- Supports chaining of operations

**Key Features**:
- ✅ One-way dependency: SubAgent only depends on Agent's snapshot
- ✅ Responsibility separation: Agent (planning) vs SubAgent (execution)
- ✅ Context isolation: SubAgent execution doesn't affect Agent

**Dependency Flow**:
```
Agent Context (clean)
    ↓ Pass snapshot (read-only)
SubAgent Context (independent)
    ↓ Return result
Agent Context (still clean) ← No SubAgent internal details
```

### 5. **Context Manager** (`src/context.py`)

**KV-Cache Optimized Context Management** based on Manus principles.

**Core Principles**:
1. **Stable Prefix**: System prompt always at start
2. **Append-Only**: No modifications to avoid cache invalidation
3. **External Memory**: File system as infinite context
4. **Attention Guidance**: Goals at context end to guide model
5. **Error Preservation**: Keep errors for learning

**Key Methods**:
- `add_system_prompt()`: Add system prompt (highest priority)
- `add_user_request()`: Add user request
- `add_assistant_response()`: Add assistant response
- `add_tool_result()`: Add tool result (preserves errors)
- `add_thought()`: Add reasoning process
- `compress_if_needed()`: Automatic context compression
- `get_messages()`: Get messages for LLM
- `get_snapshot()`: Get snapshot for SubAgent
- `update_shared_memory()`: Shared memory for SubAgent communication

**Automatic Compression Strategy**:
```
1. Keep system prompt (stable, cacheable)
2. Keep last N entries (attention window, default: 20)
3. Archive old entries to external file (reversible)
4. Update goals for attention guidance
```

**Workspace Structure**:
```
workspace/session_<id>/
├── session_context.json  # Current session state
├── goals.md             # Active objectives
├── errors.md            # Error history (for learning)
└── archive_*.json       # Compressed context snapshots
```

### 6. **Core Agent** (`src/agent.py`)

**Thought Model**:
```python
class Thought(BaseModel):
    reasoning: str                    # Current reasoning
    next_action: str                 # Next action type
    tool_name: Optional[str]         # Tool name (for use_tool)
    tool_parameters: Optional[Dict]   # Tool parameters (for use_tool)
    subagent_type: Optional[str]     # SubAgent type (for use_skill/call_chain)
    subagent_command: Optional[str]   # SubAgent command/skill name
```

**Action Types**:
- `use_tool`: Execute a direct tool
- `use_skill`: Execute a skill via SkillSubAgent
- `call_chain`: Execute a chain via ChainSubAgent
- `think`: Continue reasoning
- `respond_to_user`: Provide response to user
- `finish`: Task complete

**Core Flow**:

1. **think()** - Generate Thought:
   - Get messages from ContextManager
   - Insert output format instruction
   - Call LLM to generate Thought
   - Add to context

2. **execute_subagent()** - Execute SubAgent:
   - Get context snapshot
   - Create SubAgent based on Thought
   - Execute and return result
   - Only add summary to Agent context

3. **run()** - Main Loop:
   ```python
   Initialize ContextManager
   Add system prompt
   Add user request
   Set goals

   Loop (max_steps):
     Compress context if needed
     think() → Generate Thought

     if next_action == 'finish':
       Return final result

     execute_subagent() → Execute SubAgent

     Check task completion
   ```

## Complete Execution Flow

### Full Workflow

```
User Request → Agent.run()
               ↓
        Initialize ContextManager
               ↓
        think() → Generate Thought
               ↓
        execute_subagent()
               ↓
    [Branch 1] use_tool
               ↓
        ToolSubAgent.execute()
               ↓
        Execute tool
               ↓
        Return result

    [Branch 2] use_skill
               ↓
        SkillSubAgent.execute()
               ↓
        Create independent context
               ↓
        Load skill prompt
               ↓
        Run LLM loop:
          think → execute tools → observe → repeat
               ↓
        Return SkillResult
               ↓
        Agent gets summary
               ↓
        Next iteration think()
```

### Skill Execution Flow

```
1. Agent generates Thought:
   use_skill, subagent_command='research'

2. SkillSubAgent creation:
   - Get Agent context snapshot (read-only)
   - Create independent ContextManager
   - session_id: skill_research_<uuid>

3. Initialize skill context:
   - Call SkillContextManager.get_context_messages()
   - Get SKILL.md content
   - Add to SubAgent's independent context

4. Run skill loop (max 20 steps):
   - Call LLM (stream=True)
   - Parse response, extract tool calls
   - Execute tools
   - Add results to SubAgent context
   - Check completion indicators
   - Repeat until done

5. Return SkillResult:
   - Contains execution steps, file paths, errors, etc.
```

## Key Design Decisions

### 1. Agent-SubAgent Architecture

**Why needed**:
- Resolve skill prompt interference with Agent Thought generation
- Achieve responsibility separation
- Avoid complex message filtering logic

**Implementation**:
```python
async def execute_subagent(self, thought: Thought):
    snapshot = self.context.get_snapshot()  # Read-only snapshot

    # Create SubAgent dynamically
    subagent = SkillSubAgent(snapshot, skill_manager, skill_name)
    result = await subagent.execute(...)

    # Only get summary, not internal details
    self.context.add_assistant_response(result.summary)
```

### 2. Prompt-Based Skills

**Why use prompts instead of code**:
- More flexible, no redeployment needed
- Easy to maintain and modify
- Matches Claude Agent Skills design
- Supports progressive disclosure

**Advantages**:
- Skills defined in Markdown files
- Can include examples, best practices, error handling
- Supports resource bindings (scripts, references, templates)

### 3. KV-Cache Optimization

**Key Design**:
- System prompt always at start (stable)
- Append-only modifications (cacheable)
- Goals at the end (attention guidance)
- Automatic compression (external memory)

**Effects**:
- Reduced token consumption
- Faster response times
- Support for long conversations

### 4. Shared Memory

**Purpose**:
- Communication between SubAgents
- Mark task states (has_tangible_results)
- Pass metadata

**Implementation**:
```python
self.context.update_shared_memory("has_tangible_results", True)
value = self.context.get_shared_memory("has_tangible_results")
```

## Usage Scenarios

### 1. Web Research

```
User: "Research AI trends in 2024"
Agent: Use research skill
      → Search → Compile → Save report
Output: research_results.md
```

### 2. File-Based Planning

```
User: "Plan a training course"
Agent: Use planning-with-files skill
      → Analyze requirements → Create plan → Save files
Output: task_plan.md, progress.md, findings.md
```

### 3. Custom Workflows

```
User: "Read README, extract info, create summary"
Agent: Use tool combination
      → file_read → Analyze → file_write
Output: summary.md
```

## Context Engineering Principles

Based on Manus's experience:

1. **KV-Cache Friendly**: Stable system prompt, append-only context
2. **External Memory**: File system for persistent storage
3. **Attention Guidance**: Goals at context end to guide model
4. **Error Preservation**: Keep errors for learning and self-correction
5. **Smart Compression**: Archive old context, keep recent window

## Key Features

### Advantages

1. **Clear Architecture**: Layered design, well-separated responsibilities
2. **Extensible**: Easy to add tools and skills
3. **Efficient**: KV-Cache optimization, context compression
4. **Flexible**: Prompt-based skills, easy to modify
5. **Reliable**: Error preservation, retry mechanisms
6. **Testable**: Independent SubAgent testing

### Design Patterns

1. **Strategy Pattern**: Different SubAgent implementations
2. **Factory Pattern**: ToolResult creation
3. **Template Method**: BaseTool interface
4. **Observer Pattern**: Context monitoring
5. **Command Pattern**: Thought execution

## Advanced Usage

### Using Skills Directly

```python
from src.skills import SkillManager
from src.tools import SearchGoogleTool, FileWriteTool

# Create tools
tools = {
    "search_google": SearchGoogleTool(),
    "file_write": FileWriteTool()
}

# Create skill manager
skill_manager = SkillManager(skills_dirs=["skills"])

# Invoke skill directly
context_messages, error = skill_manager.invoke(
    command="research",
    user_request="Research AI",
    tools_available=tools
)
```

### Agent with Skills

```python
from src.agent import MinimalAgent
from src.tools import SearchGoogleTool, FileReadTool, FileWriteTool

# Create agent with tools and skills directories
agent = MinimalAgent(
    tools=[SearchGoogleTool(), FileReadTool(), FileWriteTool()],
    skills_dirs=["skills"]
)

# Agent will choose best approach (tools or skills)
result = await agent.run("Research AI and create comprehensive report")

# View context summary
print(agent.get_context_summary())

# Clear context
agent.clear_context()
```

### Creating Custom Skills

Create a new skill directory with `SKILL.md`:

```bash
mkdir skills/my-skill
```

**`skills/my-skill/SKILL.md`**:
```yaml
---
name: my-skill
description: Describe what this skill does
version: 1.0.0
allowed-tools: search_google, file_write
---

# My Skill

You are a specialized assistant...

## <WORKFLOW> My Workflow

Follow this step-by-step process:

### Step 1: Do something
Use `tool_name` to...

### Step 2: Process results
...

### Step 3: Save output
Use `file_write` to save...

## <BEST_PRACTICES> Guidelines
...

## <ERROR_HANDLING> What to Do If...
...

## Examples
...
```

The skill will be automatically loaded by `SkillManager`.

## Technical Stack

- **Language**: Python 3.14+
- **Data Validation**: Pydantic
- **API Client**: OpenAI (AsyncOpenAI)
- **Search**: DuckDuckGo (ddgs)
- **Dependency Management**: uv

## Documentation

- `README.md` - Project overview (this file)
- `QUICKSTART.md` - Quick start guide
- `REFACTORING_SUMMARY.md` - Agent-SubAgent architecture refactoring details
- `CONTEXT_ENGINEERING.md` - Context engineering details
- `SKILLS.md` - Skills system documentation

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_e2e.py::test_research_workflow_end_to_end

# Run with coverage
pytest --cov=src tests/
```

## References

Inspired by Manus's blog post on Context Engineering:
https://manus.im/zh-cn/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus

## Summary

This is a **well-designed Agent system** with key highlights:

1. **True Agent-SubAgent Architecture**: Responsibility separation, context isolation
2. **Prompt-Based Skills**: Flexible and maintainable
3. **KV-Cache Optimization**: Efficient, token-saving
4. **External Memory**: Supports long conversations
5. **Automation**: Automatic compression, error handling

The project has high code quality, clear architecture, and serves as an excellent reference implementation or foundation for Agent systems.
