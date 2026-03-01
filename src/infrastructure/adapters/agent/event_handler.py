"""
Module containing the EventHandler class.
Provides an event handler for interacting with Azure AI Agents in streaming mode.

Main features:
- Handles partial messages (deltas) from the assistant agent.
- Logs run events, steps, and tool calls.
- Maintains an internal queue for streaming response chunks.
- Handles errors and unhandled events.
- Provides a generator to retrieve text chunks progressively.
"""

import logging
from typing import Generator

from azure.ai.agents.models import (
    RunStepDeltaChunk,
    RunStep,
    ThreadRun,
    ThreadMessage,
    MessageDeltaChunk,
    AgentEventHandler,
)
logger = logging.getLogger(__name__)


class EventHandler(AgentEventHandler):
    """
    Event handler for Azure AI Agents.

    This class extends AgentEventHandler and provides:
    - Management of partial messages (deltas) from the assistant.
    - Logging of run events and tool calls.
    - Storage of text chunks for progressive streaming.
    """

    def __init__(self):
        """
        Initializes the EventHandler.

        Attributes:
            _current_message_id (str | None): ID of the message currently being processed.
            _accumulated_text (str): Accumulated text for the current message.
            _stream_queue (list): Queue of chunks ready for streaming.
        """
        super().__init__()
        self._current_message_id = None
        self._accumulated_text = ""
        self._stream_queue = []

    def on_message_delta(self, delta: MessageDeltaChunk) -> None:
        """
        Handles partial message updates (MessageDeltaChunk).

        Args:
            delta (MessageDeltaChunk): The delta of the received message.
        """
        if delta.id != self._current_message_id:
            if self._current_message_id is not None:
                logger.info("")

            self._current_message_id = delta.id
            self._accumulated_text = ""
            logger.info("\nassistant > ")

        partial_text = ""
        if delta.delta.content:
            for chunk in delta.delta.content:
                partial_text += chunk.text.get("value", "")

        self._accumulated_text += partial_text

        if partial_text:
            self._stream_queue.append(partial_text)
            logger.info(partial_text)

    def on_thread_message(self, message: ThreadMessage) -> None:
        """
        Handles thread messages.

        Args:
            message (ThreadMessage): The message received in the thread.
        """
        if message.status == "completed" and message.role == "assistant":
            logger.info("")
            self._current_message_id = None
            self._accumulated_text = ""
        else:
            logger.info(f"{message.status} (id: {message.id})")

    def on_thread_run(self, run: ThreadRun) -> None:
        """
        Handles thread run events.

        Args:
            run (ThreadRun): The current run instance.
        """
        logger.info(f"status > {run.status}")
        if run.status == "failed":
            logger.error(f"error > {run.last_error}")

    def on_run_step(self, step: RunStep) -> None:
        """
        Handles run steps.

        Args:
            step (RunStep): The step being executed.
        """
        logger.info(f"{step.type} > {step.status}")

    def on_run_step_delta(self, delta: RunStepDeltaChunk) -> None:
        """
        Handles step deltas to track tool calls.

        Args:
            delta (RunStepDeltaChunk): The delta of the step received.
        """
        if delta.delta.step_details and delta.delta.step_details.tool_calls:
            for tcall in delta.delta.step_details.tool_calls:
                if getattr(tcall, "function", None) and tcall.function.name:
                    logger.info(f"tool call > {tcall.function.name}")

    def on_unhandled_event(self, event_type: str, event_data):
        """
        Handles unhandled events.

        Args:
            event_type (str): The type of the event.
            event_data: The event data.
        """
        logger.debug(f"unhandled > {event_type}")

    def on_error(self, data: str) -> None:
        """
        Handles errors.

        Args:
            data (str): Error message.
        """
        logger.error(f"error > {data}")

    def on_done(self) -> None:
        """
        Called when the run is completed.
        """
        logger.info("done")

    def get_stream_chunks(self) -> Generator[str, None, None]:
        """
        Generator to retrieve text chunks progressively for streaming.

        Yields:
            str: A chunk of text to be displayed.
        """
        while self._stream_queue:
            yield self._stream_queue.pop(0)

    def has_chunks(self) -> bool:
        """
        Checks if there are chunks available in the queue.

        Returns:
            bool: True if chunks are available, False otherwise.
        """
        return len(self._stream_queue) > 0
