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
                // Determine selected option
                var selectedItem = PomodoroOptions.SelectedItem as ComboBoxItem;
                int minutes = 25;
                if (selectedItem?.Tag is string tagString && int.TryParse(tagString, out int parsed))
                {
                    minutes = parsed;
                }

                _totalSeconds = minutes * 60;
                _remainingSeconds = _totalSeconds;
                TimeDisplay.Text = $"{minutes:D2}:00";
                TimerProgressBar.Value = 100;

                switch (minutes)
                {
                    case 5:
                        _currentState = PomodoroState.ShortBreak;
                        LayoutRoot.Background = new SolidColorBrush(Colors.MediumSeaGreen);
                        break;
                    case 15:
                        _currentState = PomodoroState.LongBreak;
                        LayoutRoot.Background = new SolidColorBrush(Colors.SteelBlue);
                        break;
                    default:
                        _currentState = PomodoroState.Focus;
                        LayoutRoot.Background = new SolidColorBrush(Colors.CornflowerBlue);
                        break;
                }

            _pomodoroTimer.Start();
            StartPauseButton.Content = "Pause";
            }
            else
            {
                if (_pomodoroTimer.IsEnabled)
                {
                    _pomodoroTimer.Stop();
                    StartPauseButton.Content = "Resume";
                }
                else
                {
                    _pomodoroTimer.Start();
                    StartPauseButton.Content = "Pause";
                }
            }
        }

        private void SkipButton_Click(object sender, RoutedEventArgs e)
        {
            _pomodoroTimer.Stop();
            _currentState = PomodoroState.Stopped;
            StartPauseButton.Content = "Start";
            TimerProgressBar.Value = 100;
            TimeDisplay.Text = "00:00";
            LayoutRoot.Background = new SolidColorBrush(Colors.Transparent);
            CurrentTaskText.IsReadOnly = false;
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
            TimeDisplay.Text = $"{_remainingSeconds / 60:D2}:{_remainingSeconds % 60:D2}";

            if (_remainingSeconds <= 0)
            {
                _pomodoroTimer.Stop();
                _currentState = PomodoroState.Stopped;
                StartPauseButton.Content = "Start";
                LayoutRoot.Background = new SolidColorBrush(Colors.Transparent);
                TimeDisplay.Text = "00:00";
                CurrentTaskText.IsReadOnly = false;
            }
        }

    }
}
