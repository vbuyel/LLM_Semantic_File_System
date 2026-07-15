import asyncio
import inspect
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

_llm_dir = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=_llm_dir / ".env")

from langfuse import get_client, propagate_attributes
from langfuse.openai import OpenAI

from domain.domain import SearchRequest, SearchResponse
from adapters.rag_search import RAGSearch
from adapters.web_search import WebSearch


class AgentResearcher:
    def __init__(self):
        self.client = OpenAI(
            base_url=os.getenv("BASE_MODEL_URL"),
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
        langfuse = get_client()
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

        # Parent span for the full agent turn; OpenAI generations + tools nest under it.
        # Explicit input = user message only (not the whole SearchRequest / system prompt).
        with langfuse.start_as_current_observation(
            as_type="span",
            name="ai-agent-turn",
            input={"text": request.text},
        ) as root_span:
            with propagate_attributes(
                user_id=request.owner,
                session_id=request.correlation_id,
                tags=["ai-agent", "semantic-fs"],
                metadata={
                    "correlation_id": request.correlation_id,
                    "model": self.model,
                },
            ):
                try:
                    request_kwargs = {
                        "name": "agent-reasoning",
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
                    error_text = f"Error: {e}"
                    root_span.update(output={"text": error_text}, level="ERROR")
                    return SearchResponse(text=error_text)

                tool_calls = response.choices[0].message.tool_calls or []
                while tool_calls:
                    messages.append(
                        self._assistant_message_payload(response.choices[0].message)
                    )
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        function_args = tool_call.function.arguments

                        callable_func = self.tool_functions.get(function_name)
                        if callable_func is None:
                            error_text = f"Unknown function: {function_name}"
                            root_span.update(output={"text": error_text}, level="ERROR")
                            return SearchResponse(text=error_text)

                        try:
                            func_args = json.loads(function_args)
                        except json.JSONDecodeError:
                            error_text = (
                                f"Invalid JSON args for function: {function_name}"
                            )
                            root_span.update(output={"text": error_text}, level="ERROR")
                            return SearchResponse(text=error_text)

                        tool_text = func_args.get("text")
                        if not isinstance(tool_text, str) or not tool_text.strip():
                            error_text = "Tool call missing required argument: text"
                            root_span.update(output={"text": error_text}, level="ERROR")
                            return SearchResponse(text=error_text)

                        tool_owner = request.owner
                        corr_id = request.correlation_id
                        with langfuse.start_as_current_observation(
                            as_type="tool",
                            name=function_name,
                            input={"text": tool_text},
                        ) as tool_span:
                            if inspect.iscoroutinefunction(callable_func):
                                tool_result = await callable_func(
                                    tool_text, tool_owner, corr_id
                                )
                            else:
                                tool_result = await asyncio.to_thread(
                                    callable_func, tool_text, tool_owner, corr_id
                                )
                            tool_span.update(output={"text": tool_result.text})

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": tool_result.text,
                            }
                        )

                    try:
                        response = self.client.chat.completions.create(
                            name="agent-reasoning-followup",
                            model=self.model,
                            messages=messages,
                            tools=self.tools,
                            top_p=0.9,
                            temperature=0.3,
                            max_tokens=5000,
                        )
                        tool_calls = response.choices[0].message.tool_calls or []
                    except Exception as e:
                        error_text = f"{e}"
                        root_span.update(output={"text": error_text}, level="ERROR")
                        return SearchResponse(text=error_text)

                content = response.choices[0].message.content
                if content is None:
                    content = "Please try again"
                root_span.update(output={"text": content})
                return SearchResponse(text=content)
