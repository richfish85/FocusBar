from pathlib import Path
import webview
from timer_model import TimerModel


class API:
    def __init__(self):
        self.model = TimerModel()

    def start(self):
        self.model.start()
        return True

    def stop(self):
        self.model.stop()
        return True

    def reset(self):
        self.model.reset()
        return True

    def tick(self):
        event = self.model.tick()
        return {
            'remaining': self.model.state.remaining,
            'mode': self.model.state.mode,
            'running': self.model.state.running,
            'event': event,
        }


def main():
    api = API()
    html = (Path(__file__).parent / 'web' / 'index.html').read_text()
    window = webview.create_window('Pomodoro', html=html, js_api=api)
    webview.start()


if __name__ == '__main__':
    main()
