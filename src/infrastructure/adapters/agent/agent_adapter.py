"""Azure AI Agent adapter with streaming and tool execution support."""

import json
import os
import logging
from typing import Generator, Callable

from azure.identity import ClientSecretCredential
from azure.ai.projects import AIProjectClient

from src.domain.exceptions.azure_agent_config_exception import AzureAgentConfigException
from src.domain.exceptions.azure_agent_run_exception import AzureAgentRunException
from src.domain.ports.output.prompt_provider_port import PromptProviderPort
from src.infrastructure.adapters.agent.event_handler import EventHandler
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


class AzureAgentAdapter:
    """Adapter for Azure AI Agents with streaming and tool execution."""

    def __init__(self, search_tool: Callable[[str], dict], prompt_provider: PromptProviderPort):
        """Initialize the adapter and Azure client.

        :param search_tool: Callable tool used by the agent.
        :param prompt_provider: Provider for agent instructions and prompts.
        :raises AzureAgentConfigException: If required env vars are missing.
        """
        self.prompt_provider = prompt_provider
        self.search_tool = search_tool

        try:
            tenant_id = os.environ["AZURE_TENANT_ID"]
            client_id = os.environ["AZURE_CLIENT_ID"]
            client_secret = os.environ["AZURE_CLIENT_SECRET"]
            endpoint = os.environ["AZURE_PROJECT_ENDPOINT"]
            self.agent_id = os.environ["AZURE_AI_AGENT_ID"]

            if not all([tenant_id, client_id, client_secret, endpoint, self.agent_id]):
                raise AzureAgentConfigException(
                    "Missing one or more Azure Agent environment variables "
                    "(AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, "
                    "AZURE_PROJECT_ENDPOINT, AZURE_AI_AGENT_ID)"
                )

            self.credential = ClientSecretCredential(
                tenant_id=tenant_id, client_id=client_id, client_secret=client_secret
            )
            self.project_client = AIProjectClient(endpoint=endpoint, credential=self.credential)
            self.agent = self.project_client.agents.get_agent(self.agent_id)

            logger.info("AzureAgentAdapter initialized. Agent ID: %s", self.agent_id)

        except KeyError as e:
            logger.error("Missing environment variable: %s", e)
            raise AzureAgentConfigException(f"Missing env variable: {e}") from e
        except Exception as e:
            logger.exception("Failed to initialize AzureAgentAdapter: %s", e)
            raise AzureAgentConfigException(f"Failed to initialize agent: {e}") from e

    def ask_question_stream(self, question: str) -> Generator[str, None, None]:
        """Stream answer tokens for a question.

        :param question: Question text to send to the agent.
        :return: Generator yielding response chunks.
        :raises AzureAgentRunException: If the run fails.
        """
        if not self.agent:
            raise AzureAgentRunException(message="Agent not initialized")

        logger.info("Starting question stream: %s", question)

        functions = {"search_tool": self.search_tool}
        thread = self.project_client.agents.threads.create()
        self.project_client.agents.messages.create(thread_id=thread.id, role="user", content=question)
        event_handler = EventHandler()

        try:
            with self.project_client.agents.runs.stream(
                thread_id=thread.id, agent_id=self.agent_id, event_handler=event_handler
            ) as stream:

                for raw_event in stream:
                    event_type, event_data = AzureAgentAdapter._normalize_event(raw_event)
                    logger.debug("Received event: %s", event_type)

                    while event_handler.has_chunks():
                        chunk = next(event_handler.get_stream_chunks())
                        yield chunk

                    if event_type == "thread.message.completed":
                        logger.info("Agent run completed")
                        break

                    elif event_type == "thread.run.failed":
                        logger.error("Agent run failed: %s", getattr(event_data, "last_error", None))
                        raise AzureAgentRunException(
                            message=f"Agent run failed: {getattr(event_data, 'last_error', None)}",
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
                            logger.info("Tool call: %s with args %s", function_name, function_args)

                            if function_name in functions:
                                try:
                                    result = functions[function_name](**function_args)
                                    output = json.dumps(result) if isinstance(result, dict) else str(result)
                                    logger.debug("Tool output: %s", output)
                                except Exception as e:
                                    output = json.dumps({"error": str(e)})
                                    logger.exception("Tool execution failed: %s", e)
                            else:
                                output = json.dumps({"error": f"Function {function_name} not found"})
                                logger.warning("Function %s not found", function_name)

                            tool_outputs.append({"tool_call_id": tool_call.id, "output": output})

                        self.project_client.agents.runs.submit_tool_outputs_stream(
                            thread_id=thread.id, run_id=run_data.id, tool_outputs=tool_outputs, event_handler=event_handler
                        )

            while event_handler.has_chunks():
                chunk = next(event_handler.get_stream_chunks())
                yield chunk

        except Exception as e:
            logger.exception("Error during agent streaming: %s", e)
            raise AzureAgentRunException(message=str(e)) from e

    def cleanup(self):
        """Release resources associated with the adapter."""
        logger.info("Cleaning up AzureAgentAdapter resources")
        pass

    def __enter__(self):
        """Enter a context manager for the adapter.

        :return: Self instance.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the adapter context and clean up resources.

        :param exc_type: Exception type, if any.
        :param exc_val: Exception value, if any.
        :param exc_tb: Exception traceback, if any.
        :return: False to propagate exceptions.
        """
        self.cleanup()
        return False

    @staticmethod
    def _normalize_event(event):
        """Normalize agent events into (event_type, event_data).

        :param event: Raw event object or tuple.
        :return: Tuple of event type and data.
        """
        if hasattr(event, "event_type"):
            return event.event_type, getattr(event, "data", None)
        if isinstance(event, tuple):
            event_type = event[0]
            event_data = event[1] if len(event) > 1 else None
            return event_type, event_data
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

    def update_agent_tools(self) -> None:
        """
        Update the tools and instructions of an existing Azure agent.
        """
        new_tools, new_instructions = self._get_tools_and_instructions()
        tools_payload = [
            {"type": "function", "function": tool["function"]}
            for tool in new_tools
        ]

        self.agent = self.project_client.agents.update_agent(
            self.agent_id,
            tools=tools_payload,
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