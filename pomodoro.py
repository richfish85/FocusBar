import tkinter as tk
from tkinter import ttk, simpledialog, colorchooser, messagebox
import time
import sys
import os
import json
from datetime import datetime
import ctypes
from dataclasses import dataclass

from storage import load_sessions, save_sessions

WORK_DURATION = 25 * 60  # 25 minutes
BREAK_DURATION = 5 * 60  # 5 minutes
LONG_BREAK_DURATION = 15 * 60  # 15 minutes


@dataclass
class TimerState:
    remaining: int
    mode: str  # 'work' or 'break'
    running: bool = False


class SessionDialog(tk.Toplevel):
    def __init__(self, master, categories, label):
        super().__init__(master)
        self.result = None
        self.title('Save Session')

        ttk.Label(self, text='Name:').grid(row=0, column=0, sticky='e')
        self.name_entry = ttk.Entry(self)
        self.name_entry.insert(0, label)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(self, text='Category:').grid(row=1, column=0, sticky='e')
        options = sorted(categories) + ['New...']
        self.category_var = tk.StringVar(value=options[0] if options else '')
        self.category_menu = ttk.Combobox(self, textvariable=self.category_var, values=options, state='readonly')
        self.category_menu.grid(row=1, column=1, sticky='w', padx=5, pady=2)

        ttk.Label(self, text='Notes:').grid(row=2, column=0, sticky='ne')
        self.notes = tk.Text(self, height=6, width=40)
        self.notes.grid(row=2, column=1, padx=5, pady=2)

        ttk.Button(self, text='Save', command=self._on_save).grid(row=3, column=0, columnspan=2, pady=5)

    def _on_save(self):
        name = self.name_entry.get()
        category = self.category_var.get()
        self.result = {
            'name': name,
            'category': category,
            'notes': self.notes.get('1.0', tk.END).strip()
        }
        self.destroy()

class PomodoroTimer:
    def __init__(self, master):
        self.master = master
        self.master.title('Pomodoro Timer')
        self.state = TimerState(WORK_DURATION, 'work', False)
        self.pomo_count = 0

        self.default_bg = master.cget('bg')

        self.master.geometry('600x400')

        style = ttk.Style()
        style.configure('Work.Horizontal.TProgressbar', troughcolor=self.default_bg, background='red')
        style.configure('Break.Horizontal.TProgressbar', troughcolor=self.default_bg, background='green')

        self.label = ttk.Label(master, text=self._format_time(self.state.remaining), font=('Helvetica', 48))
        self.label.pack(pady=20)

        self.progress = ttk.Progressbar(master, length=400, mode='determinate', maximum=WORK_DURATION)
        self.progress.pack(fill='x', padx=10)

        button_frame = ttk.Frame(master)
        button_frame.pack(pady=10)

        self.start_button = ttk.Button(button_frame, text='Start', command=self.start)
        self.start_button.pack(side='left', padx=5)
        self.stop_button = ttk.Button(button_frame, text='Stop', command=self.stop)
        self.stop_button.pack(side='left', padx=5)
        self.reset_button = ttk.Button(button_frame, text='Reset', command=self.reset)
        self.reset_button.pack(side='left', padx=5)
        self.save_button = ttk.Button(button_frame, text='Save', command=self.save_session)
        self.save_button.pack(side='left', padx=5)
        self.category_button = ttk.Button(button_frame, text='\U0001F5C2 Categories', command=self.manage_categories)
        self.category_button.pack(side='left', padx=5)
        self.stats_button = ttk.Button(button_frame, text='Stats', command=self.show_stats)
        self.stats_button.pack(side='left', padx=5)

        dock_frame = ttk.Frame(master)
        dock_frame.pack(side='bottom', pady=5)
        self.dock_bottom_btn = ttk.Button(dock_frame, text='Dock Bottom', command=self.dock_bottom)
        self.dock_bottom_btn.pack(side='left', padx=5)
        self.dock_right_btn = ttk.Button(dock_frame, text='Dock Right', command=self.dock_right)
        self.dock_right_btn.pack(side='left', padx=5)

        self.session_frame = ttk.Frame(master)
        filter_frame = ttk.Frame(self.session_frame)
        filter_frame.pack(fill='x')
        ttk.Label(filter_frame, text='Filter:').pack(side='left')
        self.filter_var = tk.StringVar(value='All')
        self.filter_menu = ttk.Combobox(filter_frame, textvariable=self.filter_var, state='readonly')
        self.filter_menu.pack(side='left', padx=5)
        self.filter_menu.bind('<<ComboboxSelected>>', lambda e: self.refresh_sessions())

        self.session_listbox = tk.Listbox(self.session_frame)
        self.session_listbox.pack()
        self.session_listbox.bind('<Double-1>', self.view_session)
        manage_frame = ttk.Frame(self.session_frame)
        manage_frame.pack(pady=5)
        self.rename_button = ttk.Button(manage_frame, text='Rename', command=self.rename_session)
        self.rename_button.pack(side='left', padx=5)
        self.delete_button = ttk.Button(manage_frame, text='Delete', command=self.delete_session)
        self.delete_button.pack(side='left', padx=5)

        self.sessions = {}
        self.categories = {}
        self.start_timestamp = None

        self.load_data()
        self.master.protocol('WM_DELETE_WINDOW', self.on_close)

        # key bindings
        master.bind('<space>', self.toggle)
        master.bind('s', lambda e: self.save_session())
        master.bind('r', lambda e: self.reset())

        self._update_display()

    def _color_emoji(self, hex_color: str) -> str:
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
        except Exception:
            r = g = b = 0
        if r < 40 and g < 40 and b < 40:
            return '⬛'
        if r > 220 and g > 220 and b > 220:
            return '⬜'
        if r >= g and r >= b:
            if g > b:
                return '🟧'
            return '🟥'
        if g >= r and g >= b:
            return '🟩'
        return '🟦'

    def update_filter_options(self):
        options = ['All'] + sorted(self.categories.keys())
        self.filter_menu['values'] = options
        if self.filter_var.get() not in options:
            self.filter_var.set('All')

    def refresh_sessions(self):
        self.session_listbox.delete(0, tk.END)
        selected = self.filter_var.get()
        for name, data in self.sessions.items():
            cat = data.get('category', '')
            if selected == 'All' or cat == selected:
                color = self.categories.get(cat, '#000000')
                self.session_listbox.insert(tk.END, f"{self._color_emoji(color)} {name}")

    def show_stats(self):
        today = datetime.now().date()
        totals = {}
        for data in self.sessions.values():
            ts = data.get('timestamp')
            if ts and datetime.fromtimestamp(ts).date() == today:
                cat = data.get('category', '')
                totals[cat] = totals.get(cat, 0) + data.get('elapsed', 0)
        if not totals:
            messagebox.showinfo('Stats', 'No sessions recorded today')
            return
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        fig, ax = plt.subplots(figsize=(4, 3))
        cats = list(totals.keys())
        mins = [totals[c] / 60 for c in cats]
        ax.bar(cats, mins, color=[self.categories.get(c, '#888888') for c in cats])
        ax.set_ylabel('Minutes')
        ax.set_title('Today')
        dialog = tk.Toplevel(self.master)
        dialog.title('Daily Stats')
        canvas = FigureCanvasTkAgg(fig, master=dialog)
        canvas.draw()
        canvas.get_tk_widget().pack()
        ttk.Button(dialog, text='Close', command=dialog.destroy).pack(pady=5)

    def _format_time(self, seconds):
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    def _update_display(self):
        self.label.config(text=self._format_time(self.state.remaining))
        if self.state.mode == 'break':
            self.progress.configure(style='Break.Horizontal.TProgressbar', maximum=BREAK_DURATION if self.pomo_count % 4 else LONG_BREAK_DURATION)
        else:
            self.progress.configure(style='Work.Horizontal.TProgressbar', maximum=WORK_DURATION)
        self.progress['value'] = (self.progress['maximum'] - self.state.remaining)

    def _tick(self):
        if self.state.running:
            if self.state.remaining > 0:
                self.state.remaining -= 1
            else:
                self._alert()
                if self.state.mode == 'work':
                    self.pomo_count += 1
                    if self.pomo_count % 4 == 0:
                        self.state.remaining = LONG_BREAK_DURATION
                    else:
                        self.state.remaining = BREAK_DURATION
                    self.state.mode = 'break'
                else:
                    self.state.mode = 'work'
                    self.state.remaining = WORK_DURATION
            self._update_display()
            self.master.after(1000, self._tick)

    def start(self):
        if not self.state.running:
            self.state.running = True
            if self.state.mode == 'work':
                self.start_timestamp = time.time()
            self._update_display()
            self._tick()

    def stop(self):
        self.state.running = False

    def toggle(self, event=None):
        if self.state.running:
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
        self.state.running = False
        self.state.remaining = WORK_DURATION
        self.state.mode = 'work'
        self.pomo_count = 0
        self._update_display()

    def _elapsed(self):
        if self.state.mode == 'work':
            return WORK_DURATION - self.state.remaining
        return WORK_DURATION

    def save_session(self):
        elapsed = self._elapsed()
        label = f"{self._format_time(elapsed)}/{self._format_time(WORK_DURATION)}"
        dialog = SessionDialog(self.master, self.categories.keys(), label)
        dialog.wait_window()
        if not dialog.result:
            return
        name = dialog.result['name'] or label
        category = dialog.result['category']
        if category == 'New...':
            new_cat = simpledialog.askstring('New Category', 'Category name:')
            if new_cat:
                color = colorchooser.askcolor()[1] or '#ffffff'
                self.categories[new_cat] = color
                category = new_cat
                self.update_filter_options()
        self.sessions[name] = {
            'elapsed': elapsed,
            'timestamp': self.start_timestamp,
            'category': category,
            'notes': dialog.result['notes']
        }
        self.refresh_sessions()
        if not self.session_frame.winfo_ismapped():
            self.session_frame.pack(side='right', padx=10)
            self.master.geometry('1000x400')
        self.save_data()

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
            self.refresh_sessions()
            self.save_data()

    def delete_session(self):
        sel = self.session_listbox.curselection()
        if not sel:
            return
        name = self.session_listbox.get(sel)
        self.session_listbox.delete(sel)
        self.sessions.pop(name, None)
        self.refresh_sessions()
        if self.session_listbox.size() == 0:
            self.session_frame.pack_forget()
            self.master.geometry('600x400')
        self.save_data()

    def view_session(self, event=None):
        sel = self.session_listbox.curselection()
        if not sel:
            return
        name = self.session_listbox.get(sel)
        data = self.sessions.get(name, {})

        dialog = tk.Toplevel(self.master)
        dialog.title(name)

        tk.Label(dialog, text=f"Elapsed: {self._format_time(data.get('elapsed', 0))}").pack(anchor='w', padx=5)
        ts = data.get('timestamp')
        if ts:
            tk.Label(dialog, text=f"Started: {time.ctime(ts)}").pack(anchor='w', padx=5)

        tk.Label(dialog, text='Category:').pack(anchor='w', padx=5)
        categories = sorted(self.categories.keys())
        category_var = tk.StringVar(value=data.get('category', ''))
        cat_menu = tk.OptionMenu(dialog, category_var, *categories)
        cat_menu.config(state='disabled')
        cat_menu.pack(padx=5, anchor='w')

        tk.Label(dialog, text='Notes:').pack(anchor='w', padx=5)
        notes = tk.Text(dialog, height=6, width=40)
        notes.insert('1.0', data.get('notes', ''))
        notes.config(state='disabled')
        notes.pack(padx=5, pady=5)

        def enable_edit():
            notes.config(state='normal')
            cat_menu.config(state='normal')
            edit_btn.pack_forget()
            tk.Button(dialog, text='Save', command=save_edit).pack(pady=5)

        def save_edit():
            data['notes'] = notes.get('1.0', tk.END).strip()
            data['category'] = category_var.get()
            self.sessions[name] = data
            self.save_data()
            dialog.destroy()

        edit_btn = tk.Button(dialog, text='Edit', command=enable_edit)
        edit_btn.pack(pady=5)

    def manage_categories(self):
        dialog = tk.Toplevel(self.master)
        dialog.title('Categories')

        listbox = tk.Listbox(dialog)
        listbox.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        for c in self.categories:
            listbox.insert(tk.END, c)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(side='right', fill='y')

        def refresh_list():
            listbox.delete(0, tk.END)
            for c in self.categories:
                listbox.insert(tk.END, c)
            self.update_filter_options()

        def add_cat():
            name = simpledialog.askstring('Add Category', 'Name:')
            if name:
                color = colorchooser.askcolor()[1] or '#ffffff'
                self.categories[name] = color
                refresh_list()
                self.save_data()
                self.update_filter_options()

        def rename_cat():
            sel = listbox.curselection()
            if not sel:
                return
            old = listbox.get(sel)
            new = simpledialog.askstring('Rename Category', 'New name:', initialvalue=old)
            if new:
                self.categories[new] = self.categories.pop(old)
                refresh_list()
                self.save_data()
                self.update_filter_options()

        def delete_cat():
            sel = listbox.curselection()
            if not sel:
                return
            name = listbox.get(sel)
            if name in self.categories:
                self.categories.pop(name)
                for s in self.sessions.values():
                    if s.get('category') == name:
                        s['category'] = ''
                refresh_list()
                self.save_data()
                self.update_filter_options()

        def change_color():
            sel = listbox.curselection()
            if not sel:
                return
            name = listbox.get(sel)
            color = colorchooser.askcolor(color=self.categories.get(name, '#ffffff'))[1]
            if color:
                self.categories[name] = color
                self.save_data()

        ttk.Button(btn_frame, text='Add', command=add_cat).pack(fill='x')
        ttk.Button(btn_frame, text='Rename', command=rename_cat).pack(fill='x')
        ttk.Button(btn_frame, text='Delete', command=delete_cat).pack(fill='x')
        ttk.Button(btn_frame, text='Color', command=change_color).pack(fill='x')

    def load_data(self):
        data = load_sessions()
        self.sessions = data.get('sessions', {})
        self.categories = data.get('categories', {})
        self.update_filter_options()
        self.refresh_sessions()
        if self.sessions:
            self.session_frame.pack(side='right', padx=10)
            self.master.geometry('1000x400')

    def save_data(self):
        data = {'sessions': self.sessions, 'categories': self.categories}
        save_sessions(data)

    def on_close(self):
        self.save_data()
        self.master.destroy()

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
    root.protocol('WM_DELETE_WINDOW', timer.on_close)
    root.mainloop()
