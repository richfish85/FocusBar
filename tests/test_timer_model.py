import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from timer_model import TimerModel


def test_timer_transitions():
    model = TimerModel(work=2, short_break=1, long_break=3)
    model.start()
    # finish work
    model.tick()
    model.tick()
    assert model.state.mode == "break"
    assert model.state.remaining == 1
    # finish short break
    model.tick()
    assert model.state.mode == "work"
    assert model.state.remaining == 2


def test_long_break_cycle():
    model = TimerModel(work=1, short_break=1, long_break=3)
    model.start()
    for i in range(4):
        model.tick()
        assert model.state.mode == "break"
        expected = 3 if (i + 1) % 4 == 0 else 1
        assert model.state.remaining == expected
        # advance through the break
        while model.state.mode == "break":
            model.tick()
        assert model.state.mode == "work"
    assert model.pomo_count == 4
