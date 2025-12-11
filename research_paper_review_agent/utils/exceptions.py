from pathlib import Path


class ConfigValidationError(Exception):
    """Custom exception for configuration validation errors with detailed messages."""

    def __init__(self, errors: list[dict], config_path: Path):
        self.errors = errors
        self.config_path = config_path
        self.message = self._format_error_message()
        super().__init__(self.message)

    def _format_error_message(self) -> str:
        lines = [f"Config validation failed ({self.config_path}):"]

        for error in self.errors:
            location = ".".join(str(loc) for loc in error.get("loc", []))
            message = error.get("msg", "Unknown error")
            lines.append(f"  - {location or 'root'}: {message}")

        return "\n".join(lines)

