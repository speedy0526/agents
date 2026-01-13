# Skills System

## Overview

Skills are higher-level abstractions that combine multiple tools to execute complex, multi-step workflows.

## What are Skills?

Skills are to Tools what Functions are to Instructions:
- **Tools**: Single-purpose operations (e.g., "read file", "search web")
- **Skills**: Multi-step workflows (e.g., "research topic and save report")

### Key Differences

| Aspect | Tools | Skills |
|---------|--------|---------|
| **Complexity** | Single operation | Multi-step workflow |
| **Composition** | Standalone | Combines multiple tools |
| **Abstraction** | Low-level | High-level |
| **Granularity** | Fine | Coarse |
| **Use Case** | Primitive operations | Complete workflows |

## Architecture

```
Skill
├── name              # Unique identifier
├── description        # What it does
├── required_tools    # Tools needed
├── parameters        # Input schema
└── execute()         # Implementation
    └── Returns SkillResult
        ├── status
        ├── result
        ├── steps_completed
        ├── errors
        ├── duration_ms
        └── summary
```

## Benefits

### 1. Efficiency
- Fewer decisions for the agent (use skill instead of planning)
- Optimized workflows (skill authors know best practices)
- Parallel execution within skill (no agent overhead)

### 2. Reusability
- Common workflows packaged as skills
- Share skills across tasks
- Build skill library over time

### 3. Maintainability
- Centralized logic for complex tasks
- Easier to update workflows
- Testable in isolation

### 4. Clarity
- Clear input/output contracts
- Documented step-by-step execution
- Better error handling

## Included Skills

### 1. ResearchSkill
**Purpose**: Research a topic and save findings to a file

**Tools Required**: `search_google`, `file_write`

**Parameters**:
- `topic` (string, required): Topic to research
- `max_results` (number, optional): Number of search results (default: 5)
- `output_file` (string, optional): Output file (default: `research_results.md`)

**Workflow**:
1. Search for topic on the web
2. Compile findings from search results
3. Format findings as markdown
4. Write to output file

**Example**:
```python
result = await skill.execute(
    tools=tools,
    topic="artificial intelligence",
    max_results=10,
    output_file="ai_research.md"
)
```

### 2. MultiTopicResearchSkill
**Purpose**: Research multiple topics and compile a comprehensive report

**Tools Required**: `search_google`, `file_write`

**Parameters**:
- `topics` (array of strings, required): List of topics to research
- `output_file` (string, optional): Output file (default: `multi_topic_report.md`)

**Workflow**:
1. Search for each topic
2. Compile results from all searches
3. Format as comprehensive report
4. Write to output file

**Example**:
```python
result = await skill.execute(
    tools=tools,
    topics=["AI", "Machine Learning", "Deep Learning"],
    output_file="tech_report.md"
)
```

## Creating Custom Skills

### Step 1: Inherit from Skill Base

```python
from src.skills.base import Skill, SkillResult
from typing import Dict, Any, List

class MyCustomSkill(Skill):
    @property
    def name(self) -> str:
        return "my_custom_skill"  # Use pattern: category_action

    @property
    def description(self) -> str:
        return "What this skill does"

    @property
    def required_tools(self) -> List[str]:
        return ["tool1", "tool2"]  # Tools needed
```

### Step 2: Define Parameters

```python
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "Description"
                },
                "param2": {
                    "type": "number",
                    "description": "Description",
                    "default": 10
                }
            },
            "required": ["param1"]
        }
```

### Step 3: Implement Execute Method

```python
    async def execute(self, tools: Dict[str, Any], **kwargs) -> SkillResult:
        import time
        start_time = time.time()
        steps = []

        # Extract parameters
        param1 = kwargs.get("param1", "")
        param2 = kwargs.get("param2", 10)

        # Step 1: Use tool1
        steps.append({
            "step": 1,
            "action": "use_tool1",
            "description": "Step 1 description"
        })

        result1 = await tools["tool1"].execute(...)

        if result1.status != "success":
            return self._create_error_result(
                errors=[f"Tool1 failed: {result1.error}"],
                steps=steps,
                summary="Skill failed at step 1",
                duration_ms=(time.time() - start_time) * 1000
            )

        steps[0]["result"] = "Step 1 completed"

        # Step 2: Use tool2
        steps.append({
            "step": 2,
            "action": "use_tool2",
            "description": "Step 2 description"
        })

        result2 = await tools["tool2"].execute(...)

        steps[1]["result"] = "Step 2 completed"

        # Return success
        duration_ms = (time.time() - start_time) * 1000
        return self._create_success_result(
            result={
                "param1": param1,
                "param2": param2
            },
            steps=steps,
            summary=f"Successfully completed custom skill",
            duration_ms=duration_ms
        )
```

### Step 4: Register Skill with Agent

```python
from src.agent import MinimalAgent
from src.skills import MyCustomSkill

agent = MinimalAgent(
    tools=[...],
    skills=[MyCustomSkill()]
)
```

## Best Practices

### 1. Naming Convention
- Use descriptive names: `research_topic`, `analyze_data`, `generate_report`
- Follow pattern: `category_action`
- Be specific but concise

### 2. Tool Validation
```python
# Always validate required tools
self.validate_tools(tools)  # Raises ValueError if missing
```

### 3. Step Tracking
```python
# Track each step for debugging and transparency
steps.append({
    "step": step_number,
    "action": "action_name",
    "description": "What happened",
    "result": "Outcome"  # Optional
})
```

### 4. Error Handling
```python
# Collect all errors, don't fail immediately
errors = []
if result1.status == "failed":
    errors.append(f"Step 1 failed: {result1.error}")

# Continue or return based on severity
```

### 5. Performance Tracking
```python
import time

start_time = time.time()
# ... execute skill ...
duration_ms = (time.time() - start_time) * 1000

return self._create_success_result(..., duration_ms=duration_ms)
```

## Skill Result Structure

```python
SkillResult(
    skill_name="skill_name",
    status="success",  # or "failed"
    result={...},  # Skill-specific data
    steps_completed=[...],  # Step-by-step execution
    errors=[...],  # List of errors (if any)
    timestamp="2024-01-01T00:00:00",
    summary="Human-readable summary",
    duration_ms=1234.56
)
```

## Usage Examples

### Direct Skill Execution

```python
from src.skills import ResearchSkill
from src.tools import SearchGoogleTool, FileWriteTool

# Create tools
tools = {
    "search_google": SearchGoogleTool(),
    "file_write": FileWriteTool()
}

# Create and execute skill
skill = ResearchSkill()
result = await skill.execute(
    tools=tools,
    topic="machine learning",
    max_results=5
)

print(result.summary)
print(f"Steps: {len(result.steps_completed)}")
```

### Agent with Skills

```python
from src.agent import MinimalAgent
from src.skills import ResearchSkill, MultiTopicResearchSkill

# Create agent with skills
agent = MinimalAgent(
    tools=[SearchGoogleTool(), FileWriteTool()],
    skills=[ResearchSkill(), MultiTopicResearchSkill()]
)

# Agent will choose to use skill when appropriate
result = await agent.run("Research AI and save findings")
```

## Testing Skills

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

## Future Skills Ideas

Potential skills to implement:

1. **AnalyzeDocumentSkill**
   - Read document
   - Analyze content
   - Extract key information
   - Generate summary

2. **GenerateReportSkill**
   - Collect data from multiple sources
   - Format as professional report
   - Save to file

3. **CodeReviewSkill**
   - Read code file
   - Analyze for issues
   - Suggest improvements
   - Generate review report

4. **DataProcessingSkill**
   - Read data file
   - Process/transform data
   - Save processed data

5. **WebCrawlSkill**
   - Search for multiple related queries
   - Follow relevant links
   - Compile comprehensive data

## Integration with Agent

The agent's thought process now includes:

```
1. Analyze task
2. Check if a matching skill exists
3. If yes → Use skill (faster, optimized)
4. If no → Plan and use tools individually
5. Execute chosen approach
6. Observe results
7. Repeat until complete
```

This provides:
- **Efficiency**: Skills are pre-optimized workflows
- **Reliability**: Tested skill implementations
- **Extensibility**: Easy to add new capabilities
- **Transparency**: Step-by-step execution tracking
