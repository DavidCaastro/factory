from __future__ import annotations

from dataclasses import dataclass
import sys


@dataclass(frozen=True)
class ProgressEvent:
    completed_steps: int
    total_steps: int
    phase: str
    message: str


class ConsoleProgressRenderer:
    def __init__(self, enabled: bool, stream=None, bar_width: int = 28):
        self.enabled = enabled
        self.stream = stream or sys.stdout
        self.bar_width = bar_width
        self._drawn = False

    def update(self, event: ProgressEvent) -> None:
        if not self.enabled:
            return

        total = max(event.total_steps, 1)
        done = max(0, min(event.completed_steps, total))
        ratio = done / total
        filled = int(round(self.bar_width * ratio))
        empty = self.bar_width - filled
        percent = int(round(ratio * 100))

        bar = "#" * filled + "-" * empty
        line1 = f"[{bar}] {percent:3d}%"
        line2 = event.message

        if not self._drawn:
            self.stream.write(f"{line1}\n{line2}")
            self._drawn = True
        else:
            self.stream.write("\r\x1b[2K\x1b[1A\r\x1b[2K")
            self.stream.write(f"{line1}\n{line2}")

        self.stream.flush()

    def finish(self) -> None:
        if not self.enabled:
            return
        if self._drawn:
            self.stream.write("\n")
            self.stream.flush()
            self._drawn = False
