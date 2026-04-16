from openai import OpenAI
import os
from dotenv import load_dotenv
import json

from src.llm.domain.domain import SearchRequest, SearchResponse
from src.llm.adapters.web_search import WebSearch
from src.llm.adapters.rag_search import RAGSearch

load_dotenv()


class AgentResearcher:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model = os.getenv("MODEL")

        self.web = WebSearch()
        self.rag = RAGSearch()
        self.tool_functions = {
            "call_web_searcher": self.web.do_search,
            "call_rag": self.rag.do_search,
        }

    def get_response(self, request: SearchRequest) -> SearchResponse:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a research assistant.",
                    },
                    {"role": "user", "content": request.text},
                ],
                tools=[
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
                            "description": "Finding information in user files (Retrieval Augmented Generation)",
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
                ],
                top_p=0.95,
                temperature=0.3,
                max_tokens=1000,
            )
        except Exception as e:
            return SearchResponse(text=f"Error: {e}")

        tool_calls = response.choices[0].message.tool_calls
        while tool_calls:
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = tool_call.function.arguments

                callable_func = self.tool_functions.get(function_name)
                if callable_func is None:
                    return SearchResponse(text=f"Unknown function: {function_name}")

                func_args = json.loads(function_args)
                tool_text = func_args.get("text")
                if not isinstance(tool_text, str) or not tool_text.strip():
                    return SearchResponse(
                        text="Tool call missing required argument: text"
                    )

                tool_result = callable_func(tool_text)

                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "system",
                                "content": "Summarize the tool content based on user query.",
                            },
                            {
                                "role": "user",
                                "content": request.text,
                            },
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": tool_result.text,
                            },
                        ],
                        tools=[
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
                                    "description": "Finding information in user files (Retrieval Augmented Generation)",
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
                        ],
                        top_p=0.9,
                        temperature=0.3,
                        max_tokens=1000,
                    )

                    tool_calls = response.choices[0].message.tool_calls
                except Exception as e:
                    return SearchResponse(text=f"{e}")

        return SearchResponse(text=response.choices[0].message.content)
