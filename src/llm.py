"""
Minimal Agent System
LLM Client with structured output support
"""

import os
from typing import Dict, Any, Optional, Type
from openai import AsyncOpenAI
from pydantic import BaseModel
import json
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    """Simplified LLM client"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        )
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        print(f"""
Using model: {self.model}
Using API key: {'set' if self.client.api_key else 'not set'}
Using base URL: {self.client.base_url}
        """)

    async def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send chat completion request"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice
        )
        return response

    async def generate_structured(
        self,
        messages: list[dict],
        response_model: Type[BaseModel]
    ) -> BaseModel:
        """Generate structured output"""
        schema = response_model.model_json_schema()
        schema_str = json.dumps(schema, indent=2)

        messages.append({
            "role": "system",
            "content": f"Respond with valid JSON matching this schema:\n{schema_str}"
        })

        response = await self.chat(messages)

        content = response.choices[0].message.content
        if content:
            return response_model.model_validate_json(content)

        # Try to extract JSON from tool calls
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            if tool_call.function.arguments:
                return response_model.model_validate_json(tool_call.function.arguments)

        raise ValueError("Failed to generate structured output")
