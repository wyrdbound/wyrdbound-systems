"""Enhanced logging configuration for GRIMOIRE runner."""

import logging
import sys

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(
    level: str = "INFO", 
    format_string: str | None = None, 
    use_rich: bool = True,
    log_file: str | None = None
) -> None:
    """Setup logging configuration with optional Rich formatting and file output."""

    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set up console handler only if no log file or if we want both
    if not log_file or use_rich:
        if use_rich:
            # Use Rich handler for beautiful colored output
            console = Console(stderr=True)
            handler = RichHandler(
                console=console,
                show_time=True,
                show_path=True,
                enable_link_path=True,
                markup=True,
            )
            # Rich handles its own formatting
            formatter = logging.Formatter("%(message)s")
        else:
            # Use standard handler
            handler = logging.StreamHandler(sys.stderr)
            # Default format if none provided
            if format_string is None:
                format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            formatter = logging.Formatter(format_string)

        handler.setFormatter(formatter)
        handler.setLevel(numeric_level)
        root_logger.addHandler(handler)

    # Set up file handler if requested
    if log_file:
        import os
        log_dir = os.path.dirname(log_file)
        if log_dir:  # Only create directory if it's not empty (i.e., not current dir)
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, mode='w')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)  # Always debug level for file
        root_logger.addHandler(file_handler)

    # Quiet down some noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return logging.getLogger(name)


def set_debug_mode() -> None:
    """Enable debug logging."""
    logging.getLogger().setLevel(logging.DEBUG)
    for handler in logging.getLogger().handlers:
        handler.setLevel(logging.DEBUG)


def set_quiet_mode() -> None:
    """Enable only warning and error logging."""
    logging.getLogger().setLevel(logging.WARNING)
    for handler in logging.getLogger().handlers:
        handler.setLevel(logging.WARNING)
