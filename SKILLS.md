# Skills System - Prompt-Based Architecture

Based on Claude Agent Skills design principles from [Deep Dive into Claude Skills](https://baoyu.io/translations/claude-skills-deep-dive).

## Overview

The Skills System is a **prompt-based meta-tool architecture** that extends Claude's capabilities through carefully crafted instructions and resource bindings. Unlike traditional code-based approaches, skills are defined as Markdown files with prompt instructions.

## Core Design Principles

### 1. Prompt-Based, Not Code-Based

Skills do not execute code. Instead, they inject specialized prompt instructions into the conversation context. This makes skills:
- **Easier to create**: Write Markdown, not Python
- **More flexible**: Prompt-based natural language instructions
- **Safer**: No code execution risks
- **Composable**: Skills can combine naturally

### 2. Meta-Tool Pattern

The system uses a **meta-tool** approach:
- **Skill tool (capital S)**: A single tool that manages all skills
- **skills (lowercase s)**: Individual skills defined as SKILL.md files

The Skill tool appears in the tools list alongside other tools like Read, Write, Bash, etc.

### 3. Progressive Disclosure

Skills follow progressive disclosure principles:
- Show minimal information initially
- Inject detailed instructions only when needed
- Keep main system prompt stable for KV-cache efficiency
- Load resources on-demand (scripts, references, assets)

### 4. Context Modification

When a skill is invoked, it modifies the conversation context:
- **User-visible message**: Brief status (e.g., "The research skill is now active")
- **Hidden message**: Full skill prompt with detailed instructions
- **Tool filtering**: Restricts available tools based on skill's `allowed-tools`
- **Resource binding**: Provides access to scripts, references, and assets

## Architecture

### Components

```
MinimalAgent
├── SkillManager (Meta-Tool)
│   ├── SkillLoader (Loads SKILL.md files)
│   ├── SkillContextManager (Injects skill prompts)
│   └── SkillRegistry (Manages available skills)
├── Tools (Read, Write, Bash, etc.)
└── ContextManager (Manages conversation context)
```

### Skill Directory Structure

Each skill is a directory containing:

```
skill-name/
├── SKILL.md              # Required: Skill definition (frontmatter + prompt)
├── scripts/              # Optional: Executable Python/Bash scripts
├── references/           # Optional: Documentation files (loaded into context)
└── assets/               # Optional: Templates and binary files (referenced only)
```

### SKILL.md Format

```markdown
---
name: skill-name
description: Brief description of what this skill does
version: 1.0.0
allowed-tools: Tool1, Tool2, Tool3
model: gpt-4-turbo
disable-model-invocation: false
---

# Skill Name

You are a [role] specialized in [domain].

## Purpose

[Brief description of what this skill does]

## When to Use

Use this skill when the user asks you to:
- [Task 1]
- [Task 2]
- [Task 3]

## Workflow

Follow this step-by-step process:

### Step 1: [Action]

[Detailed instructions]

### Step 2: [Action]

[Detailed instructions]

...

## Best Practices

[List of best practices]

## Error Handling

[How to handle errors]

## Examples

[Example usage scenarios]

## Output Format

[Format of expected output]

## Tips for Effective Execution

[Additional guidance]

## Context Variables

You have access to:
- Base directory: {baseDir}
- User request: [from invocation]
- Available tools: [list]

Use these to guide your actions.
```

### Frontmatter Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | Yes | string | Unique skill identifier |
| `description` | Yes | string | Brief description (shown in tool description) |
| `version` | No | string | Skill version (default: "1.0.0") |
| `allowed-tools` | No | string | Comma-separated list of allowed tools |
| `model` | No | string | Preferred model for this skill |
| `disable-model-invocation` | No | boolean | If true, skill can only be manually invoked |

## Skill Execution Flow

```
1. User Request
   ↓
2. Agent Thinks
   ↓
3. Agent Chooses Skill
   ↓
4. Agent Calls Skill Tool (with command: "skill-name")
   ↓
5. Skill Manager:
   - Looks up skill
   - Validates allowed-tools
   - Creates context messages
   ↓
6. Context Injection:
   - User-visible message: "The skill-name skill is now active"
   - Hidden message: [Full skill prompt from SKILL.md]
   ↓
7. Agent Continues (with enhanced context)
   ↓
8. Agent Executes Task (following skill instructions)
   ↓
9. Task Complete
```

## Resource Bindings

### scripts/

Executable automation scripts:
- Python scripts (.py)
- Bash scripts (.sh)
- Can be executed using Bash tool
- Used for complex operations

**Example:**
```python
# scripts/process_data.py
import sys

# Data processing logic
print("Processing data...")
```

### references/

Documentation loaded into context:
- Markdown files (.md)
- Text files (.txt)
- PDF files (.pdf)
- Loaded using Read tool on-demand

**Example:**
```markdown
# references/api_documentation.md

## API Reference

Detailed API documentation here...
```

### assets/

Files referenced but not loaded into context:
- Templates
- Binary files
- Images
- Accessible via paths but not auto-loaded

**Example:**
```markdown
# assets/report_template.md

Template for generating reports...
```

## Best Practices

### Writing Effective SKILL.md

1. **Keep it focused**: Main prompt under 5,000 words
2. **Use imperative mood**: "Analyze code..." not "You should analyze..."
3. **Structure clearly**: Overview → Purpose → Workflow → Examples → Tips
4. **Use {baseDir}**: Always use the {baseDir} variable for paths
5. **Provide examples**: Include concrete usage examples
6. **Handle errors**: Explicit error handling instructions
7. **Specify output**: Clear output format requirements

### Skill Design Patterns

1. **Script Automation**: Offload complex operations to scripts/
2. **Read-Process-Write**: File transformation workflows
3. **Search-Analyze-Report**: Information gathering and synthesis
4. **Guided Multi-Step**: Complex tasks broken into steps
5. **Template-Based Generation**: Output from templates in assets/

### Security

1. **Minimum Privilege**: Only include necessary tools in allowed-tools
2. **Disable Auto-Invocation**: Use `disable-model-invocation: true` for dangerous operations
3. **Validate Inputs**: Always validate user inputs in skill instructions
4. **Sanitize Paths**: Never trust file paths, always validate

## Included Skills

### Research Skill

**Location**: `skills/research/SKILL.md`

**Purpose**: Research a topic on the web, compile findings, and save to a markdown file

**Required Tools**: `search_google`, `file_write`

**Resources**:
- `references/research_tips.md`: Research best practices
- `assets/report_template.md`: Report generation template

**Usage**:
```
User: "Research artificial intelligence trends in 2024"

Agent: [Decides to use research skill]
       → Calls skill tool with command: "research"
       → Skill prompt is injected
       → Agent follows research workflow
       → Searches web, compiles findings, saves report
```

### PDF Skill

**Location**: `skills/pdf/SKILL.md`

**Purpose**: Work with PDF documents including extraction, creation, merging, and form filling

**Required Tools**: `Read`, `Write`

**Usage**:
```
User: "Extract text from document.pdf"

Agent: [Decides to use pdf skill]
       → Calls skill tool with command: "pdf"
       → Skill prompt is injected
       → Agent follows PDF processing workflow
       → Extracts text, saves to file
```

## Creating Custom Skills

### Step 1: Create Skill Directory

```bash
mkdir -p skills/my-skill/{scripts,references,assets}
```

### Step 2: Create SKILL.md

```markdown
---
name: my-skill
description: What this skill does
version: 1.0.0
allowed-tools: Tool1, Tool2
---

# My Skill

You are a [role]...

[Rest of skill content]
```

### Step 3: Add Resources (Optional)

Add scripts, references, or assets as needed.

### Step 4: Test

Restart the agent to load the new skill, then test with a user request.

## Example: Creating a Data Analysis Skill

```bash
mkdir -p skills/data-analysis/{scripts,references}
```

Create `skills/data-analysis/SKILL.md`:

```markdown
---
name: data-analysis
description: Analyze data and generate reports
version: 1.0.0
allowed-tools: Read, Write, Bash
---

# Data Analysis Skill

You are a data analyst specializing in statistical analysis and reporting.

## Purpose

Analyze data files and generate comprehensive reports.

## Workflow

1. Read the data file using Read tool
2. Load analysis script from scripts/
3. Execute analysis
4. Generate report
5. Save results

...
```

Add `scripts/analyze.py`:

```python
import pandas as pd
import sys

# Analysis logic
df = pd.read_csv(sys.argv[1])
print(df.describe())
```

## Benefits of Prompt-Based Skills

### For Users

1. **Faster Execution**: Pre-optimized workflows
2. **Better Reliability**: Tested, battle-proven patterns
3. **Clearer Results**: Structured output formats
4. **Easy to Understand**: Read SKILL.md to know what happens

### For Developers

1. **Easier to Create**: Write Markdown, not Python
2. **Easier to Modify**: Edit prompts, no code compilation
3. **Easier to Share**: Share SKILL.md files
4. **Easier to Test**: Test prompts directly in conversation

## Comparison: Old vs New Skills System

| Aspect | Old System (Code-Based) | New System (Prompt-Based) |
|--------|------------------------|---------------------------|
| **Definition** | Python classes | Markdown files |
| **Execution** | Code execution | Prompt injection |
| **Extensibility** | Requires coding | Write Markdown |
| **Complexity** | Higher | Lower |
| **Flexibility** | Limited | High |
| **Safety** | Code execution risks | No code execution |
| **Learning Curve** | Steeper | Gentler |
| **Sharing** | Code files | Simple Markdown files |

## Advanced Features

### Skill Versioning

Use the `version` field to manage skill versions:

```yaml
---
version: 2.0.0
...
```

### Model Selection

Specify preferred model for complex skills:

```yaml
---
model: gpt-4-turbo
...
```

### Tool Restrictions

Limit tools to minimum required:

```yaml
---
allowed-tools: Read, Write
...
```

### Manual Invocation Only

For dangerous operations:

```yaml
---
disable-model-invocation: true
...
```

## Troubleshooting

### Skill Not Loading

- Check SKILL.md is in correct location
- Verify frontmatter syntax (YAML between `---` lines)
- Ensure `name` field is unique

### Skill Not Working

- Read the SKILL.md to understand expected behavior
- Check if required tools are available
- Review skill execution logs

### Context Too Long

- Keep skill prompts concise (< 5,000 words)
- Use progressive disclosure
- Load references on-demand

## Resources

- [Claude Skills Deep Dive](https://baoyu.io/translations/claude-skills-deep-dive) - Original article
- SKILL.md files in `skills/` directory - Example skills
- [Manus Context Engineering](./CONTEXT_ENGINEERING.md) - Context management principles

## Summary

The new Skills System is a **prompt-based meta-tool architecture** that:

✅ Defines skills as Markdown files (SKILL.md)
✅ Uses a meta-tool (Skill tool) to manage all skills
✅ Injects skill prompts into conversation context
✅ Supports resource bindings (scripts, references, assets)
✅ Implements progressive disclosure
✅ Follows least-privilege security principles
✅ Makes skill creation accessible to non-programmers

This brings the Minimal Agent closer to Claude's native skills architecture, providing a powerful, flexible, and easy-to-use system for extending agent capabilities.
