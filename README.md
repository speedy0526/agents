# Minimal Agent System

A minimal AI agent with Model + Tools + Skills + Loop + Context Engineering, based on Manus principles.

## Features

- **Model**: LLM integration (OpenAI-compatible)
- **Tools**: Search and file operations
- **Skills**: High-level workflows combining multiple tools (NEW!)
- **Loop**: Simple reasoning-action loop
- **Context Engineering**: KV-cache optimization, external memory, attention guidance

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and set your API key:

```bash
cp .env.example .env
# Edit .env with your API key
```

## Usage

```bash
python -m src.main
```

## Project Structure

```
src/
├── agent.py          # Core agent: Model + Tools + Skills + Loop + Context
├── llm.py            # LLM client
├── context.py        # Context manager with KV-cache optimization
├── main.py           # Entry point with skill examples
├── skills/           # Skills system (NEW!)
│   ├── base.py       # Skill base class
│   ├── research.py    # Research skills
│   └── __init__.py
└── tools/
    ├── base.py       # Tool base class
    ├── search_tools.py    # Web search
    └── file_tools.py     # File operations
```

## Architecture

### 1. **Model** (`src/llm.py`)
- Handles communication with language models
- Supports structured output generation
- Configurable endpoint and model

### 2. **Tools** (`src/tools/`)
- Extensible tool system
- Current tools:
  - `search_google`: Web search via DuckDuckGo (free)
  - `file_read`: Read file content
  - `file_write`: Write content to files

### 3. **Skills** (`src/skills/`) 🆕
- High-level abstractions combining multiple tools
- Current skills:
  - `research_topic`: Research a topic and save findings
  - `research_multiple_topics`: Research multiple topics and compile report
- Skills are optimized workflows for common tasks

**Tools vs Skills**:
- **Tools**: Single-purpose operations (e.g., "read file")
- **Skills**: Multi-step workflows (e.g., "research and save report")

### 4. **Loop** (`src/agent.py`)
- Thought generation
- Tool/Skill selection and execution
- Result observation
- Repeat until completion

### 5. **Context Engineering** (`src/context.py`)
- **KV-Cache Optimization**: Stable system prompt, append-only context
- **External Memory**: File system as infinite context
- **Attention Guidance**: Goals at context end to guide model
- **Error Preservation**: Keep errors for learning
- **Smart Compression**: Automatic context compression

## Context Engineering Principles

Based on Manus's experience:

1. **KV-Cache Friendly**: Stable system prompt, append-only context
2. **External Memory**: File system for persistent storage
3. **Attention Guidance**: Goals at context end to guide model
4. **Error Preservation**: Keep errors for learning and self-correction
5. **Smart Compression**: Archive old context, keep recent window

See `CONTEXT_ENGINEERING.md` for detailed explanation.

## Skills System

Skills are higher-level abstractions that combine multiple tools to execute complex workflows.

### Key Benefits

- **Efficiency**: Pre-optimized workflows, fewer agent decisions
- **Reusability**: Share skills across tasks
- **Maintainability**: Centralized logic, easy to update
- **Transparency**: Step-by-step execution tracking

### Included Skills

1. **ResearchSkill**: Research a topic and save findings
2. **MultiTopicResearchSkill**: Research multiple topics and compile report

See `SKILLS.md` for detailed documentation and how to create custom skills.

## Example

The agent can:
- Search for web information
- Read and write files
- Use skills for complex workflows
- Reason about multi-step tasks
- Maintain context across steps
- Learn from errors
- Compress context efficiently

## Advanced Usage

### Using Skills Directly

```python
from src.skills import ResearchSkill
from src.tools import SearchGoogleTool, FileWriteTool

# Create tools
tools = {
    "search_google": SearchGoogleTool(),
    "file_write": FileWriteTool()
}

# Execute skill directly
skill = ResearchSkill()
result = await skill.execute(
    tools=tools,
    topic="artificial intelligence",
    max_results=10
)

print(f"Status: {result.status}")
print(f"Summary: {result.summary}")
print(f"Steps: {len(result.steps_completed)}")
```

### Agent with Skills

```python
from src.agent import MinimalAgent
from src.tools import SearchGoogleTool, FileReadTool, FileWriteTool
from src.skills import ResearchSkill, MultiTopicResearchSkill

# Create agent with tools and skills
agent = MinimalAgent(
    tools=[SearchGoogleTool(), FileReadTool(), FileWriteTool()],
    skills=[ResearchSkill(), MultiTopicResearchSkill()]
)

# Agent will choose best approach (tools or skills)
result = await agent.run("Research AI and create comprehensive report")

# View context summary
print(agent.get_context_summary())

# Clear context
agent.clear_context()
```

### Adding Custom Skills

See `SKILLS.md` for complete guide. Quick example:

```python
from src.skills.base import Skill, SkillResult

class MySkill(Skill):
    @property
    def name(self) -> str:
        return "my_skill"

    @property
    def description(self) -> str:
        return "What this skill does"

    @property
    def required_tools(self) -> List[str]:
        return ["tool1", "tool2"]

    async def execute(self, tools: Dict[str, Any], **kwargs) -> SkillResult:
        # Implement workflow combining tools
        # Return SkillResult with steps and results
        pass

# Register with agent
agent = MinimalAgent(
    tools=[...],
    skills=[MySkill()]
)
```

## Documentation

- `README.md` - Project overview (this file)
- `QUICKSTART.md` - Quick start guide
- `CONTEXT_ENGINEERING.md` - Context engineering details
- `SKILLS.md` - Skills system documentation (NEW!)
- `MANUS_IMPLEMENTATION.md` - Context engineering implementation

## References

Inspired by Manus's blog post on Context Engineering:
https://manus.im/zh-cn/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
