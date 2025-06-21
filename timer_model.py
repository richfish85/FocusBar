from dataclasses import dataclass
import time

WORK_DURATION = 25 * 60
BREAK_DURATION = 5 * 60
LONG_BREAK_DURATION = 15 * 60


@dataclass
class TimerState:
    remaining: int
    mode: str  # 'work' or 'break'
    running: bool = False


class TimerModel:
    """Pure timer logic for the Pomodoro widget."""

    def __init__(self, work: int = WORK_DURATION, short_break: int = BREAK_DURATION,
                 long_break: int = LONG_BREAK_DURATION):
        self.work = work
        self.short_break = short_break
        self.long_break = long_break
        self.state = TimerState(work, "work", False)
        self.pomo_count = 0
        self.start_timestamp = None

    def start(self):
        if not self.state.running:
            self.state.running = True
            if self.state.mode == "work":
                self.start_timestamp = time.time()

    def stop(self):
        self.state.running = False

    def reset(self):
        self.state.running = False
        self.state.remaining = self.work
        self.state.mode = "work"
        self.pomo_count = 0

    def tick(self):
        """Advance the timer by one second and return an event string."""
        if not self.state.running:
            return None
        if self.state.remaining > 0:
            self.state.remaining -= 1
        if self.state.remaining > 0:
            return None

        if self.state.mode == "work":
            self.pomo_count += 1
            self.state.mode = "break"
            self.state.remaining = self.long_break if self.pomo_count % 4 == 0 else self.short_break
            event = "work_complete"
        else:
            self.state.mode = "work"
            self.state.remaining = self.work
            event = "break_complete"
        return event

    def elapsed(self) -> int:
        if self.state.mode == "work":
            return self.work - self.state.remaining
        return self.work
