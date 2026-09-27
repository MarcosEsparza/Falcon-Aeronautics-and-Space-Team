"""Run with: streamlit run app.py."""
from dataclasses import asdict
import json
import pandas as pd
import streamlit as st
from engineering import Well, duty, size_pumps
from history import synthetic_history, compare

st.set_page_config(page_title='ESP Design Intelligence', page_icon='⚙', layout='wide')
st.title('ESP Design Intelligence')
st.caption('Electric submersible pump screening • Synthetic demonstration • No external AI service')
st.warning('All historical wells and pump curves are fictional. Outputs are preliminary single-phase screening estimates, not field-ready designs.')
with st.sidebar:
    st.header('Well and operating target')
    flow = st.number_input('Liquid rate (bbl/day)', 100., 12000., 2500., 100.)
    depth = st.number_input('Pump vertical depth (ft)', 100., 15000., 6000., 100.)
    length = st.number_input('Tubing measured length (ft)', 100., 20000., 6500., 100.)
    diameter = st.number_input('Tubing internal diameter (in)', 1., 6., 2.5, .1)
    sg = st.number_input('Liquid specific gravity', .5, 1.5, .95, .01)
    viscosity = st.number_input('Dynamic viscosity (cP)', .1, 100., 1., .1)
    whp = st.number_input('Wellhead pressure (psig)', 0., 3000., 150., 25.)
    pip = st.number_input('Pump intake pressure (psig)', 0., 6000., 900., 25.)
    frequency = st.slider('Frequency (Hz)', 40., 70., 60.)
    motor_eff = st.slider('Motor efficiency', .70, 1., .90, .01)
    margin = st.slider('Motor shaft-power margin', 0., .50, .15, .01)
well = Well(flow, depth, length, diameter, sg, viscosity, whp, pip)
try:
    load = duty(well)
    candidates = size_pumps(well, frequency, motor_eff, margin)
except ValueError as exc:
    st.error(str(exc))
    st.stop()
cols = st.columns(3)
cols[0].metric('Required pump head', f"{load['head_m']:.0f} m")
cols[1].metric('Tubing friction head', f"{load['friction_m']:.0f} m")
cols[2].metric('Hydraulic power at duty', f"{load['hydraulic_kw']:.1f} kW")
if load['raw_head_m'] <= 0:
    st.info('This prescribed-flow balance requires no positive pump head. Check natural-flow feasibility with an inflow and outflow model.')
if 2300 < load['reynolds'] < 4000:
    st.warning('Transitional pipe flow: friction is interpolated and uncertain.')
if viscosity > 5:
    st.warning('Viscosity exceeds the synthetic history range. Pump curves have no viscosity correction.')
sizing, analogs, assumptions = st.tabs(['Engineering sizing', 'AI-assisted historical comparison', 'Method and limits'])
with sizing:
    st.subheader('Eligible fictional pumps')
    st.caption('Screened at 70–120% of speed-adjusted best efficiency point flow. Ranked by electrical power at the requested flow.')
    if candidates:
        selected = candidates[0]
        st.subheader('Synthetic pump recommendation')
        st.caption('First eligible result from the existing screening engine. Synthetic demonstration only; not a validated or optimal field design.')
        summary = st.container(border=True)
        summary_top = summary.columns(2)
        summary_top[0].metric('Pump model', selected['pump'])
        summary_top[1].metric('Estimated stage count', f"{selected['stages']:,}")
        summary_bottom = summary.columns(3)
        summary_bottom[0].metric('Modeled pump efficiency', f"{selected['efficiency']:.1%}")
        summary_bottom[1].metric('Estimated electrical power (kW)', f"{selected['electrical_kw']:.1f}")
        summary_bottom[2].metric('Minimum motor shaft-power rating (kW)', f"{selected['minimum_motor_rating_kw']:.1f}")
        with st.expander('View all eligible synthetic pumps'):
            st.dataframe(pd.DataFrame(candidates), hide_index=True)
    elif load['head_m'] > 0:
        st.error('No fictional pump covers this rate at the selected frequency. Change the target or extend the catalog.')
    st.caption('Stage rounding adds head. Actual operating flow requires a pump/system-curve intersection; motor rating is shaft power plus margin, not electrical input.')
    sensitivity = []
    for multiplier in [.8, .9, 1., 1.1, 1.2]:
        point = Well(**(asdict(well) | {'flow_bpd': flow * multiplier}))
        sensitivity.append({'flow_bpd': point.flow_bpd, 'required_head_m': duty(point)['head_m']})
    st.subheader('Required head vs. liquid production')
    st.line_chart(
        pd.DataFrame(sensitivity),
        x='flow_bpd',
        y='required_head_m',
        x_label='Liquid production (bbl/day)',
        y_label='Required head (m)',
        height=320,
    )
with analogs:
    history = synthetic_history()
    k = st.slider('Historical neighbors', 3, 20, 8)
    neighbors, votes, outside = compare(well, history, k)
    st.write(f'Nearest-neighbor suggestion at historical 60 Hz: **{votes.index[0]}** ({votes.iloc[0]:.0%} of neighbor labels).')
    st.caption('This is an interpretable machine-learning classifier over synthetic engineering labels. Vote share is not confidence, reliability, or probability of success. Current-frequency engineering eligibility takes precedence.')
    if outside:
        st.warning('Outside synthetic feature coverage: ' + ', '.join(outside))
    st.dataframe(neighbors[['well_id', 'pump', 'distance', 'flow_bpd', 'depth_ft', 'sg', 'viscosity_cp', 'intake_psi', 'tubing_id_in', 'head_m']], hide_index=True)
    st.download_button('Download synthetic history CSV', history.to_csv(index=False), 'synthetic_history.csv', 'text/csv')
with assumptions:
    st.markdown('''Steady incompressible liquid with constant density and viscosity. Pump intake and wellhead pressures use the same gauge reference. Vertical depth sets elevation head; measured tubing length sets friction. Equal endpoint velocity heads; minor losses omitted.

Darcy–Weisbach friction uses 64/Re for laminar flow and the Haaland approximation for turbulent flow, with interpolation between Reynolds numbers 2300 and 4000. Tubing roughness is fixed at 0.045 mm.

Pump head = elevation rise + pressure-head difference + friction head. Hydraulic power = density × gravity × flow × head. Fictional pump curves use affinity scaling at constant geometry.

Before field design: verify inflow/drawdown, multiphase outflow, free gas and gas separation, viscosity corrections, net positive suction head, motor cooling, temperature, cable/drive losses, casing clearance, thrust, shaft/stage limits, materials and sand handling. These are not evaluated here.''')
    st.json(load)
st.download_button('Download design JSON', json.dumps({'synthetic_demo': True, 'well': asdict(well), 'frequency_hz': frequency, 'motor_efficiency': motor_eff, 'motor_margin': margin, 'duty': load, 'candidates': candidates}, indent=2), 'esp_screening_design.json', 'application/json')
