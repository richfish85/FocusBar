import tkinter as tk
from tkinter import simpledialog
import time
import sys
import ctypes

WORK_DURATION = 25 * 60  # 25 minutes
BREAK_DURATION = 5 * 60  # 5 minutes

class PomodoroTimer:
    def __init__(self, master):
        self.master = master
        self.master.title('Pomodoro Timer')
        self.is_running = False
        self.current_time = WORK_DURATION
        self.on_break = False

        self.master.geometry('600x400')

        self.label = tk.Label(master, text=self._format_time(self.current_time), font=('Helvetica', 48))
        self.label.pack(pady=20)

        button_frame = tk.Frame(master)
        button_frame.pack(pady=10)

        self.start_button = tk.Button(button_frame, text='Start', command=self.start)
        self.start_button.pack(side='left', padx=5)
        self.stop_button = tk.Button(button_frame, text='Stop', command=self.stop)
        self.stop_button.pack(side='left', padx=5)
        self.save_button = tk.Button(button_frame, text='Save', command=self.save_session)
        self.save_button.pack(side='left', padx=5)

        dock_frame = tk.Frame(master)
        dock_frame.pack(side='bottom', pady=5)
        self.dock_bottom_btn = tk.Button(dock_frame, text='Dock Bottom', command=self.dock_bottom)
        self.dock_bottom_btn.pack(side='left', padx=5)
        self.dock_right_btn = tk.Button(dock_frame, text='Dock Right', command=self.dock_right)
        self.dock_right_btn.pack(side='left', padx=5)

        self.session_frame = tk.Frame(master)
        self.session_listbox = tk.Listbox(self.session_frame)
        self.session_listbox.pack()
        manage_frame = tk.Frame(self.session_frame)
        manage_frame.pack(pady=5)
        self.rename_button = tk.Button(manage_frame, text='Rename', command=self.rename_session)
        self.rename_button.pack(side='left', padx=5)
        self.delete_button = tk.Button(manage_frame, text='Delete', command=self.delete_session)
        self.delete_button.pack(side='left', padx=5)

        self.sessions = {}
        self.start_timestamp = None

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
            self.start_timestamp = time.time()
            self._tick()

    def stop(self):
        self.is_running = False

    def _elapsed(self):
        return WORK_DURATION - self.current_time

    def save_session(self):
        elapsed = self._elapsed()
        label = f"{self._format_time(elapsed)}/{self._format_time(WORK_DURATION)}"
        name = simpledialog.askstring('Save Session', 'Enter session name:', initialvalue=label)
        if not name:
            name = label
        self.sessions[name] = elapsed
        self.session_listbox.insert(tk.END, name)
        if not self.session_frame.winfo_ismapped():
            self.session_frame.pack(side='right', padx=10)
            self.master.geometry('1000x400')

    def rename_session(self):
        sel = self.session_listbox.curselection()
        if not sel:
            return
        current = self.session_listbox.get(sel)
        new_name = simpledialog.askstring('Rename Session', 'New name:', initialvalue=current)
        if new_name:
            self.sessions[new_name] = self.sessions.pop(current)
            self.session_listbox.delete(sel)
            self.session_listbox.insert(sel, new_name)

    def delete_session(self):
        sel = self.session_listbox.curselection()
        if not sel:
            return
        name = self.session_listbox.get(sel)
        self.session_listbox.delete(sel)
        self.sessions.pop(name, None)
        if self.session_listbox.size() == 0:
            self.session_frame.pack_forget()
            self.master.geometry('600x400')

    def dock_bottom(self):
        if sys.platform != 'win32':
            return
        user32 = ctypes.windll.user32
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        height = 100
        self.master.geometry(f"{sw}x{height}+0+{sh-height}")

    def dock_right(self):
        if sys.platform != 'win32':
            return
        user32 = ctypes.windll.user32
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        width = 200
        self.master.geometry(f"{width}x{sh}+{sw-width}+0")

if __name__ == '__main__':
    root = tk.Tk()
    timer = PomodoroTimer(root)
    root.mainloop()
