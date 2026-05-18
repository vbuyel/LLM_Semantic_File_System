import asyncio
import inspect
import json
import os
import re
import uuid
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from src.llm.domain.domain import SearchRequest, SearchResponse
from src.llm.adapters.rag_search import RAGSearch
from src.llm.adapters.web_search import WebSearch

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


class AgentResearcher:
    def __init__(self):
        self.client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        )
        self.model = os.getenv("MODEL")

        self.web = WebSearch()
        self.rag = RAGSearch()
        self.tool_functions = {
            "call_web_searcher": self.web.do_search,
            "call_rag": self.rag.do_search,
        }
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "call_web_searcher",
                    "description": "Search the web for information based on a query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The search query text",
                            }
                        },
                        "required": ["text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "call_rag",
                    "description": "Search and retrieve actual content from the user's personal files. Returns file names, paths, and text content. Use this to answer questions about what's inside the user's documents.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The search query text",
                            }
                        },
                        "required": ["text"],
                    },
                },
            },
        ]


    @staticmethod
    def _should_force_rag(text: str) -> bool:
        lowered = text.lower()
        rag_hints = (
            "use rag",
            "rag",
            "my file",
            "my files",
            "file about",
            "find file",
            "project file",
            "file named",
            "file called",
            "document",
        )
        russian_hints = (
            "файл",
            "документ",
        )
        if any(hint in lowered for hint in rag_hints):
            return True
        if any(hint in lowered for hint in russian_hints):
            return True
        if re.search(r'\b\w+\.(py|txt|md|pdf|docx?|xlsx?|pptx?|json|csv|yaml|yml|xml|html?|js|ts|jsx|tsx|css|sql|sh|bat|ini|cfg|conf|log)\b', lowered):
            return True
        if re.search(r'\b[A-Z][A-Za-z0-9]+[_\-][A-Za-z0-9]+\b', text):
            return True
        return False


    @staticmethod
    def _assistant_message_payload(message):
        payload = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in message.tool_calls
            ]
        return payload


    async def get_response(self, request: SearchRequest) -> SearchResponse:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a research assistant with access to the user's personal files and the web.\n\n"
                    "## CRITICAL: How to use call_rag results\n\n"
                    "When you call call_rag, you receive the actual text content of the user's files "
                    "(file names, paths, and text chunks). "
                    "You MUST read that content carefully and answer the user's question based on it.\n\n"
                    "### Requirements:\n"
                    "1. ALWAYS answer in the same language the user wrote in.\n"
                    "2. Actually READ the file content and use it to answer. Do NOT just list file names.\n"
                    "3. If the file content answers the question, provide that information directly "
                    "(summarize, translate, find specific data, or quote as appropriate).\n"
                    "4. NEVER say 'Found relevant files:' or 'Based on the retrieved documents:' "
                    "or anything similar — just give the answer.\n"
                    "5. If call_rag returned content about a different file than what was asked, "
                    "tell the user that the requested file was not found in the index.\n"
                    "6. Do NOT call call_web_searcher after call_rag — the file search already covers user documents.\n\n"
                    "### Examples:\n"
                    "BAD: 'Found some relevant files: File1.txt, File2.txt'\n"
                    "GOOD: 'В файле содержится следующая информация: [content summary]'\n\n"
                    "BAD: 'Based on the retrieved documents, here is what I found...'\n"
                    "GOOD: 'According to your file, [direct answer from file content]'"
                ),
            },
            {"role": "user", "content": request.text},
        ]
        try:
            request_kwargs = {
                "model": self.model,
                "messages": messages,
                "tools": self.tools,
                "top_p": 0.95,
                "temperature": 0.3,
                "max_tokens": 5000,
            }
            if self._should_force_rag(request.text):
                request_kwargs["tool_choice"] = {
                    "type": "function",
                    "function": {"name": "call_rag"},
                }
            response = self.client.chat.completions.create(**request_kwargs)
        except Exception as e:
            return SearchResponse(text=f"Error: {e}")

        tool_calls = response.choices[0].message.tool_calls or []
        while tool_calls:
            messages.append(self._assistant_message_payload(response.choices[0].message))
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = tool_call.function.arguments

                callable_func = self.tool_functions.get(function_name)
                if callable_func is None:
                    return SearchResponse(text=f"Unknown function: {function_name}")

                try:
                    func_args = json.loads(function_args)
                except json.JSONDecodeError:
                    return SearchResponse(text=f"Invalid JSON args for function: {function_name}")

                tool_text = func_args.get("text")
                if not isinstance(tool_text, str) or not tool_text.strip():
                    return SearchResponse(
                        text="Tool call missing required argument: text"
                    )

                tool_owner = request.owner
                corr_id = request.correlation_id
                if inspect.iscoroutinefunction(callable_func):
                    tool_result = await callable_func(tool_text, tool_owner, corr_id)
                else:
                    tool_result = await asyncio.to_thread(callable_func, tool_text, tool_owner, corr_id)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result.text,
                    }
                )

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools,
                    top_p=0.9,
                    temperature=0.3,
                    max_tokens=5000,
                )
                tool_calls = response.choices[0].message.tool_calls or []
            except Exception as e:
                return SearchResponse(text=f"{e}")

        content = response.choices[0].message.content
        if content is None:
            content = "Please try again"
        return SearchResponse(text=content)
