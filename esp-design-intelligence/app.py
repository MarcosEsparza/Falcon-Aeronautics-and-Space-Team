"""Run with: streamlit run app.py."""
from dataclasses import asdict
import json

import altair as alt
import pandas as pd
import streamlit as st

from engineering import Well, duty, size_pumps
from history import synthetic_history, compare

st.set_page_config(page_title='ESP Design Intelligence', page_icon='⚙', layout='wide')
st.title('ESP Design Intelligence')
st.caption('Electric submersible pump screening · Synthetic engineering demonstration')
st.warning('Fictional historical wells and pumps are not validated field designs.')

with st.sidebar:
    st.header('Well and operating target')
    with st.expander('Operating conditions', expanded=True):
        flow = st.number_input('Liquid rate (bbl/day)', 100., 12000., 2500., 100.)
        whp = st.number_input('Wellhead pressure (psig)', 0., 3000., 150., 25.)
        pip = st.number_input('Pump intake pressure (psig)', 0., 6000., 900., 25.)
        frequency = st.slider('Frequency (Hz)', 40., 70., 60.)
    with st.expander('Well geometry'):
        depth = st.number_input('Pump vertical depth (ft)', 100., 15000., 6000., 100.)
        length = st.number_input('Tubing measured length (ft)', 100., 20000., 6500., 100.)
        diameter = st.number_input('Tubing internal diameter (in)', 1., 6., 2.5, .1)
    with st.expander('Fluid properties'):
        sg = st.number_input('Liquid specific gravity', .5, 1.5, .95, .01)
        viscosity = st.number_input('Dynamic viscosity (cP)', .1, 100., 1., .1)
    with st.expander('Motor assumptions'):
        motor_eff = st.slider('Motor efficiency', .70, 1., .90, .01)
        margin = st.slider('Motor shaft-power margin', 0., .50, .15, .01)

well = Well(flow, depth, length, diameter, sg, viscosity, whp, pip)
try:
    load = duty(well)
    candidates = size_pumps(well, frequency, motor_eff, margin)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

with st.container(border=True):
    st.subheader('Design Snapshot')
    st.metric('REQUIRED HEAD', f"{load['head_m']:.0f} m")
    st.metric('TUBING FRICTION HEAD', f"{load['friction_m']:.0f} m")
    st.metric('HYDRAULIC POWER', f"{load['hydraulic_kw']:.1f} kW")

if load['raw_head_m'] <= 0:
    st.info('This prescribed-flow balance requires no positive pump head. Check natural-flow feasibility with an inflow and outflow model.')
if 2300 < load['reynolds'] < 4000:
    st.warning('Transitional pipe flow: friction is interpolated and uncertain.')
if viscosity > 5:
    st.warning('Viscosity exceeds the synthetic history range. Pump curves have no viscosity correction.')

sizing, analogs, assumptions = st.tabs(['Sizing', 'History', 'Method'])
with sizing:
    st.subheader('Eligible fictional pumps')
    st.caption('Screened at 70–120% of speed-adjusted best efficiency point flow. Ranked by electrical power at the requested flow.')
    if candidates:
        selected = candidates[0]
        st.subheader('Synthetic screening candidate')
        with st.container(border=True):
            st.metric('Pump model', selected['pump'])
            st.markdown(
                f"**{selected['stages']:,} stages** · "
                f"**{selected['electrical_kw']:.1f} kW** modeled electrical input"
            )
            st.caption('First eligible synthetic screening result; not a validated field design.')

        with st.expander('Efficiency and motor details'):
            st.metric('Modeled pump efficiency', f"{selected['efficiency']:.1%}")
            st.metric(
                'Minimum motor shaft-power rating (kW)',
                f"{selected['minimum_motor_rating_kw']:.1f}",
            )

        with st.expander('View all eligible synthetic pumps'):
            pump_table = pd.DataFrame(candidates)[[
                'pump', 'stages', 'relative_flow', 'efficiency', 'installed_head_m',
                'shaft_kw', 'electrical_kw', 'minimum_motor_rating_kw',
            ]].rename(columns={
                'pump': 'Pump model',
                'stages': 'Stages',
                'relative_flow': 'Requested flow / BEP',
                'efficiency': 'Modeled efficiency',
                'installed_head_m': 'Installed head (m)',
                'shaft_kw': 'Shaft power (kW)',
                'electrical_kw': 'Modeled electrical input (kW)',
                'minimum_motor_rating_kw': 'Minimum motor shaft-power rating (kW)',
            })
            st.dataframe(
                pump_table,
                hide_index=True,
                use_container_width=True,
                column_config={
                    'Stages': st.column_config.NumberColumn(format='%d'),
                    'Requested flow / BEP': st.column_config.NumberColumn(format='%.2f'),
                    'Modeled efficiency': st.column_config.NumberColumn(format='percent'),
                    'Installed head (m)': st.column_config.NumberColumn(format='%.0f'),
                    'Shaft power (kW)': st.column_config.NumberColumn(format='%.1f'),
                    'Modeled electrical input (kW)': st.column_config.NumberColumn(format='%.1f'),
                    'Minimum motor shaft-power rating (kW)': st.column_config.NumberColumn(format='%.1f'),
                },
            )
    elif load['head_m'] > 0:
        st.error('No fictional pump covers this rate at the selected frequency. Change the target or extend the catalog.')

    st.caption('Stage rounding adds head. Actual operating flow requires a pump/system-curve intersection; motor rating is shaft power plus margin, not electrical input.')
    sensitivity = []
    for multiplier in [.8, .9, 1., 1.1, 1.2]:
        point = Well(**(asdict(well) | {'flow_bpd': flow * multiplier}))
        sensitivity.append({
            'Liquid rate (bbl/day)': point.flow_bpd,
            'Required head (m)': duty(point)['head_m'],
        })
    sensitivity_frame = pd.DataFrame(sensitivity)
    requested_duty = pd.DataFrame([{
        'Liquid rate (bbl/day)': flow,
        'Required head (m)': load['head_m'],
        'Series': 'Requested duty point',
    }])
    axes = {
        'x': alt.X('Liquid rate (bbl/day):Q', title='Liquid rate (bbl/day)', scale=alt.Scale(zero=False)),
        'y': alt.Y('Required head (m):Q', title='Required head (m)', scale=alt.Scale(zero=True)),
    }
    sensitivity_line = alt.Chart(sensitivity_frame).mark_line(point=True, color='#29A77D').encode(
        **axes,
        tooltip=[
            alt.Tooltip('Liquid rate (bbl/day):Q', format=',.0f'),
            alt.Tooltip('Required head (m):Q', format=',.1f'),
        ],
    )
    duty_marker = alt.Chart(requested_duty).mark_point(
        color='#F3F7F5', filled=True, size=140, stroke='#29A77D', strokeWidth=2,
    ).encode(
        **axes,
        tooltip=[
            alt.Tooltip('Series:N'),
            alt.Tooltip('Liquid rate (bbl/day):Q', format=',.0f'),
            alt.Tooltip('Required head (m):Q', format=',.1f'),
        ],
    )
    st.subheader('System required head')
    st.caption(
        f"Requested duty point: {flow:,.0f} bbl/day · {load['head_m']:.0f} m required head. "
        'This is a system required-head sensitivity chart—not a pump curve, operating-point intersection, or validated nodal analysis.'
    )
    st.altair_chart((sensitivity_line + duty_marker).properties(height=320), use_container_width=True)

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

st.download_button(
    'Download design JSON',
    json.dumps({
        'synthetic_demo': True,
        'well': asdict(well),
        'frequency_hz': frequency,
        'motor_efficiency': motor_eff,
        'motor_margin': margin,
        'duty': load,
        'candidates': candidates,
    }, indent=2),
    'esp_screening_design.json',
    'application/json',
)
