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

        self.default_bg = master.cget('bg')

        self.master.geometry('600x400')

        self.label = tk.Label(master, text=self._format_time(self.current_time), font=('Helvetica', 48))
        self.label.pack(pady=20)

        button_frame = tk.Frame(master)
        button_frame.pack(pady=10)

        self.start_button = tk.Button(button_frame, text='Start', command=self.start)
        self.start_button.pack(side='left', padx=5)
        self.stop_button = tk.Button(button_frame, text='Stop', command=self.stop)
        self.stop_button.pack(side='left', padx=5)
        self.reset_button = tk.Button(button_frame, text='Reset', command=self.reset)
        self.reset_button.pack(side='left', padx=5)
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

        # key bindings
        master.bind('<space>', self.toggle)
        master.bind('s', lambda e: self.save_session())
        master.bind('r', lambda e: self.reset())

    def _format_time(self, seconds):
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    def _tick(self):
        if self.is_running:
            if self.current_time > 0:
                self.current_time -= 1
            else:
                self._alert()
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

    def toggle(self, event=None):
        if self.is_running:
            self.stop()
        else:
            self.start()

    def _alert(self):
        # play sound
        try:
            if sys.platform == 'win32':
                import winsound
                winsound.MessageBeep()
            else:
                import simpleaudio as sa
                import math
                import struct
                freq = 880
                fs = 44100
                dur = 0.2
                samples = [math.sin(2 * math.pi * freq * t / fs) for t in range(int(fs*dur))]
                audio = b''.join(struct.pack('<h', int(s*32767*0.3)) for s in samples)
                sa.play_buffer(audio, 1, 2, fs)
        except Exception:
            try:
                self.master.bell()
            except Exception:
                pass

        # flash background
        self.master.config(bg='yellow')
        self.master.after(1000, lambda: self.master.config(bg=self.default_bg))

    def reset(self, event=None):
        self.is_running = False
        self.current_time = WORK_DURATION
        self.on_break = False
        self.label.config(text=self._format_time(self.current_time))

    def _elapsed(self):
        return WORK_DURATION - self.current_time

    def save_session(self):
        elapsed = self._elapsed()
        label = f"{self._format_time(elapsed)}/{self._format_time(WORK_DURATION)}"

        dialog = tk.Toplevel(self.master)
        dialog.title('Save Session')

        tk.Label(dialog, text='Name:').grid(row=0, column=0, sticky='e')
        name_entry = tk.Entry(dialog)
        name_entry.insert(0, label)
        name_entry.grid(row=0, column=1, padx=5, pady=2)

        tk.Label(dialog, text='Category:').grid(row=1, column=0, sticky='e')
        categories = sorted({v.get('category') for v in self.sessions.values() if isinstance(v, dict) and v.get('category')})
        categories.append('New...')
        category_var = tk.StringVar(value=categories[0] if categories else '')
        tk.OptionMenu(dialog, category_var, *categories).grid(row=1, column=1, sticky='w', padx=5, pady=2)

        tk.Label(dialog, text='Notes:').grid(row=2, column=0, sticky='ne')
        notes_widget = tk.Text(dialog, height=6, width=40)
        notes_widget.grid(row=2, column=1, padx=5, pady=2)

        def on_save():
            name = name_entry.get() or label
            category = category_var.get()
            if category == 'New...':
                new_cat = simpledialog.askstring('New Category', 'Category name:')
                if new_cat:
                    category = new_cat
            notes_text = notes_widget.get('1.0', tk.END).strip()
            self.sessions[name] = {
                'elapsed': elapsed,
                'timestamp': self.start_timestamp,
                'category': category,
                'notes': notes_text
            }
            self.session_listbox.insert(tk.END, name)
            if not self.session_frame.winfo_ismapped():
                self.session_frame.pack(side='right', padx=10)
                self.master.geometry('1000x400')
            dialog.destroy()

        tk.Button(dialog, text='Save', command=on_save).grid(row=3, column=0, columnspan=2, pady=5)

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
