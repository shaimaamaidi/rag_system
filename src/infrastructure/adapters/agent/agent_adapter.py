"""
Module containing the AzureAgentAdapter class.
Provides an adapter for interacting with Azure AI Agents via Azure AI Projects.
Enables streaming questions, managing tools, and updating agent instructions.

Main features:
- Initialize an Azure AI Agent using credentials from environment variables.
- Pose questions in streaming mode with Server-Sent Events (SSE).
- Map and execute associated tools (classify_question, search_cv_rag, out_of_scope_response).
- Update and display the tools registered on the agent.
- Context manager support for automatic resource handling.
"""

import json
import os
from typing import Generator, Callable

from azure.ai.agents.models import ToolSet, FunctionTool
from azure.identity import ClientSecretCredential
from azure.ai.projects import AIProjectClient

from src.domain.exceptions.azure_agent_config_exception import AzureAgentConfigException
from src.domain.exceptions.azure_agent_run_exception import AzureAgentRunException
from src.domain.ports.output.prompt_provider_port import PromptProviderPort
from src.infrastructure.adapters.agent.event_handler import EventHandler


class AzureAgentAdapter:
    """
    Adapter for interacting with Azure AI Agents.

    This class provides an interface to:
    - Ask questions to an Azure Agent in streaming mode and receive incremental responses.
    - Map and execute defined tools for the agent.
    - Display and update the agent's tools and instructions.

    Attributes:
        search_tool (callable): Tool to search answers in CV content.
        project_client (AIProjectClient): Azure AI Project client for interacting with the agent.
        agent_id (str): Identifier of the Azure AI agent.
        agent (object): Agent instance retrieved from Azure.
    """

    def __init__(
            self,
            search_tool: Callable[[str], dict],
            prompt_provider: PromptProviderPort):
        """
        Initializes the Azure AI Project client and retrieves the agent.

        Args:
            search_tool (callable): Function to search CV content.

        Raises:
            ValueError: If the agent cannot be retrieved properly.
        """
        tenant_id = os.environ["AZURE_TENANT_ID"]
        client_id = os.environ["AZURE_CLIENT_ID"]
        client_secret = os.environ["AZURE_CLIENT_SECRET"]
        endpoint = os.environ["AZURE_PROJECT_ENDPOINT"]

        self.agent_id = os.environ["AZURE_AI_AGENT_ID"]

        if not all([tenant_id, client_id, client_secret, endpoint, self.agent_id]):
            raise AzureAgentConfigException(
                "Missing one or more Azure Agent environment variables "
                "(AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_PROJECT_ENDPOINT, AZURE_AI_AGENT_ID)"
            )

        self.credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )

        self.project_client = AIProjectClient(
            endpoint=endpoint,
            credential=self.credential
        )

        self.agent = self.project_client.agents.get_agent(self.agent_id)
        self.search_tool = search_tool

        self.prompt_provider = prompt_provider

    def ask_question_stream(self, question: str) -> Generator[str, None, None]:
        if not self.agent:
            raise AzureAgentRunException(
                message="Agent not initialized"
            )

        functions = {
            "search_cv_rag": self.search_tool,
        }

        thread = self.project_client.agents.threads.create()

        self.project_client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=question,
        )

        event_handler = EventHandler()

        with self.project_client.agents.runs.stream(
                thread_id=thread.id,
                agent_id=self.agent_id,
                event_handler=event_handler
        ) as stream:

            for raw_event in stream:
                event_type, event_data = self._normalize_event(raw_event)

                # Yield chunks disponibles après chaque event
                while event_handler.has_chunks():
                    chunk = next(event_handler.get_stream_chunks())
                    yield chunk

                if event_type == "thread.message.completed":
                    break

                elif event_type == "thread.run.failed":
                    raise AzureAgentRunException(
                        message=f"Agent run failed: {event_data.last_error}",
                        code="AZURE_AGENT_RUN_ERROR",
                        http_status=502
                    )

                elif event_type == "thread.run.requires_action":
                    run_data = event_data
                    tool_calls = run_data.required_action.submit_tool_outputs.tool_calls
                    tool_outputs = []

                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments or "{}")

                        if function_name in functions:
                            try:
                                result = functions[function_name](**function_args)
                                output = (
                                    json.dumps(result)
                                    if isinstance(result, dict)
                                    else str(result)
                                )
                            except Exception as e:
                                output = json.dumps({"error": str(e)})
                        else:
                            output = json.dumps(
                                {"error": f"Function {function_name} not found"}
                            )

                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": output
                        })

                    self.project_client.agents.runs.submit_tool_outputs_stream(
                        thread_id=thread.id,
                        run_id=run_data.id,
                        tool_outputs=tool_outputs,
                        event_handler=event_handler
                    )

        # Yield les derniers chunks restants
        while event_handler.has_chunks():
            chunk = next(event_handler.get_stream_chunks())
            yield chunk


    def cleanup(self):
        """
        Cleans up resources used by the adapter.
        """
        pass

    def __enter__(self):
        """
        Context manager entry.

        Returns:
            AzureAgentAdapter: The current instance.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Automatic cleanup on context manager exit.

        Args:
            exc_type: Exception type (if any).
            exc_val: Exception value (if any).
            exc_tb: Exception traceback (if any).

        Returns:
            bool: False to propagate any exceptions.
        """
        self.cleanup()
        return False

    def _normalize_event(self, event):
        """
        Normalize an Azure SSE event into a tuple (event_type, event_data).

        Args:
            event: Event object or tuple received from Azure SSE.

        Returns:
            tuple: (event_type: str, event_data: object)
        """
        # Cas 1 : objet Event
        if hasattr(event, "event_type"):
            return event.event_type, getattr(event, "data", None)

        # Cas 2 : tuple (event_type, data, ...)
        if isinstance(event, tuple):
            event_type = event[0]
            event_data = event[1] if len(event) > 1 else None
            return event_type, event_data

        # Cas inconnu
        return None, None

    def _list_agent_tools(self):
        """
        Display all tools currently registered on the Azure agent.

        Raises:
            ValueError: If the agent is not initialized.
            AttributeError: If tools cannot be retrieved.
        """
        if not self.agent:
            raise ValueError("Agent not initialised !")

        try:
            print("\n📘 Agent's instructions :")
            instructions = getattr(self.agent, "instructions", None)
            if instructions:
                print(instructions)
            else:
                print("Agent without instructions.")
            tools = self.agent.tools
            if not tools:
                print("Agent without tools.")
                return

            print("Agent's tools :")
            for i, tool in enumerate(tools, 1):
                name = tool.get("function", {}).get("name", "Nom inconnu")
                desc = tool.get("function", {}).get("description", "")
                print(f"{i}. {name} - {desc}")

        except AttributeError:
            raise

    def update_agent_tools(self) ->None:
        """
        Update the tools and instructions of an existing Azure agent.
        """
        new_tools, new_instructions =self._get_tools_and_instructions()
        new_toolset = ToolSet()

        for tool in new_tools:
            func = tool["callable"]
            func.__name__ = tool["function"]["name"]
            function_tool = FunctionTool({func})
            new_toolset.add(function_tool)

        self.agent = self.project_client.agents.update_agent(
            self.agent_id,
            tools=new_toolset,
            instructions=new_instructions,
            temperature=self.agent.temperature
        )


    def _get_tools_and_instructions(self):
        """
        Prepare the list of tools and instructions for the agent.

        Returns:
            tuple: (tools_json: list, instructions: str)
        """
        tools_json = [
            {
                "type": "function",
                "function": {
                    "name": "search_tool",
                    "description": "Cherche la réponse dans BDD.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string"
                            }
                        },
                        "required": ["question"]
                    }
                },
                "callable": self.search_tool
            }
        ]

        # 3️⃣ Instructions pour l'agent
        instructions = self.prompt_provider.get_agent_instructions()

        return tools_json, instructions