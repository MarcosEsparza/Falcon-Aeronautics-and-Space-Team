import math
import pytest
from engineering import Well, duty, size_pumps, pump_point, PUMPS, BPD_TO_M3S, G
from history import synthetic_history, compare


def test_static_head_and_power():
    w = Well(flow_bpd=100, intake_psi=150, wellhead_psi=150)
    d = duty(w)
    assert d['head_m'] == pytest.approx(6000 * .3048 + d['friction_m'])
    assert d['hydraulic_kw'] == pytest.approx(950 * G * 100 * BPD_TO_M3S * d['head_m'] / 1000)


def test_laminar_friction_independent_poiseuille():
    w = Well(flow_bpd=100, viscosity_cp=100)
    d = duty(w)
    diameter = w.tubing_id_in * .0254
    pressure_drop = 128 * .1 * (w.tubing_length_ft * .3048) * (100 * BPD_TO_M3S) / (math.pi * diameter**4)
    assert d['reynolds'] < 2300
    assert d['friction_m'] == pytest.approx(pressure_drop / (950 * G))


@pytest.mark.parametrize('field,value', [('sg', 0), ('flow_bpd', -1), ('intake_psi', float('nan')), ('depth_ft', float('inf')), ('tubing_length_ft', 50)])
def test_invalid_inputs(field, value):
    with pytest.raises(ValueError):
        duty(Well(**{field: value}))


def test_pressure_sign_and_monotonic_friction():
    assert duty(Well(intake_psi=1000))['head_m'] < duty(Well(intake_psi=900))['head_m']
    assert duty(Well(flow_bpd=3000))['friction_m'] > duty(Well(flow_bpd=2000))['friction_m']


def test_stage_rounding_and_power_balance():
    w = Well()
    row = size_pumps(w)[0]
    assert row['installed_head_m'] >= duty(w)['head_m']
    stage_head = row['installed_head_m'] / row['stages']
    assert (row['stages'] - 1) * stage_head < duty(w)['head_m']
    assert row['electrical_kw'] * .9 == pytest.approx(row['shaft_kw'])
    assert row['minimum_motor_rating_kw'] == pytest.approx(row['shaft_kw'] * 1.15)


def test_no_pump_and_no_coverage():
    assert size_pumps(Well(intake_psi=6000)) == []
    assert size_pumps(Well(flow_bpd=12000)) == []


def test_affinity_scaling_at_equal_relative_flow():
    a = size_pumps(Well(flow_bpd=3000), 60)[0]
    b = size_pumps(Well(flow_bpd=2500), 50)[0]
    assert a['pump'] == b['pump']
    assert b['installed_head_m']/b['stages'] == pytest.approx(a['installed_head_m']/a['stages'] * (50/60)**2)


def test_pump_point_matches_sizing_and_uses_fixed_stage_count():
    well = Well()
    sized = size_pumps(well)[0]
    point = pump_point(well, sized['pump'], 60, sized['stages'], well.flow_bpd)
    assert point['stages'] == sized['stages']
    assert point['installed_head_m'] == pytest.approx(sized['installed_head_m'])
    assert point['efficiency'] == pytest.approx(sized['efficiency'])
    assert point['shaft_kw'] == pytest.approx(sized['shaft_kw'])
    assert point['shaft_hp'] == pytest.approx(point['shaft_kw'] * 1.34102209)


def test_pump_point_bep_operating_limits_and_frequency_scaling():
    well = Well()
    bep, base_head, peak_eff = PUMPS['SYN-3000']
    low = pump_point(well, 'SYN-3000', 60, 100, bep * .7)
    at_bep = pump_point(well, 'SYN-3000', 60, 100, bep)
    high = pump_point(well, 'SYN-3000', 60, 100, bep * 1.2)
    scaled = pump_point(well, 'SYN-3000', 50, 100, bep * 50 / 60)
    assert low['supported'] and high['supported']
    assert at_bep['relative_flow'] == pytest.approx(1)
    assert at_bep['efficiency'] == pytest.approx(peak_eff)
    assert at_bep['stage_head_m'] == pytest.approx(base_head)
    assert scaled['stage_head_m'] == pytest.approx(base_head * (50 / 60) ** 2)
    assert not pump_point(well, 'SYN-3000', 60, 100, bep * .699)['supported']
    assert not pump_point(well, 'SYN-3000', 60, 100, bep * 1.201)['supported']


def test_history_reproducible_and_self_neighbor():
    history = synthetic_history()
    assert history.equals(synthetic_history())
    row = history.iloc[0]
    well = Well(**{key: row[key] for key in Well.__dataclass_fields__})
    neighbors, votes, outside = compare(well, history)
    assert neighbors.iloc[0]['well_id'] == row['well_id']
    assert neighbors.iloc[0]['distance'] == 0
    assert votes.sum() == pytest.approx(1)
    assert outside == []
    assert 'flow_bpd' in compare(Well(flow_bpd=12000), history)[2]
