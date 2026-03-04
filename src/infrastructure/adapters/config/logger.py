import logging

"""
Module responsible for setting up the global logger configuration.
This logger is used across the application to provide consistent
and timestamped logging for debugging, info, warning, and error messages.
"""

def setup_logger():
    """
    Configure the global logging settings for the application.

    Settings applied:
        - Level: INFO (logs INFO, WARNING, ERROR, CRITICAL)
        - Format: Timestamp, log level, logger name, and message
        - Date format: YYYY-MM-DD HH:MM:SS

    Notes:
        - Should be called once at the application startup.
        - All modules importing logging will inherit this configuration.
        - Can be extended later to include file handlers or rotating logs.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
