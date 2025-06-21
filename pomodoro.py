import tkinter as tk
from tkinter import simpledialog, colorchooser, messagebox
from ttkbootstrap import Window
from ttkbootstrap import ttk
import time
import sys
import os
import json
from datetime import datetime, timedelta
import ctypes
from dataclasses import dataclass

from storage import load_sessions, save_sessions
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

WORK_DURATION = 25 * 60  # 25 minutes
BREAK_DURATION = 5 * 60  # 5 minutes
LONG_BREAK_DURATION = 15 * 60  # 15 minutes

ICONS = {
    'start': "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAgUlEQVR4nNWWOw6AQAhEZ4z3NntyrOh0+cdIucV7YYBkKSKYrGOU/qmAiy3ZbTvokJgRcVEqIvcMspLQkDOS8BZFI0uvqVdSugOPpHxoVmRtl/wmaRPIJXx6P6fAWqUOLHhJ4IEDiYi8YK1QB1F4SJCBA46IsmCtbQdVOADw97+KGyQfMDeUrtBPAAAAAElFTkSuQmCC",
    'stop': "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAOElEQVR4nGP8//8/Ay0BE01NH7VgUFjAglOGkZH05PX/PyO60NAPolELRi0YtWA4WMA4WmUOfwsAeXsJK4myg7UAAAAASUVORK5CYII=",
    'reset': "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAnklEQVR4nNWVSw6AQAhDqfH+V64rjTFMKeMnsUslr3RGECSjIyBIBtz6tQNudeIazIJ3LVUBGegcSdsgExB0k6G6ZAekEsoEd+ER4pKv8AzkNJAmcODqeWnQhbQMzt3fhacGT8teFZVGyV9P8L3BOZ69DsSHUSaoTKr3qcG1ixHEmna17Dr/gtHMyCNyB03Vlev6KEzSOA3YBrP6/6BtALFJJqQrTwIAAAAASUVORK5CYII=",
    'stats': "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAASklEQVR4nGP8//8/Ay0BE01NH7VgUFjAQqkBjYyNGMmw/n89I4w99INo8MQBobDGBYZ+ENE/DsgNa1xg6AfRqAUDbwHjaKVPCAAAwEASLwxuQ+4AAAAASUVORK5CYII=",
    'category': "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAUElEQVR4nGP8//8/Ay0BE01NH7VgUFjAgiGyjJFwsor6z0isBQPgA2IAIV8i+XA4RjIyICEycQXb0A+ioW8B/kgmJlcTAEM/iBhHq8zhbwEAM8kQ16VzPcYAAAAASUVORK5CYII="
}


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
        self.active_name = 'Session'

        self.style = ttk.Style()
        self.style.configure('Work.Horizontal.TProgressbar', background='red')
        self.style.configure('Break.Horizontal.TProgressbar', background='green')
        self.theme = 'superhero'

        self.paned = ttk.PanedWindow(master, orient='horizontal')
        self.paned.pack(fill='both', expand=True)

        self.timer_frame = ttk.Frame(self.paned)
        self.paned.add(self.timer_frame, weight=1)

        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=1)

        self.label = ttk.Label(self.timer_frame, text=self._format_time(self.state.remaining), font=('Helvetica', 48))
        self.label.pack(pady=20)

        # entry for quick session name
        self.quick_name_var = tk.StringVar(value='Session')
        self.name_entry = ttk.Entry(self.timer_frame, textvariable=self.quick_name_var)
        self.name_entry.pack(pady=2)
        self.name_entry.bind('<Return>', self.quick_save_session)

        self.progress = ttk.Progressbar(self.timer_frame, length=200, mode='determinate', maximum=WORK_DURATION)
        self.progress.pack(fill='x', padx=10)

        button_frame = ttk.Frame(self.timer_frame)
        button_frame.pack(pady=10)

        self.icons = {k: tk.PhotoImage(data=v) for k, v in ICONS.items()}

        self.start_button = ttk.Button(button_frame, image=self.icons['start'], command=self.start)
        self.start_button.pack(side='left', padx=2)
        self.stop_button = ttk.Button(button_frame, image=self.icons['stop'], command=self.stop)
        self.stop_button.pack(side='left', padx=2)
        self.reset_button = ttk.Button(button_frame, image=self.icons['reset'], command=self.reset)
        self.reset_button.pack(side='left', padx=2)
        self.save_button = ttk.Button(button_frame, text='Save', command=self.save_session)
        self.save_button.pack(side='left', padx=2)
        self.category_button = ttk.Button(button_frame, image=self.icons['category'], command=self.manage_categories)
        self.category_button.pack(side='left', padx=2)
        self.stats_button = ttk.Button(button_frame, image=self.icons['stats'], command=self.show_stats)
        self.stats_button.pack(side='left', padx=2)

        self.dark_var = tk.BooleanVar(value=False)
        self.dark_toggle = ttk.Checkbutton(button_frame, text='Dark Mode', variable=self.dark_var, command=self.toggle_theme)
        self.dark_toggle.pack(side='left', padx=2)

        # analytics and sessions
        self.analytics_frame = ttk.Frame(right_frame)
        self.analytics_frame.pack(fill='both', expand=True)

        self.session_frame = ttk.Frame(right_frame)
        filter_frame = ttk.Frame(self.session_frame)
        filter_frame.pack(fill='x')
        ttk.Label(filter_frame, text='Filter:').pack(side='left')
        self.filter_var = tk.StringVar(value='All')
        self.filter_menu = ttk.Combobox(filter_frame, textvariable=self.filter_var, state='readonly')
        self.filter_menu.pack(side='left', padx=5)
        self.filter_menu.bind('<<ComboboxSelected>>', lambda e: self.refresh_sessions())

        self.session_listbox = tk.Listbox(self.session_frame)
        self.session_listbox.pack(fill='both', expand=True)
        self.session_listbox.bind('<Double-1>', self.view_session)
        manage_frame = ttk.Frame(self.session_frame)
        manage_frame.pack(pady=5)
        self.rename_button = ttk.Button(manage_frame, text='Rename', command=self.rename_session)
        self.rename_button.pack(side='left', padx=5)
        self.delete_button = ttk.Button(manage_frame, text='Delete', command=self.delete_session)
        self.delete_button.pack(side='left', padx=5)

        # bottom bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(master, textvariable=self.status_var, anchor='w')
        self.status_bar.pack(fill='x', side='bottom')

        self.sessions_by_date = {}
        self.flat_sessions = {}
        self.categories = {}
        self.start_timestamp = None
        self.streak = 0

        # analytics widgets
        self.period_var = tk.StringVar(value='Day')
        toggle = ttk.Frame(self.analytics_frame)
        toggle.pack(pady=2)
        for val in ('Day', 'Week', 'Month'):
            ttk.Radiobutton(toggle, text=val, variable=self.period_var, value=val, command=self.refresh_analytics).pack(side='left')

        self.fig_cat, self.ax_cat = plt.subplots(figsize=(2.5, 2.5))
        self.canvas_cat = FigureCanvasTkAgg(self.fig_cat, master=self.analytics_frame)
        self.canvas_cat.get_tk_widget().pack()

        self.fig_spark, self.ax_spark = plt.subplots(figsize=(2.5, 0.8))
        self.canvas_spark = FigureCanvasTkAgg(self.fig_spark, master=self.analytics_frame)
        self.canvas_spark.get_tk_widget().pack(fill='x')

        self.load_data()
        self.master.protocol('WM_DELETE_WINDOW', self.on_close)

        master.bind('<space>', self.toggle)
        master.bind('s', lambda e: self.save_session())
        master.bind('r', lambda e: self.reset())

        self._update_display()
        self.refresh_analytics()

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
        for date, sess in self.sessions_by_date.items():
            for name, data in sess.items():
                cat = data.get('category', '')
                if selected == 'All' or cat == selected:
                    color = self.categories.get(cat, '#000000')
                    self.session_listbox.insert(tk.END, f"{self._color_emoji(color)} {name}")

    def aggregate(self, start_date, end_date):
        total = {}
        for date, sess in self.sessions_by_date.items():
            if start_date <= date <= end_date:
                for s in sess.values():
                    cat = s.get('category') or 'Uncategorised'
                    total[cat] = total.get(cat, 0) + s.get('elapsed', 0)
        return total

    def compute_streak(self):
        today = datetime.now().date()
        streak = 0
        d = today
        while True:
            key = d.isoformat()
            if key in self.sessions_by_date and self.sessions_by_date[key]:
                streak += 1
                d -= timedelta(days=1)
            else:
                break
        return streak

    def refresh_analytics(self):
        end = datetime.now().date()
        if self.period_var.get() == 'Day':
            start = end
        elif self.period_var.get() == 'Week':
            start = end - timedelta(days=6)
        else:
            start = end - timedelta(days=29)
        totals = self.aggregate(start.isoformat(), end.isoformat())
        self.ax_cat.clear()
        if totals:
            cats = list(totals.keys())
            mins = [totals[c] / 60 for c in cats]
            self.ax_cat.pie(mins, labels=cats)
        self.canvas_cat.draw()

        self.ax_spark.clear()
        days = []
        vals = []
        d = start
        while d <= end:
            key = d.isoformat()
            total = sum(s.get('elapsed', 0) / 60 for s in self.sessions_by_date.get(key, {}).values())
            days.append(d)
            vals.append(total)
            d += timedelta(days=1)
        self.ax_spark.plot(range(len(vals)), vals, color='blue')
        self.ax_spark.axis('off')
        self.canvas_spark.draw()

    def show_stats(self):
        today = datetime.now().date()
        totals = {}
        for sess in self.sessions_by_date.get(today.isoformat(), {}).values():
            cat = sess.get('category', '')
            totals[cat] = totals.get(cat, 0) + sess.get('elapsed', 0)
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
        text = f"{self.active_name} \u2192 \u23F1 {self._format_time(self.state.remaining)} left • 🍅 #{self.pomo_count} today • Focus streak: {self.streak} days"
        self.status_var.set(text)

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
        date_key = datetime.fromtimestamp(self.start_timestamp).date().isoformat() if self.start_timestamp else datetime.now().date().isoformat()
        self.sessions_by_date.setdefault(date_key, {})[name] = {
            'elapsed': elapsed,
            'timestamp': self.start_timestamp,
            'category': category,
            'notes': dialog.result['notes']
        }
        self.flat_sessions[name] = (date_key, self.sessions_by_date[date_key][name])
        self.active_name = name
        self.refresh_sessions()
        if not self.session_frame.winfo_ismapped():
            self.session_frame.pack(fill='both', expand=True)
        self.streak = self.compute_streak()
        self.save_data()
        self.refresh_analytics()
        self._update_display()

    def quick_save_session(self, event=None):
        """Save current session using the text entry without showing a dialog."""
        elapsed = self._elapsed()
        name = self.quick_name_var.get() or f"Session {len(self.flat_sessions)+1}"
        date_key = datetime.fromtimestamp(self.start_timestamp).date().isoformat() if self.start_timestamp else datetime.now().date().isoformat()
        self.sessions_by_date.setdefault(date_key, {})[name] = {
            'elapsed': elapsed,
            'timestamp': self.start_timestamp,
            'category': '',
            'notes': ''
        }
        self.flat_sessions[name] = (date_key, self.sessions_by_date[date_key][name])
        self.active_name = name
        self.refresh_sessions()
        if not self.session_frame.winfo_ismapped():
            self.session_frame.pack(fill='both', expand=True)
        self.streak = self.compute_streak()
        self.save_data()
        self.refresh_analytics()
        self._update_display()

    def toggle_theme(self):
        """Switch between light and dark themes and persist the choice."""
        if self.dark_var.get():
            self.style.theme_use('darkly')
            self.theme = 'darkly'
        else:
            self.style.theme_use('superhero')
            self.theme = 'superhero'
        self.save_data()

    def rename_session(self):
        sel = self.session_listbox.curselection()
        if not sel:
            return
        current = self.session_listbox.get(sel)
        new_name = simpledialog.askstring('Rename Session', 'New name:', initialvalue=current)
        if new_name:
            date_key, data = self.flat_sessions.pop(current)
            self.sessions_by_date[date_key].pop(current)
            self.sessions_by_date[date_key][new_name] = data
            self.flat_sessions[new_name] = (date_key, data)
            self.session_listbox.delete(sel)
            self.session_listbox.insert(sel, new_name)
            self.refresh_sessions()
            self.save_data()
            self.streak = self.compute_streak()
            self.refresh_analytics()
            self._update_display()

    def delete_session(self):
        sel = self.session_listbox.curselection()
        if not sel:
            return
        name = self.session_listbox.get(sel)
        self.session_listbox.delete(sel)
        date_key, _ = self.flat_sessions.pop(name)
        self.sessions_by_date.get(date_key, {}).pop(name, None)
        self.refresh_sessions()
        if self.session_listbox.size() == 0:
            self.session_frame.pack_forget()
        self.save_data()
        self.streak = self.compute_streak()
        self.refresh_analytics()
        self._update_display()
        self.streak = self.compute_streak()
        self.refresh_analytics()

    def view_session(self, event=None):
        sel = self.session_listbox.curselection()
        if not sel:
            return
        name = self.session_listbox.get(sel)
        date_key, data = self.flat_sessions.get(name, (None, {}))

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
            if date_key:
                self.sessions_by_date[date_key][name] = data
                self.flat_sessions[name] = (date_key, data)
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
                for sess in self.sessions_by_date.values():
                    for s in sess.values():
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
        self.sessions_by_date = data.get('sessions_by_date', {})
        self.categories = data.get('categories', {})
        self.theme = data.get('theme', 'superhero')
        try:
            self.style.theme_use(self.theme)
            self.dark_var.set(self.theme == 'darkly')
        except Exception:
            pass
        self.flat_sessions = {
            name: (date, sess[name])
            for date, sess in self.sessions_by_date.items()
            for name in sess
        }
        self.streak = self.compute_streak()
        self.update_filter_options()
        self.refresh_sessions()
        if self.sessions_by_date:
            self.session_frame.pack(fill='both', expand=True)

    def save_data(self):
        data = {
            'sessions_by_date': self.sessions_by_date,
            'categories': self.categories,
            'theme': self.theme
        }
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
    root = Window(themename='superhero')
    timer = PomodoroTimer(root)
    root.protocol('WM_DELETE_WINDOW', timer.on_close)
    root.mainloop()
