from src.llm.ai_gateway.domain.domain import Request, Response

from openai import OpenAI
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

class AgenticAI:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model = os.getenv("MODEL")
        self.tool_functions = {
            "call_agent_researcher": self.call_agent_researcher,
        }

    def call_agent_researcher(self, query: Request) -> Response:
        params = {"text": query.text}
        if query.file_path:
            params["file_path"] = query.file_path
        
        response = requests.get(f"{os.getenv("LSFS_URL")}:8001/research_agent", params=params)
        return Response(text=response.text)

    def get_response(self, request: Request) -> Response:
        file_context = ""
        if request.file_path:
            file_context = f"\n\nUser uploaded a file: {request.file_path}\nYou should analyze this file using the call_agent_researcher tool."
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "call_agent_researcher",
                            "description": "Asking AI Agent to find information from the internet or in user file (Retrieval Augmented Generation)",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "text": {
                                        "type": "string",
                                        "description": "The search query text"
                                    },
                                        "file_path": {
                                            "type": "string",
                                            "description": "Absolute path or URL of the file to analyze"
                                    }
                                },
                                "required": ["text"]
                            }
                        }
                    },
                ],
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a helpful AI assistant.{file_context} If a file path is mentioned in the user's message, you MUST pass it to the call_agent_researcher tool as the 'file_path' parameter."
                    },
                    {
                        "role": "system",
                        "content": f"You are a helpful AI assistant. If user want to search through internet or to ask on the query web search needed, you MUST use tool call_agent_researcher."
                    },
                    {
                        "role": "user",
                        "content": request.text + file_context
                    }
                ],
                temperature=0.7,
                max_tokens=10000,
                top_p=0.95,
            )

        except Exception as e:
            return Response(text=f"Request to the model. {str(e)}")

        tool_calls = response.choices[0].message.tool_calls
        while tool_calls:
            function_name = tool_calls[0].function.name
            function_args = tool_calls[0].function.arguments
            
            callable_func = self.tool_functions.get(function_name)
            if callable_func is None:
                return Response(text=f"Unknown function: {function_name}")
            
            args_dict = json.loads(function_args)
            request = Request(text=args_dict.get("text"), file_path=args_dict.get("file_path"))
            
            tool_result = callable_func(request)

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You have to answer on user query only based on tool content. If you do not know the answer, try to call tools one more time",
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
                    temperature=0.7,
                    max_tokens=2000,
                    top_p=0.95,
                )

                tool_calls = response.choices[0].message.tool_calls
            except Exception as e:
                return Response(text=f"Request to the model with tool info. {str(e)}")

        content = response.choices[0].message.content
        return Response(text=content)
