from pathlib import Path
from streamlit.testing.v1 import AppTest
from engineering import Well, size_pumps
APP = Path(__file__).resolve().parents[1] / 'app.py'


def test_dashboard_and_reactivity():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    assert not app.exception
    assert {expander.label for expander in app.sidebar.expander} == {
        'Operating conditions', 'Well geometry', 'Fluid properties', 'Motor assumptions'
    }
    original = app.metric[0].value
    app.number_input('Liquid rate (bbl/day)').set_value(3000.).run()
    assert not app.exception
    assert app.metric[0].value != original
    app.slider('Frequency (Hz)').set_value(50.).run()
    assert not app.exception


def test_summary_panel_for_first_eligible_pump():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    expected = size_pumps(Well())[0]
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics['Pump model'] == expected['pump']
    assert metrics['Estimated stage count'] == f"{expected['stages']:,}"
    assert metrics['Estimated electrical power (kW)'] == f"{expected['electrical_kw']:.1f}"
    assert len(app.expander) == 2
    assert app.expander[0].label == 'View efficiency and motor details'
    assert app.expander[1].label == 'View all eligible synthetic pumps'
    assert any('not a validated or optimal field design' in caption.value for caption in app.caption)


def test_invalid_geometry_and_uncovered_rate():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    app.number_input('Tubing measured length (ft)').set_value(1000.).run()
    assert app.error
    assert not app.exception
    app.number_input('Tubing measured length (ft)').set_value(6500.)
    app.number_input('Liquid rate (bbl/day)').set_value(12000.).run()
    assert any('No fictional pump' in x.value for x in app.error)
    assert 'Pump model' not in {metric.label for metric in app.metric}
    assert not app.exception
