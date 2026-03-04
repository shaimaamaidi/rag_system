"""Event handler for streaming Azure AI Agent responses."""

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

from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


class EventHandler(AgentEventHandler):
    """Handle streaming events from Azure AI Agents."""

    def __init__(self):
        """Initialize the handler and internal buffers."""
        super().__init__()
        self._current_message_id = None
        self._accumulated_text = ""
        self._stream_queue = []

    def on_message_delta(self, delta: MessageDeltaChunk) -> None:
        """Handle partial message updates.

        :param delta: Delta chunk of the received message.
        :return: None.
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
        """Handle thread message updates.

        :param message: Thread message update.
        :return: None.
        """
        if message.status == "completed" and message.role == "assistant":
            logger.info("")
            self._current_message_id = None
            self._accumulated_text = ""
        else:
            logger.info("%s (id: %s)", message.status, message.id)

    def on_thread_run(self, run: ThreadRun) -> None:
        """Handle thread run events.

        :param run: Thread run instance.
        :return: None.
        """
        logger.info("status > %s", run.status)
        if run.status == "failed":
            logger.error("error > %s", run.last_error)

    def on_run_step(self, step: RunStep) -> None:
        """Handle run step updates.

        :param step: Run step instance.
        :return: None.
        """
        logger.info("%s > %s", step.type, step.status)

    def on_run_step_delta(self, delta: RunStepDeltaChunk) -> None:
        """Handle run step deltas to track tool calls.

        :param delta: Run step delta chunk.
        :return: None.
        """
        if delta.delta.step_details and delta.delta.step_details.tool_calls:
            for tcall in delta.delta.step_details.tool_calls:
                if getattr(tcall, "function", None) and tcall.function.name:
                    logger.info("tool call > %s", tcall.function.name)

    def on_unhandled_event(self, event_type: str, event_data):
        """Handle unhandled events.

        :param event_type: Event type string.
        :param event_data: Event payload.
        :return: None.
        """
        logger.debug("unhandled > %s", event_type)

    def on_error(self, data: str) -> None:
        """Handle errors.

        :param data: Error message.
        :return: None.
        """
        logger.error("error > %s", data)

    def on_done(self) -> None:
        """Handle run completion.

        :return: None.
        """
        logger.info("done")

    def get_stream_chunks(self) -> Generator[str, None, None]:
        """Yield queued streaming chunks.

        :return: Generator of text chunks.
        """
        while self._stream_queue:
            yield self._stream_queue.pop(0)

    def has_chunks(self) -> bool:
        """Return True if there are chunks queued for streaming.

        :return: True when chunks are available.
        """
        return len(self._stream_queue) > 0
