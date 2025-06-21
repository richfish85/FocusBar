from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt


def aggregate(sessions_by_date, start_date, end_date):
    total = {}
    for date, sess in sessions_by_date.items():
        if start_date <= date <= end_date:
            for s in sess.values():
                cat = s.get("category") or "Uncategorised"
                total[cat] = total.get(cat, 0) + s.get("elapsed", 0)
    return total


def setup(frame):
    period_var = tk.StringVar(value="Day")
    toggle = ttk.Frame(frame)
    toggle.pack(pady=2)
    for val in ("Day", "Week", "Month"):
        ttk.Radiobutton(toggle, text=val, variable=period_var, value=val).pack(side="left")

    fig_cat, ax_cat = plt.subplots(figsize=(2.5, 2.5))
    canvas_cat = FigureCanvasTkAgg(fig_cat, master=frame)
    canvas_cat.get_tk_widget().pack()

    fig_spark, ax_spark = plt.subplots(figsize=(2.5, 0.8))
    canvas_spark = FigureCanvasTkAgg(fig_spark, master=frame)
    canvas_spark.get_tk_widget().pack(fill="x")

    return {
        "period_var": period_var,
        "ax_cat": ax_cat,
        "ax_spark": ax_spark,
        "canvas_cat": canvas_cat,
        "canvas_spark": canvas_spark,
    }


def refresh(ctx, sessions_by_date):
    end = datetime.now().date()
    if ctx["period_var"].get() == "Day":
        start = end
    elif ctx["period_var"].get() == "Week":
        start = end - timedelta(days=6)
    else:
        start = end - timedelta(days=29)

    totals = aggregate(sessions_by_date, start.isoformat(), end.isoformat())
    ctx["ax_cat"].clear()
    if totals:
        cats = list(totals.keys())
        mins = [totals[c] / 60 for c in cats]
        ctx["ax_cat"].pie(mins, labels=cats)
    ctx["canvas_cat"].draw()

    ctx["ax_spark"].clear()
    vals = []
    d = start
    while d <= end:
        key = d.isoformat()
        total = sum(
            s.get("elapsed", 0) / 60 for s in sessions_by_date.get(key, {}).values()
        )
        vals.append(total)
        d += timedelta(days=1)
    ctx["ax_spark"].plot(range(len(vals)), vals, color="blue")
    ctx["ax_spark"].axis("off")
    ctx["canvas_spark"].draw()


def show_stats(master, sessions_by_date, categories):
    today = datetime.now().date()
    totals = {}
    for sess in sessions_by_date.get(today.isoformat(), {}).values():
        cat = sess.get("category", "")
        totals[cat] = totals.get(cat, 0) + sess.get("elapsed", 0)
    if not totals:
        messagebox.showinfo("Stats", "No sessions recorded today")
        return
    fig, ax = plt.subplots(figsize=(4, 3))
    cats = list(totals.keys())
    mins = [totals[c] / 60 for c in cats]
    ax.bar(cats, mins, color=[categories.get(c, "#888888") for c in cats])
    ax.set_ylabel("Minutes")
    ax.set_title("Today")
    dialog = tk.Toplevel(master)
    dialog.title("Daily Stats")
    canvas = FigureCanvasTkAgg(fig, master=dialog)
    canvas.draw()
    canvas.get_tk_widget().pack()
    ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=5)
