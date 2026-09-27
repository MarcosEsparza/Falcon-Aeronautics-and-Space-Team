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
    next(x for x in app.sidebar.number_input if x.label == 'Liquid rate (bbl/day)').set_value(3000.).run()
    assert not app.exception
    assert app.metric[0].value != original
    next(x for x in app.sidebar.slider if x.label == 'Frequency (Hz)').set_value(50.).run()
    assert not app.exception


def test_summary_panel_for_first_eligible_pump():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    assert not app.exception
    expected = size_pumps(Well())[0]
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics['Pump model'] == expected['pump']
    assert metrics['Modeled pump efficiency'] == f"{expected['efficiency']:.1%}"
    assert metrics['Minimum motor shaft-power rating (kW)'] == f"{expected['minimum_motor_rating_kw']:.1f}"
    assert any(
        f"{expected['stages']:,} stages" in item.value
        and f"{expected['electrical_kw']:.1f} kW" in item.value
        for item in app.markdown
    )
    labels = [item.label for item in app.expander]
    assert 'Efficiency and motor details' in labels
    assert 'View all eligible synthetic pumps' in labels
    assert any(
        'not a validated or optimal field design' in caption.value
        for caption in app.caption
    )


def test_invalid_geometry_and_uncovered_rate():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    next(x for x in app.sidebar.number_input if x.label == 'Tubing measured length (ft)').set_value(1000.).run()
    assert app.error
    assert not app.exception
    next(x for x in app.sidebar.number_input if x.label == 'Tubing measured length (ft)').set_value(6500.)
    next(x for x in app.sidebar.number_input if x.label == 'Liquid rate (bbl/day)').set_value(12000.).run()
    assert any('No fictional pump' in x.value for x in app.error)
    assert 'Pump model' not in {metric.label for metric in app.metric}
    labels = [item.label for item in app.expander]
    assert 'Efficiency and motor details' not in labels
    assert 'View all eligible synthetic pumps' not in labels
    assert not app.exception
