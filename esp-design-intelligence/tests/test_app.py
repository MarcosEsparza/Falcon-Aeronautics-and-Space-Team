from pathlib import Path
from streamlit.testing.v1 import AppTest
APP = Path(__file__).resolve().parents[1] / 'app.py'


def test_dashboard_and_reactivity():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    assert not app.exception
    original = app.metric[0].value
    app.number_input[0].set_value(3000.).run()
    assert not app.exception
    assert app.metric[0].value != original
    app.slider[0].set_value(50.).run()
    assert not app.exception


def test_invalid_geometry_and_uncovered_rate():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    app.number_input[2].set_value(1000.).run()
    assert app.error
    assert not app.exception
    app.number_input[2].set_value(6500.)
    app.number_input[0].set_value(12000.).run()
    assert any('No fictional pump' in x.value for x in app.error)
    assert not app.exception
