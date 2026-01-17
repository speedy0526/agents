# Quick Start Guide

## Project Structure

```
listen-train/
├── .env                # Environment variables (create from .env.example)
├── .env.example         # Example configuration
├── README.md            # Project documentation
├── CONTEXT_ENGINEERING.md # Context engineering details
├── SKILLS.md            # Skills system documentation (NEW!)
├── requirements.txt     # Python dependencies
└── src/
    ├── agent.py         # Core agent: Model + Tools + Skills + Loop + Context
    ├── llm.py           # LLM client
    ├── context.py       # Context manager (KV-cache optimization)
    ├── main.py          # Entry point
    ├── skills/           # Skills system (NEW!)
    │   ├── base.py       # Skill base class
    │   ├── research.py    # Research skills
    │   └── __init__.py
    └── tools/
        ├── base.py      # Tool base class
        ├── search_tools.py   # Web search tool
        └── file_tools.py    # File read/write tools
```

## Architecture

### 1. **Model (LLM)** - `src/llm.py`
- Handles communication with OpenAI-compatible APIs
- Supports structured output generation
- Configurable endpoint and model

### 2. **Tools** - `src/tools/`
- Extensible tool system
- Current tools:
  - `search_google`: Web search via DuckDuckGo (free, no API key)
  - `file_read`: Read file content
  - `file_write`: Write content to files

### 3. **Skills** - `src/skills/` 🆕
- **ResearchSkill**: Research a topic and save findings to file
- **MultiTopicResearchSkill**: Research multiple topics and compile report

**Skills vs Tools**:
- **Tools** = Single operations (e.g., "read file")
- **Skills** = Multi-step workflows (e.g., "research and save report")

Benefits of skills:
- Faster execution (optimized workflows)
- Better reliability (tested implementations)
- Less agent overhead (pre-planned steps)

### 4. **Loop** - `src/agent.py`
- Thought generation
- Tool/Skill selection and execution
- Result observation
- Repeat until completion

### 5. **Context Engineering** - `src/context.py`
- **KV-Cache Optimization**: Stable system prompt, append-only context
- **External Memory**: File system as infinite context
- **Attention Guidance**: Goals to keep model focused
- **Error Preservation**: Keep errors for learning
- **Automatic Compression**: Smart context compression

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run agent
python -m src.main
```

## Usage

### Basic Usage (with Skills)

```bash
python -m src.main
```

The agent will demonstrate:
1. Researching a single topic using `ResearchSkill`
2. Researching multiple topics using `MultiTopicResearchSkill`

### Using Skills Directly

```python
import asyncio
from src.skills import ResearchSkill
from src.tools import SearchGoogleTool, FileWriteTool

async def main():
    # Create tools
    tools = {
        "search_google": SearchGoogleTool(),
        "file_write": FileWriteTool()
    }

    # Create skill
    skill = ResearchSkill()

    # Execute skill
    result = await skill.execute(
        tools=tools,
        topic="artificial intelligence",
        max_results=5,
        output_file="ai_research.md"
    )

    print(f"Status: {result.status}")
    print(f"Summary: {result.summary}")
    print(f"Steps: {len(result.steps_completed)}")

    # Review execution steps
    for step in result.steps_completed:
        print(f"\n  Step {step['step']}: {step['action']}")
        print(f"    {step['description']}")

asyncio.run(main())
```

### Using Agent with Skills

```python
import asyncio
from src.agent import MinimalAgent
from src.tools import SearchGoogleTool, FileReadTool, FileWriteTool
from src.skills import ResearchSkill, MultiTopicResearchSkill

async def main():
    # Create agent with tools and skills
    agent = MinimalAgent(
        tools=[SearchGoogleTool(), FileReadTool(), FileWriteTool()],
        skills=[ResearchSkill(), MultiTopicResearchSkill()]
    )

    # Agent will choose best approach (tools or skills)
    result = await agent.run(
        "Research machine learning and write a comprehensive report"
    )

    print(f"Result: {result}")

asyncio.run(main())
```

## Adding Custom Skills

### Step 1: Create Skill Class

```python
# src/skills/my_skills.py
from src.skills.base import Skill, SkillResult
from typing import Dict, Any, List
import time

class MyCustomSkill(Skill):
    @property
    def name(self) -> str:
        return "my_custom_skill"

    @property
    def description(self) -> str:
        return "Describe what this skill does in one sentence"

    @property
    def required_tools(self) -> List[str]:
        return ["tool1", "tool2"]  # Tools this skill needs

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "Description of param1"
                }
            },
            "required": ["param1"]
        }

    async def execute(self, tools: Dict[str, Any], **kwargs) -> SkillResult:
        start_time = time.time()
        steps = []

        # Step 1: Use tool1
        steps.append({
            "step": 1,
            "action": "use_tool1",
            "description": "First step description"
        })

        result1 = await tools["tool1"].execute(...)

        if result1.status != "success":
            return self._create_error_result(
                errors=[f"Tool1 failed: {result1.error}"],
                steps=steps,
                summary="Skill failed at step 1",
                duration_ms=(time.time() - start_time) * 1000
            )

        steps[0]["result"] = "Completed successfully"

        # Step 2: Use tool2
        steps.append({
            "step": 2,
            "action": "use_tool2",
            "description": "Second step description"
        })

        result2 = await tools["tool2"].execute(...)

        # Return success
        duration_ms = (time.time() - start_time) * 1000
        return self._create_success_result(
            result={"param1": kwargs.get("param1")},
            steps=steps,
            summary="Skill completed successfully",
            duration_ms=duration_ms
        )
```

### Step 2: Import and Register

```python
# src/main.py or your application
from src.skills import MyCustomSkill

# Create agent with your skill
agent = MinimalAgent(
    tools=[...],  # Include required tools
    skills=[MyCustomSkill()]
)
```

## Context Management

### Automatic Compression

When context grows too large (>8000 chars), agent automatically:
- Keeps system prompt (stable, cacheable)
- Keeps recent entries (attention window)
- Archives old entries to external memory (reversible)
- Updates goals for attention guidance

### Workspace Structure

```
workspace/
├── session_context.json     # Current session state
├── goals.md                # Active objectives
├── errors.md               # Error history (for learning)
└── archive_*.json          # Compressed context snapshots
```

### Manual Context Control

```python
# View context summary
print(agent.get_context_summary())

# Clear context (keep system prompt)
agent.clear_context()

# Set specific goals
agent.context.set_goals([
    "Research topic thoroughly",
    "Summarize findings",
    "Write comprehensive report"
])

# Access context manager directly
agent.context.compress_if_needed()
```

## Example Tasks

### Using Skills

1. **Single Topic Research**:
   "Research 'Python programming' and save findings"

   → Agent uses `ResearchSkill` (optimized workflow)

2. **Multi-Topic Research**:
   "Research these topics: AI, ML, Deep Learning"

   → Agent uses `MultiTopicResearchSkill` (single workflow for all topics)

### Using Tools

3. **Custom Workflow**:
   "Read README.md, extract specific info, and create summary"

   → Agent plans and uses tools individually

## Benefits of Skills

### Performance
- **Faster Execution**: Pre-planned workflows, no agent decision overhead
- **Better Caching**: Stable skill execution patterns

### Reliability
- **Tested Workflows**: Skills are verified implementations
- **Error Handling**: Comprehensive error recovery within skills

### Maintainability
- **Centralized Logic**: Complex workflows in one place
- **Easy Updates**: Change skill implementation, not agent

### Transparency
- **Step Tracking**: Detailed execution history
- **Clear Results**: Well-defined output format

## Testing

### Test Skills

```bash
# Run skill tests
python3 test_skills.py
```

Tests verify:
- Skill import and creation
- Tool validation
- Parameter validation
- Execution with real tools
- Result structure
- Error handling

## Troubleshooting

### Import Errors
```bash
# Ensure dependencies are installed
pip install -r requirements.txt
```

### API Key Issues
```bash
# Check .env file
cat .env
# Should see: OPENAI_API_KEY=your_key_here
```

### Skill Errors
```bash
# Check if required tools are available
# Skills validate tools before execution
```

## Documentation

- `README.md` - Project overview
- `QUICKSTART.md` - This file (quick start guide)
- `CONTEXT_ENGINEERING.md` - Context engineering details
- `SKILLS.md` - Skills system documentation (NEW!)
- `MANUS_IMPLEMENTATION.md` - Context engineering implementation

## Skill Ideas

Potential skills to implement:

1. **AnalyzeDocumentSkill**: Read and analyze documents
2. **GenerateReportSkill**: Create professional reports
3. **CodeReviewSkill**: Review and analyze code
4. **DataProcessingSkill**: Process and transform data
5. **WebCrawlSkill**: Crawl and compile web data

See `SKILLS.md` for implementation guide.

## References

### Context Engineering
Based on Manus principles:
https://manus.im/zh-cn/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus

Key principles:
- KV-cache friendly design
- External memory for infinite context
- Attention guidance with goals
- Error preservation for learning
- Automatic context compression

### Skills System
Skills provide higher-level abstractions:
- Combine multiple tools
- Execute optimized workflows
- Improve efficiency and reliability
