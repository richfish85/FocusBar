import tkinter as tk
from tkinter import simpledialog, colorchooser, messagebox, ttk
import time
import sys
from datetime import datetime, timedelta
import ctypes
import os
from PIL import Image, ImageTk

try:
    import darkdetect  # type: ignore
    DARK = darkdetect.isDark()
except Exception:
    DARK = False

from storage import load_sessions, save_sessions
from timer_model import (
    TimerModel,
    WORK_DURATION,
    BREAK_DURATION,
    LONG_BREAK_DURATION,
)
from ui_analytics import (
    setup as analytics_setup,
    refresh as analytics_refresh,
    show_stats,
)
from ui_sessions import SessionsPane

ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")

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
        self.model = TimerModel()
        self.active_name = 'Session'

        self.style = ttk.Style()
        self.style.configure('Work.Horizontal.TProgressbar', background='red')
        self.style.configure('Break.Horizontal.TProgressbar', background='green')
        self.style.theme_use('vista')

        self.theme_var = tk.BooleanVar(value=DARK)
        self.apply_theme()
        self.default_bg = master.cget('background')

        self.nb = ttk.Notebook(master)
        self.nb.pack(fill='both', expand=True)

        self.timer_frame = ttk.Frame(self.nb)
        self.session_frame = ttk.Frame(self.nb)
        self.analytics_frame = ttk.Frame(self.nb)

        self.nb.add(self.timer_frame, text='Timer')
        self.nb.add(self.session_frame, text='Sessions')
        self.nb.add(self.analytics_frame, text='Analytics')

        self.label = ttk.Label(
            self.timer_frame,
            text=self._format_time(self.model.state.remaining),
            font=('Helvetica', 48),
        )
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

        self.icons = {
            name: ImageTk.PhotoImage(Image.open(os.path.join(ICON_DIR, f"{name}.ico")))
            for name in ("start", "stop", "reset", "category", "stats")
        }

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
        self.theme_switch = ttk.Checkbutton(
            button_frame,
            text='\u263E' if self.theme_var.get() else '\u2600',
            variable=self.theme_var,
            onvalue=True,
            offvalue=False,
            command=self.apply_theme,
        )
        self.theme_switch.pack(side='left', padx=2)

        # analytics and sessions
        self.sessions_pane = SessionsPane(self.session_frame, self.view_session)
        self.sessions_pane.pack(fill='both', expand=True)
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
        self.streak = 0

        # analytics widgets
        self.analytics_ctx = analytics_setup(self.analytics_frame)
        self.analytics_ctx["period_var"].trace_add("write", lambda *a: self.refresh_analytics())

        self.load_data()
        self.master.protocol('WM_DELETE_WINDOW', self.on_close)

        master.bind('<space>', self.toggle)

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
        self.sessions_pane.categories = self.categories
        self.sessions_pane.update_filter_options()

    def refresh_sessions(self):
        self.sessions_pane.sessions_by_date = self.sessions_by_date
        self.sessions_pane.categories = self.categories
        self.sessions_pane.update_list()

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
        analytics_refresh(self.analytics_ctx, self.sessions_by_date)

    def show_stats(self):
        show_stats(self.master, self.sessions_by_date, self.categories)

    def apply_theme(self, *_):
        if self.theme_var.get():
            self.master.tk_setPalette(background='#333333', foreground='#ffffff')
            if hasattr(self, 'theme_switch'):
                self.theme_switch.config(text='\u263E')
        else:
            self.master.tk_setPalette(background='', foreground='')
            if hasattr(self, 'theme_switch'):
                self.theme_switch.config(text='\u2600')

    def _format_time(self, seconds):
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    def _update_display(self):
        self.label.config(text=self._format_time(self.model.state.remaining))
        if self.model.state.mode == 'break':
            self.progress.configure(
                style='Break.Horizontal.TProgressbar',
                maximum=BREAK_DURATION if self.model.pomo_count % 4 else LONG_BREAK_DURATION,
            )
        else:
            self.progress.configure(style='Work.Horizontal.TProgressbar', maximum=WORK_DURATION)
        self.progress['value'] = (self.progress['maximum'] - self.model.state.remaining)
        text = (
            f"{self.active_name} \u2794 \u23F1 {self._format_time(self.model.state.remaining)} left "
            f"\u2022 \U0001F345 {self.model.pomo_count} \u2022 \U0001F525 {self.streak}"
        )
        self.status_var.set(text)

    def _tick(self):
        event = self.model.tick()
        if event:
            self._alert(event)
        if self.model.state.running:
            self._update_display()
            self.master.after(1000, self._tick)

    def start(self):
        if not self.model.state.running:
            self.model.start()
            self._update_display()
            self._tick()

    def stop(self):
        self.model.stop()

    def toggle(self, event=None):
        if self.model.state.running:
            self.stop()
        else:
            self.start()

    def _alert(self, event):
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

        if event == 'work_complete':
            if messagebox.askyesno('Work complete', 'Save this session?'):
                self.quick_save_session()

    def reset(self, event=None):
        self.model.reset()
        self._update_display()

    def _elapsed(self):
        return self.model.elapsed()

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
        ts = self.model.start_timestamp
        date_key = datetime.fromtimestamp(ts).date().isoformat() if ts else datetime.now().date().isoformat()

        self.refresh_analytics()
        self._update_display()

    def quick_save_session(self, event=None):
        """Save current session using the text entry without showing a dialog."""
        elapsed = self._elapsed()
        name = self.quick_name_var.get() or f"Session {len(self.flat_sessions)+1}"
        ts = self.model.start_timestamp
        date_key = datetime.fromtimestamp(ts).date().isoformat() if ts else datetime.now().date().isoformat()
        self.sessions_by_date.setdefault(date_key, {})[name] = {
            'elapsed': elapsed,
            'timestamp': ts,
            'category': '',
            'notes': ''
        }
        self.flat_sessions[name] = (date_key, self.sessions_by_date[date_key][name])
        self.active_name = name
        self.refresh_sessions()
        self.streak = self.compute_streak()
        self.save_data()
        self.refresh_analytics()
        self._update_display()


    def rename_session(self):
        sel = self.sessions_pane.listbox.curselection()
        if not sel:
            return
        current = self.sessions_pane.listbox.get(sel)
        new_name = simpledialog.askstring('Rename Session', 'New name:', initialvalue=current)
        if new_name:
            date_key, data = self.flat_sessions.pop(current)
            self.sessions_by_date[date_key].pop(current)
            self.sessions_by_date[date_key][new_name] = data
            self.flat_sessions[new_name] = (date_key, data)
            self.sessions_pane.listbox.delete(sel)
            self.sessions_pane.listbox.insert(sel, new_name)
            self.refresh_sessions()
            self.save_data()
            self.streak = self.compute_streak()
            self.refresh_analytics()
            self._update_display()

    def delete_session(self):
        sel = self.sessions_pane.listbox.curselection()
        if not sel:
            return
        name = self.sessions_pane.listbox.get(sel)
        self.sessions_pane.listbox.delete(sel)
        date_key, _ = self.flat_sessions.pop(name)
        self.sessions_by_date.get(date_key, {}).pop(name, None)
        self.refresh_sessions()
        self.save_data()
        self.streak = self.compute_streak()
        self.refresh_analytics()
        self._update_display()
        self.streak = self.compute_streak()
        self.refresh_analytics()

    def view_session(self, event=None):
        sel = self.sessions_pane.listbox.curselection()
        if not sel:
            return
        name = self.sessions_pane.listbox.get(sel)
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

        ttk.Button(dialog, text='Close', command=dialog.destroy).pack(pady=5)

    def load_data(self):
        data = load_sessions()
        self.sessions_by_date = data.get('sessions_by_date', {})
        self.categories = data.get('categories', {})
        self.theme_var.set(bool(data.get('theme', self.theme_var.get())))
        self.apply_theme()
        self.flat_sessions = {
            name: (date, sess[name])
            for date, sess in self.sessions_by_date.items()
            for name in sess
        }
        self.streak = self.compute_streak()
        self.sessions_pane.set_data(self.sessions_by_date, self.categories)
        if self.sessions_by_date:
            pass

    def save_data(self):
        data = {
            'sessions_by_date': self.sessions_by_date,
            'categories': self.categories,
            'theme': self.theme_var.get(),
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

    def manage_categories(self):
        dialog = tk.Toplevel(self.master)
        dialog.title("Manage Categories")
        dialog.geometry("300x400")

        listbox = tk.Listbox(dialog)
        listbox.pack(fill='both', expand=True, padx=5, pady=5)
        for cat in sorted(self.categories.keys()):
            listbox.insert('end', cat)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', padx=5, pady=5)

        def refresh_list():
            listbox.delete(0, 'end')
            for cat in sorted(self.categories.keys()):
                listbox.insert('end', cat)
            self.update_filter_options()

        def add_cat():
            new_cat = simpledialog.askstring('New Category', 'Category name:', parent=dialog)
            if new_cat and new_cat not in self.categories:
                color = colorchooser.askcolor()[1] or '#ffffff'
                self.categories[new_cat] = color
                refresh_list()
                self.save_data()
                self.update_filter_options()

        def rename_cat():
            sel = listbox.curselection()
            if not sel:
                return
            old_name = listbox.get(sel)
            new_name = simpledialog.askstring('Rename Category', 'New name:', initialvalue=old_name, parent=dialog)
            if new_name and new_name not in self.categories:
                self.categories[new_name] = self.categories.pop(old_name)
                # update sessions with old category name
                for date, sess in self.sessions_by_date.items():
                    for s in sess.values():
                        if s.get('category') == old_name:
                            s['category'] = new_name
                refresh_list()
                self.save_data()
                self.update_filter_options()

        def delete_cat():
            sel = listbox.curselection()
            if not sel:
                return
            name = listbox.get(sel)
            if messagebox.askyesno('Delete Category', f'Delete category "{name}"?', parent=dialog):
                self.categories.pop(name, None)
                # remove category from sessions
                for date, sess in self.sessions_by_date.items():
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


# create the main application window
def main():
    root = tk.Tk()
    app = PomodoroTimer(root)
    app.dock_right()  # or app.dock_right() for right docking
    root.mainloop()

if __name__ == "__main__":
    main()  
