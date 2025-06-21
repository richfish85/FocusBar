import tkinter as tk
from tkinter import ttk

class SessionsPane(ttk.Frame):
    """List of saved sessions with filter dropdown and details pane."""

    def __init__(self, master, on_view):
        super().__init__(master)
        self.on_view = on_view
        top = ttk.Frame(self)
        top.pack(fill='x')
        ttk.Label(top, text='Filter:').pack(side='left')
        self.filter_var = tk.StringVar(value='All')
        self.filter_menu = ttk.Combobox(top, textvariable=self.filter_var, state='readonly')
        self.filter_menu.pack(side='left', padx=5)
        self.filter_menu.bind('<<ComboboxSelected>>', lambda e: self.update_list())

        self.listbox = tk.Listbox(self)
        self.listbox.pack(fill='both', expand=True)
        self.listbox.bind('<Double-1>', lambda e: self.on_view())
        self.listbox.bind('<<ListboxSelect>>', self._show_details)

        self.detail = tk.Text(self, height=4, state='disabled')
        self.detail.pack(fill='x', pady=2)

        self.sessions_by_date = {}
        self.categories = {}

    def set_data(self, sessions_by_date, categories):
        self.sessions_by_date = sessions_by_date
        self.categories = categories
        self.update_filter_options()
        self.update_list()

    def update_filter_options(self):
        options = ['All'] + sorted(self.categories.keys())
        self.filter_menu['values'] = options
        if self.filter_var.get() not in options:
            self.filter_var.set('All')

    def update_list(self):
        self.listbox.delete(0, tk.END)
        selected = self.filter_var.get()
        for date, sess in self.sessions_by_date.items():
            for name, data in sess.items():
                cat = data.get('category', '')
                if selected == 'All' or cat == selected:
                    self.listbox.insert(tk.END, name)
        self._show_details()

    def _show_details(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            self.detail.config(state='normal'); self.detail.delete('1.0', tk.END); self.detail.config(state='disabled');
            return
        name = self.listbox.get(sel)
        for date, sess in self.sessions_by_date.items():
            if name in sess:
                data = sess[name]
                break
        else:
            data = {}
        text = f"Elapsed: {data.get('elapsed', 0)}s\nCategory: {data.get('category','')}"
        self.detail.config(state='normal')
        self.detail.delete('1.0', tk.END)
        self.detail.insert('1.0', text)
        self.detail.config(state='disabled')