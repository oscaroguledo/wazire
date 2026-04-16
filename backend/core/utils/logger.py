import sys
from datetime import datetime, timezone
from typing import Optional
try:
	from colorama import Fore, Style, init as colorama_init

	colorama_init(autoreset=True)
except Exception:
	# colorama not available in the environment; provide no-op fallbacks
	class _NoColor:
		CYAN = ""
		GREEN = ""
		YELLOW = ""
		RED = ""
		MAGENTA = ""

	class _NoStyle:
		RESET_ALL = ""

	Fore = _NoColor()
	Style = _NoStyle()


class Logger:
	LEVELS = {
		"DEBUG": 10,
		"INFO": 20,
		"WARNING": 30,
		"ERROR": 40,
		"CRITICAL": 50,
	}

	LEVEL_COLORS = {
		"DEBUG": Fore.CYAN,
		"INFO": Fore.GREEN,
		"WARNING": Fore.YELLOW,
		"ERROR": Fore.RED,
		"CRITICAL": Fore.MAGENTA,
	}

	def __init__(self, name: str = "wazire", level: str = "DEBUG") -> None:
		self.name = name
		self.level = level.upper()
		self.levelno = self.LEVELS.get(self.level, 10)

	def _should_log(self, level: str) -> bool:
		return self.LEVELS.get(level, 0) >= self.levelno

	def _format(self, level: str, message: str) -> str:
		ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
		color = self.LEVEL_COLORS.get(level, "")
		level_colored = f"{color}{level}{Style.RESET_ALL}"
		return f"[{ts}] {level_colored} - {self.name} - {message}"

	def _print(self, level: str, message: str) -> None:
		if not self._should_log(level):
			return
		print(self._format(level, message), file=sys.stdout, flush=True)

	def debug(self, message: str, *args, **kwargs) -> None:
		self._print("DEBUG", self._render(message, *args, **kwargs))

	def info(self, message: str, *args, **kwargs) -> None:
		self._print("INFO", self._render(message, *args, **kwargs))

	def warning(self, message: str, *args, **kwargs) -> None:
		self._print("WARNING", self._render(message, *args, **kwargs))

	def error(self, message: str, *args, **kwargs) -> None:
		self._print("ERROR", self._render(message, *args, **kwargs))

	def critical(self, message: str, *args, **kwargs) -> None:
		self._print("CRITICAL", self._render(message, *args, **kwargs))

	def exception(self, message: str, *args, exc_info: Optional[Exception] = None, **kwargs) -> None:
		msg = self._render(message, *args, **kwargs)
		if exc_info:
			msg = f"{msg} | exception: {exc_info!r}"
		self._print("ERROR", msg)

	def _render(self, message: str, *args, **kwargs) -> str:
		try:
			if args or kwargs:
				return message.format(*args, **kwargs)
			return message
		except Exception:
			return message


def get_logger(name: str = "wazire", level: str = "DEBUG") -> Logger:
	return Logger(name=name, level=level)


# default module logger
logger = get_logger()
