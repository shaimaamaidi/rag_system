"""Update Azure agent tools configuration."""
import logging
import sys

from src.domain.exceptions.app_exception import AppException
from src.infrastructure.di.container import Container
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


def main() -> None:
    """Update the Azure agent tools.

    :return: None.
    """
    logger.info("Updating Azure agent tools...")

    try:
        container = Container()
    except AppException as e:
        logger.error("Container initialization failed: [%s] %s", e.code, e.message)
        sys.exit(1)
    except Exception as e:
        logger.error("Container initialization failed: %s", str(e))
        sys.exit(1)

    agent = container.agent_adapter
    agent.update_agent_tools()
    logger.info("Azure agent tools updated successfully.")
    # agent._list_agent_tools()


if __name__ == "__main__":
    main()