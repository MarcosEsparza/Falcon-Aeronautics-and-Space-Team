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
    original = next(metric.value for metric in app.metric if metric.label == 'REQUIRED HEAD')
    next(x for x in app.sidebar.number_input if x.label == 'Liquid rate (bbl/day)').set_value(3000.).run()
    assert not app.exception
    updated = next(metric.value for metric in app.metric if metric.label == 'REQUIRED HEAD')
    assert updated != original
    next(x for x in app.sidebar.slider if x.label == 'Frequency (Hz)').set_value(50.).run()
    assert not app.exception


def test_design_snapshot_uses_existing_duty_values():
    app = run_app()
    expected = duty(Well())
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics['REQUIRED HEAD'] == f"{expected['head_m']:.0f} m"
    assert metrics['TUBING FRICTION HEAD'] == f"{expected['friction_m']:.0f} m"
    assert metrics['HYDRAULIC POWER'] == f"{expected['hydraulic_kw']:.1f} kW"
    assert sum(item.value == 'Design Snapshot' for item in app.subheader) == 1


def test_summary_panel_for_first_eligible_pump():
    app = run_app()
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
    assert any('not a validated field design' in caption.value for caption in app.caption)


def test_required_head_chart_identifies_requested_duty_from_duty_result():
    app = run_app()
    expected = duty(Well())
    assert any(
        'Requested duty point' in caption.value
        and '2,500 bbl/day' in caption.value
        and f"{expected['head_m']:.0f} m" in caption.value
        for caption in app.caption
    )
    assert any('System required head' in subheader.value for subheader in app.subheader)


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
    assert 'Pump model' not in {metric.label for metric in app.metric}
    labels = [item.label for item in app.expander]
    assert 'Efficiency and motor details' not in labels
    assert 'View all eligible synthetic pumps' not in labels
    assert not app.exception


def test_root_streamlit_theme_uses_supported_dark_palette():
    config = tomllib.loads(THEME.read_text())
    assert config == {
        'theme': {
            'base': 'dark',
            'primaryColor': '#29A77D',
            'backgroundColor': '#101A1C',
            'secondaryBackgroundColor': '#1A292B',
            'textColor': '#F3F7F5',
            'font': 'sans serif',
        }
    }
