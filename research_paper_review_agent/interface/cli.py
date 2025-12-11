import argparse
import json
import sys

from ..core.agent import run_agent
from ..services.config_service import load_config
from ..utils.exceptions import ConfigValidationError
from ..utils.logger import get_logger, setup_logger


def run_cli(argv=None) -> None:
    try:
        parser = argparse.ArgumentParser(description="Academic paper review AI agent")
        parser.add_argument(
            "-c",
            "--config",
            type=str,
            default=None,
            help="Path to config.json (default: None)",
        )
        parser.add_argument(
            "--log-level",
            type=str,
            default="INFO",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            help="Set logging level (default: INFO)",
        )
        args = parser.parse_args(argv)

        setup_logger(args.log_level)

        config = load_config(args.config) if args.config else load_config()

        run_agent(config)

    except ConfigValidationError as e:
        logger = get_logger("CLI")
        logger.error(e.message)
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger = get_logger("CLI")
        logger.error(f"Invalid JSON format - {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        logger = get_logger("CLI")
        logger.error(str(e))
        sys.exit(1)
    except ValueError as e:
        logger = get_logger("CLI")
        logger.error(f"Invalid argument value - {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger = get_logger("CLI")
        logger.info("Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger = get_logger("CLI")
        logger.error(f"An unexpected error occurred - {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_cli(sys.argv[1:])

