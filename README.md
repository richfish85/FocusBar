# Pomodoro Widget

This repository contains a simple Pomodoro timer written in Python. It provides a minimal GUI using Tkinter to manage work and break intervals. The widget now lets you save sessions, manage categories and even dock the window on Windows systems.

## Usage

Run the application with Python 3:

```bash
python3 pomodoro.py
```

Press **Start** to begin the timer. A progress bar tracks each cycle and turns green during breaks. After four completed pomodoros a 15 minute long break is automatically scheduled. Use **Save** to record your progress. Sessions are written to `~/.pomopad/sessions_YYYY-MM.json` so they persist between runs. Saved sessions appear in a list on the right and can be filtered by category with the dropdown above the list. Double-click a session to view details or edit notes and category. Use the **🗂 Categories** button to create, rename or delete categories and pick a colour for each. The **Stats** button pops up a small bar chart of today's focused minutes per category. Use **Dock Bottom** or **Dock Right** to attach the window to the respective side of the screen on Windows.
