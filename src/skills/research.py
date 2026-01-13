"""
Research Skills
Skills for researching and collecting information
"""

import asyncio
import time
from typing import Dict, Any, List
from .base import Skill, SkillResult


class ResearchSkill(Skill):
    """
    Research a topic and save findings to a file

    Combines:
    - search_google: Web search
    - file_write: Save findings
    """

    @property
    def name(self) -> str:
        return "research_topic"

    @property
    def description(self) -> str:
        return "Research a topic on the web and save comprehensive findings to a file"

    @property
    def required_tools(self) -> List[str]:
        return ["search_google", "file_write"]

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic to research"
                },
                "max_results": {
                    "type": "number",
                    "description": "Number of search results (default: 5)",
                    "default": 5
                },
                "output_file": {
                    "type": "string",
                    "description": "File to save research findings (default: research_results.md)",
                    "default": "research_results.md"
                }
            },
            "required": ["topic"]
        }

    async def execute(self, tools: Dict[str, Any], **kwargs) -> SkillResult:
        """Execute research skill"""
        start_time = time.time()
        steps = []

        # Extract parameters
        topic = kwargs.get("topic", "")
        max_results = kwargs.get("max_results", 5)
        output_file = kwargs.get("output_file", "research_results.md")

        if not topic:
            return self._create_error_result(
                errors=["Missing required parameter: topic"],
                steps=[],
                summary="Research failed: no topic provided",
                duration_ms=0
            )

        # Validate tools
        try:
            self.validate_tools(tools)
        except ValueError as e:
            return self._create_error_result(
                errors=[str(e)],
                steps=[],
                summary=f"Validation failed: {e}",
                duration_ms=0
            )

        # Step 1: Search for information
        steps.append({
            "step": 1,
            "action": "search_google",
            "description": f"Searching for '{topic}'"
        })

        search_tool = tools["search_google"]
        search_result = await search_tool.execute(query=topic, max_results=max_results)

        if search_result.status != "success":
            return self._create_error_result(
                errors=[f"Search failed: {search_result.error}"],
                steps=steps,
                summary="Research failed at search step",
                duration_ms=(time.time() - start_time) * 1000
            )

        steps[0]["result"] = f"Found {len(search_result.result.get('results', []))} results"

        # Step 2: Compile findings
        steps.append({
            "step": 2,
            "action": "compile_findings",
            "description": "Compiling research findings"
        })

        results = search_result.result.get('results', [])

        if not results:
            return self._create_error_result(
                errors=["No search results found"],
                steps=steps,
                summary="Research failed: no results found",
                duration_ms=(time.time() - start_time) * 1000
            )

        # Step 3: Write to file
        steps.append({
            "step": 3,
            "action": "file_write",
            "description": f"Saving findings to {output_file}"
        })

        write_tool = tools["file_write"]

        # Format findings as markdown
        content = f"# Research Results: {topic}\n\n"
        content += f"Generated: {search_result.timestamp}\n\n"
        content += "## Findings\n\n"

        for i, result in enumerate(results, 1):
            content += f"### {i}. {result.get('title', 'N/A')}\n\n"
            content += f"**URL:** {result.get('url', 'N/A')}\n\n"
            content += f"**Summary:** {result.get('snippet', 'N/A')}\n\n"

        write_result = await write_tool.execute(filepath=output_file, content=content)

        steps[2]["result"] = f"Wrote {len(content)} characters to {output_file}"

        if write_result.status != "success":
            return self._create_error_result(
                errors=[f"Write failed: {write_result.error}"],
                steps=steps,
                summary="Research failed at write step",
                duration_ms=(time.time() - start_time) * 1000
            )

        duration_ms = (time.time() - start_time) * 1000

        return self._create_success_result(
            result={
                "topic": topic,
                "results_count": len(results),
                "output_file": output_file,
                "file_size": len(content)
            },
            steps=steps,
            summary=f"Successfully researched '{topic}' and saved {len(results)} findings to {output_file}",
            duration_ms=duration_ms
        )


class MultiTopicResearchSkill(Skill):
    """
    Research multiple topics and compile a comprehensive report

    Combines:
    - search_google: Multiple searches
    - file_write: Save compiled report
    """

    @property
    def name(self) -> str:
        return "research_multiple_topics"

    @property
    def description(self) -> str:
        return "Research multiple topics and compile a comprehensive report"

    @property
    def required_tools(self) -> List[str]:
        return ["search_google", "file_write"]

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of topics to research"
                },
                "output_file": {
                    "type": "string",
                    "description": "File to save report (default: multi_topic_report.md)",
                    "default": "multi_topic_report.md"
                }
            },
            "required": ["topics"]
        }

    async def execute(self, tools: Dict[str, Any], **kwargs) -> SkillResult:
        """Execute multi-topic research skill"""
        start_time = time.time()
        steps = []

        topics = kwargs.get("topics", [])
        output_file = kwargs.get("output_file", "multi_topic_report.md")

        if not topics:
            return self._create_error_result(
                errors=["Missing required parameter: topics"],
                steps=[],
                summary="No topics provided",
                duration_ms=0
            )

        # Validate tools
        try:
            self.validate_tools(tools)
        except ValueError as e:
            return self._create_error_result(
                errors=[str(e)],
                steps=[],
                summary=f"Validation failed: {e}",
                duration_ms=0
            )

        search_tool = tools["search_google"]
        write_tool = tools["file_write"]

        all_results = {}

        # Research each topic
        for i, topic in enumerate(topics, 1):
            step_num = len(steps) + 1
            steps.append({
                "step": step_num,
                "action": f"search_topic_{i}",
                "description": f"Researching topic {i}/{len(topics)}: '{topic}'"
            })

            search_result = await search_tool.execute(query=topic, max_results=3)

            if search_result.status == "success":
                results = search_result.result.get('results', [])
                all_results[topic] = results
                steps[-1]["result"] = f"Found {len(results)} results"
            else:
                steps[-1]["result"] = f"Search failed: {search_result.error}"
                all_results[topic] = []

        # Compile and write report
        steps.append({
            "step": len(steps) + 1,
            "action": "compile_report",
            "description": "Compiling comprehensive report"
        })

        content = "# Multi-Topic Research Report\n\n"
        content += f"Generated: {search_result.timestamp}\n\n"

        for topic, results in all_results.items():
            content += f"## {topic}\n\n"
            if results:
                for j, result in enumerate(results, 1):
                    content += f"{j}. {result.get('title', 'N/A')}\n"
                    content += f"   URL: {result.get('url', 'N/A')}\n"
                    content += f"   {result.get('snippet', 'N/A')[:80]}...\n\n"
            else:
                content += "No results found.\n\n"

        write_result = await write_tool.execute(filepath=output_file, content=content)

        duration_ms = (time.time() - start_time) * 1000

        if write_result.status != "success":
            return self._create_error_result(
                errors=[f"Write failed: {write_result.error}"],
                steps=steps,
                summary="Research completed but failed to save report",
                duration_ms=duration_ms
            )

        return self._create_success_result(
            result={
                "topics_researched": len(topics),
                "total_results": sum(len(r) for r in all_results.values()),
                "output_file": output_file,
                "file_size": len(content)
            },
            steps=steps,
            summary=f"Successfully researched {len(topics)} topics and saved to {output_file}",
            duration_ms=duration_ms
        )
