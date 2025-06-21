# Pomodoro Widget

This repository contains a simple Pomodoro timer written in Python. It provides a minimal GUI using Tkinter to manage work and break intervals. The widget now lets you save sessions, manage categories and even dock the window on Windows systems.

## Usage

Run the application with Python 3:

```bash
python3 pomodoro.py
```

Press **Start** to begin the timer. The timer will alternate between 25-minute work sessions and 5-minute breaks.
Use **Save** to record your progress. Sessions are written to `~/.pomopad/sessions_YYYY-MM.json` so they persist between runs. Saved sessions appear in a list on the right. Double-click a session to view details or edit notes and category. Use the **🗂 Categories** button to create, rename or delete categories and pick a colour for each. Use **Dock Bottom** or **Dock Right** to attach the window to the respective side of the screen on Windows.
