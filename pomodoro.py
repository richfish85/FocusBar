import tkinter as tk
import time
import threading

WORK_DURATION = 25 * 60  # 25 minutes
BREAK_DURATION = 5 * 60  # 5 minutes

class PomodoroTimer:
    def __init__(self, master):
        self.master = master
        self.master.title('Pomodoro Timer')
        self.is_running = False
        self.current_time = WORK_DURATION
        self.on_break = False

        self.label = tk.Label(master, text=self._format_time(self.current_time), font=('Helvetica', 48))
        self.label.pack(pady=20)

        self.start_button = tk.Button(master, text='Start', command=self.start)
        self.start_button.pack(side='left', padx=10)
        self.stop_button = tk.Button(master, text='Stop', command=self.stop)
        self.stop_button.pack(side='right', padx=10)

    def _format_time(self, seconds):
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    def _tick(self):
        if self.is_running:
            if self.current_time > 0:
                self.current_time -= 1
            else:
                self.on_break = not self.on_break
                self.current_time = BREAK_DURATION if self.on_break else WORK_DURATION
            self.label.config(text=self._format_time(self.current_time))
            self.master.after(1000, self._tick)

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._tick()

    def stop(self):
        self.is_running = False

if __name__ == '__main__':
    root = tk.Tk()
    timer = PomodoroTimer(root)
    root.mainloop()
