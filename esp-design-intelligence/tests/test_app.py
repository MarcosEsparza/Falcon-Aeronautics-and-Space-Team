from pathlib import Path
import tomllib

from streamlit.testing.v1 import AppTest

from engineering import Well, duty, size_pumps

PROJECT = Path(__file__).resolve().parents[1]
APP = PROJECT / 'app.py'
THEME = PROJECT.parent / '.streamlit' / 'config.toml'


def run_app():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    assert not app.exception
    return app


def test_dashboard_inputs_and_reactivity():
    app = run_app()
    assert {expander.label for expander in app.sidebar.expander} == {
        'Operating conditions', 'Well geometry', 'Fluid properties', 'Motor assumptions'
    }
    original = next(metric.value for metric in app.metric if metric.label == 'Required head')
    next(x for x in app.sidebar.number_input if x.label == 'Liquid rate (bbl/day)').set_value(3000.).run()
    assert not app.exception
    updated = next(metric.value for metric in app.metric if metric.label == 'Required head')
    assert updated != original
    next(x for x in app.sidebar.slider if x.label == 'Frequency (Hz)').set_value(50.).run()
    assert not app.exception


def test_design_snapshot_uses_existing_duty_values():
    app = run_app()
    expected = duty(Well())
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics['Required head'] == f"{expected['head_m']:.0f} m"
    assert metrics['Target rate'] == '2,500 bbl/day'
    assert metrics['Friction head'] == f"{expected['friction_m']:.0f} m"
    assert metrics['Hydraulic power'] == f"{expected['hydraulic_kw']:.1f} kW"
    assert sum(item.value == 'Design snapshot' for item in app.subheader) == 1


def test_selection_panel_matches_first_eligible_pump():
    app = run_app()
    expected = size_pumps(Well())[0]
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics['Estimated stage count'] == f"{expected['stages']:,}"
    assert metrics['Modeled efficiency'] == f"{expected['efficiency']:.1%}"
    assert metrics['Shaft horsepower'] == f"{expected['shaft_kw'] * 1.34102209:.1f} hp"
    assert metrics['Estimated electrical input'] == f"{expected['electrical_kw']:.1f} kW"
    assert metrics['Minimum motor shaft-power rating'] == f"{expected['minimum_motor_rating_kw']:.1f} kW"
    assert any(expected['pump'] in item.value for item in app.markdown)
    assert any('not a validated field design' in caption.value for caption in app.caption)


def test_three_curve_views_and_requested_duty_are_present():
    app = run_app()
    headings = {item.value for item in app.subheader}
    assert {'Pump and system head', 'Pump shaft horsepower', 'Modeled pump efficiency'} <= headings
    assert len(app.get('vega_lite_chart')) >= 3
    expected = duty(Well())
    assert any(
        'fixed installed stage count' in caption.value
        and 'requested flow' in caption.value
        and '70–120%' in caption.value
        and 'not a validated well operating point' in caption.value
        for caption in app.caption
    )
    assert expected['head_m'] > 0


def test_eligible_pump_table_has_human_readable_columns():
    app = run_app()
    table = app.dataframe[0].value
    assert list(table.columns) == [
        'Pump model', 'Stages', 'Requested flow / BEP', 'Modeled efficiency',
        'Installed head (m)', 'Shaft power (kW)', 'Modeled electrical input (kW)',
        'Minimum motor shaft-power rating (kW)',
    ]
    assert table.iloc[0]['Pump model'] == size_pumps(Well())[0]['pump']


def test_invalid_geometry_and_uncovered_rate():
    app = run_app()
    next(x for x in app.sidebar.number_input if x.label == 'Tubing measured length (ft)').set_value(1000.).run()
    assert app.error
    assert not app.exception
    next(x for x in app.sidebar.number_input if x.label == 'Tubing measured length (ft)').set_value(6500.)
    next(x for x in app.sidebar.number_input if x.label == 'Liquid rate (bbl/day)').set_value(12000.).run()
    assert any('No fictional pump' in x.value for x in app.error)
    assert 'Estimated stage count' not in {metric.label for metric in app.metric}
    assert 'View all eligible synthetic pumps' not in [item.label for item in app.expander]
    assert not app.exception


def test_history_language_does_not_call_vote_share_confidence():
    app = run_app()
    assert any('Vote share describes' in caption.value and 'not confidence' in caption.value for caption in app.caption)
    assert any('Descriptive proximity' in caption.value and 'not confidence' in caption.value for caption in app.caption)


def test_root_streamlit_theme_uses_supported_dark_palette():
    config = tomllib.loads(THEME.read_text())
    assert config == {'theme': {'base': 'dark', 'primaryColor': '#29A77D', 'backgroundColor': '#101A1C', 'secondaryBackgroundColor': '#1A292B', 'textColor': '#F3F7F5', 'font': 'sans serif'}}
