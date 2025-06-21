using Microsoft.UI;
using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Controls.Primitives;
using Microsoft.UI.Xaml.Data;
using Microsoft.UI.Xaml.Input;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Navigation;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices.WindowsRuntime;
using Windows.Foundation;
using Windows.Foundation.Collections;
using Windows.UI;

// To learn more about WinUI, the WinUI project structure,
// and more about our project templates, see: http://aka.ms/winui-project-info.

namespace FocusBar
{
    /// <summary>
    /// An empty window that can be used on its own or navigated to within a Frame.
    /// </summary>
    public sealed partial class MainWindow : Window
    {
        private int _totalSeconds;
        private int _remainingSeconds;
        private enum PomodoroState { Stopped, Focus, ShortBreak, LongBreak }
        private PomodoroState _currentState = PomodoroState.Stopped;
        private DispatcherTimer _pomodoroTimer = new DispatcherTimer();

        private void StartPauseButton_Click(object sender, Microsoft.UI.Xaml.RoutedEventArgs e)
        {
            CurrentTaskText.IsReadOnly = true;
            if (_currentState == PomodoroState.Stopped)
            {
                // Start a new Focus session
                _currentState = PomodoroState.Focus;
                _totalSeconds = 25 * 60; // 25 minutes
                _remainingSeconds = _totalSeconds;
                _pomodoroTimer.Start();
                StartPauseButton.Content = "Pause"; // Update button text
                                                    // Change the background color to indicate focus
                LayoutRoot.Background = new Microsoft.UI.Xaml.Media.SolidColorBrush(Colors.CornflowerBlue);
                CurrentTaskText.IsReadOnly = false;
            }

            // Add else if logic here for "Pause" and "Resume"
        }

        public MainWindow()
        {
            InitializeComponent();

            _pomodoroTimer.Interval = TimeSpan.FromSeconds(1);
            _pomodoroTimer.Tick += PomodoroTimer_Tick; // We will create this method next


            var hwnd = WinRT.Interop.WindowNative.GetWindowHandle(this);
            var windowId = Microsoft.UI.Win32Interop.GetWindowIdFromWindow(hwnd);
            var appWindow = AppWindow.GetFromWindowId(windowId);

            // Set the presenter to Overlapped (the standard window mode)
            var presenter = appWindow.Presenter as OverlappedPresenter;
            if (presenter != null)
            {
                presenter.IsMaximizable = false;
                presenter.IsMinimizable = false;
                presenter.IsResizable = false;
                presenter.SetBorderAndTitleBar(false, false); // This makes it borderless!
            }

            // Get screen dimensions
            var displayArea = DisplayArea.GetFromWindowId(windowId, DisplayAreaFallback.Primary);
            var screenWidth = displayArea.WorkArea.Width;
            var screenHeight = displayArea.WorkArea.Height;

            // Define our Focus Bar width
            const int focusBarWidth = 100; // You can make this a setting later

            // Set the size and position
            appWindow.Resize(new Windows.Graphics.SizeInt32(focusBarWidth, screenHeight));
            appWindow.Move(new Windows.Graphics.PointInt32(screenWidth - focusBarWidth, 0));
        }

        private void PomodoroTimer_Tick(object sender, object e)
        {
            _remainingSeconds--;

            // Update the ProgressBar
            TimerProgressBar.Value = ((double)_remainingSeconds / _totalSeconds) * 100;

            if (_remainingSeconds <= 0)
            {
                _pomodoroTimer.Stop();
                // Logic to switch to the next state (e.g., from Focus to Break) goes here
                // Play a sound, change the color, etc.
            }
        }

    }
}
