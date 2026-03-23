from openai import OpenAI
import os
from dotenv import load_dotenv
import json

from src.llm.agent_web_rag.domain.domain import SearchRequest, SearchResponse, RAGRequest
from src.llm.agent_web_rag.adapters.web_search import WebSearch
from src.llm.agent_web_rag.adapters.rag_search import RAGSearch


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
        available_files = ""
        if request.file_path:
            available_files = f"\n\nIMPORTANT: The user has uploaded file: {request.file_path}. You MUST use the call_rag tool to analyze this file."
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"You are a research assistant.{available_files}"},
                    {"role": "user", "content": request.text}
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
                                        "description": "The search query text"
                                    }
                                },
                                "required": ["text"]
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "call_rag",
                            "description": "Finding information in user file (Retrieval Augmented Generation)",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "text": {
                                        "type": "string",
                                        "description": "The search query text"
                                    },
                                    "file_path": {
                                        "type": "string",
                                        "description": "File path/URL"
                                    }
                                },
                                "required": ["text", "file_path"]
                            }
                        }
                    },
                ],
                top_p=0.95,
                temperature=0.3,
                max_tokens=1000
            )
        except Exception as e:
            return SearchResponse(text=f"Error: {e}")

        tool_calls = response.choices[0].message.tool_calls
        while tool_calls:
            function_name = tool_calls[0].function.name
            function_args = tool_calls[0].function.arguments

            callable_func = self.tool_functions.get(function_name)
            if callable_func is None:
                return SearchResponse(text=f"Unknown function: {function_name}")
            
            func_args = json.loads(function_args)
            tool_text = func_args.get("text")
            if not isinstance(tool_text, str) or not tool_text.strip():
                return SearchResponse(text="Tool call missing required argument: text")

            tool_file_path = func_args.get("file_path")
            
            if function_name == "call_rag" and tool_file_path:
                tool_result = callable_func(RAGRequest(text=tool_text, additional_data=tool_file_path))
            else:
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
                            "tool_call_id": tool_calls[0].id,
                            "content": tool_result.text,
                        }
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
                                            "description": "The search query text"
                                        }
                                    },
                                    "required": ["text"]
                                }
                            }
                        },
                        {
                        "type": "function",
                        "function": {
                            "name": "call_rag",
                            "description": "Finding information in user file (Retrieval Augmented Generation)",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "text": {
                                        "type": "string",
                                        "description": "The search query text"
                                    },
                                    "file_path": {
                                        "type": "string",
                                        "description": "File path/URL"
                                    }
                                },
                                "required": ["text", "file_path"]
                            }
                        }
                    },
                    ],
                    top_p=0.9,
                    temperature=0.3,
                    max_tokens=1000
                )

                tool_calls = response.choices[0].message.tool_calls
            except Exception as e:
                return SearchResponse(text=f"{e}")

        return SearchResponse(text=response.choices[0].message.content)
