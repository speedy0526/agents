"""
Minimal Agent System
Pure LLM client - focused on communication only
"""

import asyncio
import json
import logging
import os
import random
import re
import time
from typing import Dict, Any, Optional, Type

from dotenv import load_dotenv
from openai import AsyncOpenAI, RateLimitError, APIError
from pydantic import BaseModel

load_dotenv()


class LLMClient:
    """Pure LLM client - handles API communication only"""

    _semaphore = None

    def __init__(self):
        # Logger setup
        self.logger = self._setup_logger()
        
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        )
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        # Settings
        self.max_concurrent = int(os.getenv("OPENAI_MAX_CONCURRENT", "1"))
        self.max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
        self.base_delay = float(os.getenv("OPENAI_BASE_DELAY", "1.0"))
        self.rate_limit_delay = float(os.getenv("OPENAI_RATE_LIMIT_DELAY", "0.5"))
        self.log_requests = os.getenv("LLM_LOG_REQUESTS", "true").lower() == "true"
        
        # Concurrency control
        if LLMClient._semaphore is None:
            LLMClient._semaphore = asyncio.Semaphore(self.max_concurrent)
        
        self._log_init_info()

    @staticmethod
    def _setup_logger() -> logging.Logger:
        """Configure and return logger instance"""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(handler)
        log_level = os.getenv("LLM_LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, log_level))
        return logger

    def _log_init_info(self):
        """Log initialization information"""
        print(f"\n{'='*60}")
        print(f"Model: {self.model}")
        print(f"Base URL: {self.client.base_url}")
        print(f"Max concurrent: {self.max_concurrent}")
        print(f"{'='*60}\n")

    async def _make_request(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str] = None,
        response_format: Optional[dict] = None
    ) -> Dict[str, Any]:
        """Make API request with retry logic"""
        for attempt in range(self.max_retries + 1):
            try:
                async with LLMClient._semaphore:
                    await asyncio.sleep(self.rate_limit_delay)
                    
                    params = {"model": self.model, "messages": messages}
                    if tools is not None:
                        params["tools"] = tools
                    if tool_choice is not None:
                        params["tool_choice"] = tool_choice
                    if response_format is not None:
                        params["response_format"] = response_format
                    
                    return await self.client.chat.completions.create(**params)
                    
            except RateLimitError as e:
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                    self.logger.warning(f"Rate limited, retry {attempt + 1}/{self.max_retries} after {delay:.2f}s")
                    await asyncio.sleep(delay)
                raise
            except APIError as e:
                if attempt < self.max_retries and e.status_code >= 500:
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                    self.logger.warning(f"API error {e.status_code}, retry {attempt + 1}/{self.max_retries}")
                    await asyncio.sleep(delay)
                raise
            except Exception as e:
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                    self.logger.warning(f"Error: {e}, retry {attempt + 1}/{self.max_retries}")
                    await asyncio.sleep(delay)
                raise

    async def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str] = None,
        response_format: Optional[dict] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Send chat completion request"""
        start = time.time()
        try:
            if stream:
                return await self._stream_chat(messages, tools, tool_choice, response_format)
            else:
                response = await self._make_request(messages, tools, tool_choice, response_format)
                duration = time.time() - start
                choice = response.choices[0]
                self.logger.info(f"Chat success: {duration:.2f}s, finish={choice.finish_reason}")
                if self.log_requests and choice.message.content:
                    self.logger.debug(f"Response: {choice.message.content[:200]}...")
                return response
        except Exception as e:
            duration = time.time() - start
            self.logger.error(f"Chat failed: {messages} {duration:.2f}s, error: {e}")
            raise

    async def _stream_chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str] = None,
        response_format: Optional[dict] = None
    ) -> Dict[str, Any]:
        """Stream chat completion and print chunks in real-time"""
        print(f"\n{'='*60}")
        print("🤖 LLM Streaming Response")
        print(f"{'='*60}\n")
        
        full_content = ""
        start = time.time()
        
        try:
            async with LLMClient._semaphore:
                await asyncio.sleep(self.rate_limit_delay)
                
                params = {"model": self.model, "messages": messages, "stream": True}
                if tools is not None:
                    params["tools"] = tools
                if tool_choice is not None:
                    params["tool_choice"] = tool_choice
                if response_format is not None:
                    params["response_format"] = response_format
                
                stream = await self.client.chat.completions.create(**params)
                
                print("💭 ", end="", flush=True)
                
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_content += content
                        print(content, end="", flush=True)
                
                duration = time.time() - start
                print(f"\n\n{'='*60}")
                print(f"✅ Stream complete: {duration:.2f}s")
                print(f"{'='*60}\n")
                
                # Return a mock response object for compatibility
                return {
                    "choices": [{
                        "message": {
                            "content": full_content,
                            "role": "assistant"
                        },
                        "finish_reason": "stop"
                    }]
                }
                
        except Exception as e:
            duration = time.time() - start
            print(f"\n❌ Stream failed: {duration:.2f}s, error: {e}\n")
            raise

    def _extract_json(self, text: str) -> str:
        """Extract JSON from text using simplified strategies"""
        if not text:
            raise ValueError("Empty text")
        
        # Strategy 1: Direct parse
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract from markdown code blocks
        if match := re.search(r'```(?:json)?\s*([\s\S]*?)```', text, re.IGNORECASE):
            try:
                json.loads(match.group(1))
                return match.group(1).strip()
            except json.JSONDecodeError:
                pass
        
        # Strategy 3: Find balanced braces
        stack = []
        candidates = []
        for i, char in enumerate(text):
            if char == '{':
                stack.append(i)
            elif char == '}' and stack:
                start = stack.pop()
                if not stack:  # Top-level brace closed
                    candidates.append((start, i))
        
        # Try longest candidates first
        for start, end in sorted(candidates, key=lambda x: x[1] - x[0], reverse=True):
            try:
                json.loads(text[start:end+1])
                return text[start:end+1]
            except json.JSONDecodeError:
                continue
        
        raise ValueError(f"No valid JSON found: {text[:100]}...")

    def _ensure_object(self, data: Any) -> Dict[str, Any]:
        """Ensure data is a JSON object, convert array to first object if needed"""
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    self.logger.warning(f"Got array, using first object")
                    return item
        raise ValueError(f"Expected object, got {type(data).__name__}")

    async def generate_structured(
        self,
        messages: list[dict],
        response_model: Type[BaseModel]
    ) -> BaseModel:
        """
        Generate structured output matching the response model
        
        Args:
            messages: Already filtered and prepared messages
            response_model: Pydantic model for validation
        """
        model_name = response_model.__name__
        self.logger.info(f"Generating {model_name}")

        # Request JSON output
        response = await self.chat(messages, response_format={"type": "json_object"})
        
        # Extract and validate JSON
        json_text = None
        if content := response.choices[0].message.content:
            self.logger.info(f"Raw LLM response: {content[:500]}...")
            json_text = self._extract_json(content)
        elif tool_calls := response.choices[0].message.tool_calls:
            json_text = self._extract_json(tool_calls[0].function.arguments)
        
        if not json_text:
            raise ValueError("No content or tool calls in response")
        
        parsed = json.loads(json_text)
        self.logger.info(f"Extracted JSON: {json.dumps(parsed, indent=2)[:300]}...")
        parsed = self._ensure_object(parsed)
        
        return response_model.model_validate(parsed)
