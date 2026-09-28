"""Run with: streamlit run app.py."""
from dataclasses import asdict
import json

import altair as alt
import pandas as pd
import streamlit as st

from engineering import Well, duty, size_pumps, pump_point
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

st.subheader('Design snapshot')
summary = st.columns(4)
summary[0].metric('Required head', f"{load['head_m']:.0f} m")
summary[1].metric('Target rate', f'{flow:,.0f} bbl/day')
summary[2].metric('Friction head', f"{load['friction_m']:.0f} m")
summary[3].metric('Hydraulic power', f"{load['hydraulic_kw']:.1f} kW")

if load['raw_head_m'] <= 0:
    st.info('This prescribed-flow balance requires no positive pump head. Check natural-flow feasibility with an inflow and outflow model.')
if 2300 < load['reynolds'] < 4000:
    st.warning('Transitional pipe flow: friction is interpolated and uncertain.')
if viscosity > 5:
    st.warning('Viscosity exceeds the synthetic history range. Pump curves have no viscosity correction.')

sizing, analogs, assumptions = st.tabs(['Sizing', 'History', 'Method'])
with sizing:
    st.subheader('Synthetic pump selection')
    st.caption('Screened at 70–120% of speed-adjusted best efficiency point flow. Ranked by electrical power at the requested flow.')
    if candidates:
        selected = candidates[0]
        with st.container(border=True):
            st.markdown(f"### {selected['pump']}")
            first = st.columns(2)
            first[0].metric('Estimated stage count', f"{selected['stages']:,}")
            first[1].metric('Modeled efficiency', f"{selected['efficiency']:.1%}")
            second = st.columns(2)
            second[0].metric('Shaft horsepower', f"{selected['shaft_kw'] * 1.34102209:.1f} hp")
            second[1].metric('Estimated electrical input', f"{selected['electrical_kw']:.1f} kW")
            st.metric('Minimum motor shaft-power rating', f"{selected['minimum_motor_rating_kw']:.1f} kW")
            st.caption('First eligible synthetic screening result; not a validated field design.')

        compare_families = st.checkbox('Compare eligible synthetic pump families', value=False)
        chart_candidates = candidates if compare_families else [selected]
        curve_rows = []
        bep_rows = []
        for candidate in chart_candidates:
            bep = pump_point(well, candidate['pump'], frequency, candidate['stages'], flow)['bep_flow_bpd']
            low, high = 0.7 * bep, 1.2 * bep
            for index in range(31):
                curve_flow = low + (high - low) * index / 30
                point = pump_point(well, candidate['pump'], frequency, candidate['stages'], curve_flow)
                curve_rows.append({
                    'Pump model': candidate['pump'], 'Liquid rate (bbl/day)': curve_flow,
                    'Pump head (m)': point['installed_head_m'],
                    'Shaft horsepower (hp)': point['shaft_hp'],
                    'Modeled efficiency (%)': point['efficiency'] * 100,
                })
            bep_point = pump_point(well, candidate['pump'], frequency, candidate['stages'], bep)
            bep_rows.append({'Pump model': candidate['pump'], 'Liquid rate (bbl/day)': bep,
                             'Pump head (m)': bep_point['installed_head_m'],
                             'Shaft horsepower (hp)': bep_point['shaft_hp'],
                             'Modeled efficiency (%)': bep_point['efficiency'] * 100})
        curves = pd.DataFrame(curve_rows)
        beps = pd.DataFrame(bep_rows)
        system_rows = []
        for multiplier in [.8, .9, 1., 1.1, 1.2]:
            point_well = Well(**(asdict(well) | {'flow_bpd': flow * multiplier}))
            system_rows.append({'Liquid rate (bbl/day)': point_well.flow_bpd,
                                'System required head (m)': duty(point_well)['head_m']})
        systems = pd.DataFrame(system_rows)
        requested = pd.DataFrame([{'Liquid rate (bbl/day)': flow, 'Required head (m)': load['head_m']}])
        color = alt.Color('Pump model:N', legend=alt.Legend(title='Synthetic family'))
        x = alt.X('Liquid rate (bbl/day):Q', title='Liquid rate (bbl/day)', scale=alt.Scale(zero=False))
        pump_head = alt.Chart(curves).mark_line(strokeWidth=3).encode(x=x, y=alt.Y('Pump head (m):Q', title='Head (m)', scale=alt.Scale(zero=True)), color=color,
            tooltip=['Pump model:N', alt.Tooltip('Liquid rate (bbl/day):Q', format=',.0f'), alt.Tooltip('Pump head (m):Q', format=',.1f')])
        system_head = alt.Chart(systems).mark_line(point=True, color='#F3F7F5', strokeDash=[6,4]).encode(x=x, y=alt.Y('System required head (m):Q', title='Head (m)'),
            tooltip=[alt.Tooltip('Liquid rate (bbl/day):Q', format=',.0f'), alt.Tooltip('System required head (m):Q', format=',.1f')])
        requested_point = alt.Chart(requested).mark_point(filled=True, size=130, color='#F3F7F5', stroke='#29A77D', strokeWidth=2).encode(x=x, y=alt.Y('Required head (m):Q'), tooltip=[alt.Tooltip('Liquid rate (bbl/day):Q', format=',.0f'), alt.Tooltip('Required head (m):Q', format=',.1f')])
        bep_head = alt.Chart(beps).mark_point(shape='diamond', size=110).encode(x=x, y='Pump head (m):Q', color=color, tooltip=['Pump model:N', alt.Tooltip('Liquid rate (bbl/day):Q', format=',.0f')])
        st.subheader('Pump and system head')
        st.altair_chart((pump_head + system_head + requested_point + bep_head).properties(height=330), use_container_width=True)
        requested_rule = alt.Chart(pd.DataFrame({'Liquid rate (bbl/day)': [flow]})).mark_rule(color='#F3F7F5', strokeDash=[4,4]).encode(x=x)
        bep_power = alt.Chart(beps).mark_point(shape='diamond', size=110).encode(x=x, y='Shaft horsepower (hp):Q', color=color)
        power = alt.Chart(curves).mark_line(strokeWidth=3).encode(x=x, y=alt.Y('Shaft horsepower (hp):Q', title='Shaft horsepower (hp)', scale=alt.Scale(zero=True)), color=color,
            tooltip=['Pump model:N', alt.Tooltip('Liquid rate (bbl/day):Q', format=',.0f'), alt.Tooltip('Shaft horsepower (hp):Q', format=',.1f')])
        st.subheader('Pump shaft horsepower')
        st.altair_chart((power + bep_power + requested_rule).properties(height=260), use_container_width=True)
        bep_eff = alt.Chart(beps).mark_point(shape='diamond', size=110).encode(x=x, y='Modeled efficiency (%):Q', color=color)
        efficiency_chart = alt.Chart(curves).mark_line(strokeWidth=3).encode(x=x, y=alt.Y('Modeled efficiency (%):Q', title='Modeled efficiency (%)', scale=alt.Scale(zero=False)), color=color,
            tooltip=['Pump model:N', alt.Tooltip('Liquid rate (bbl/day):Q', format=',.0f'), alt.Tooltip('Modeled efficiency (%):Q', format='.1f')])
        st.subheader('Modeled pump efficiency')
        st.altair_chart((efficiency_chart + bep_eff + requested_rule).properties(height=260), use_container_width=True)
        st.caption(f"Curves use each pump's fixed installed stage count and {frequency:.0f} Hz frequency. Diamonds mark BEP; the dashed vertical line marks requested flow. Only the prescribed 70–120% envelope is plotted. The pump/system overlay is illustrative—not a validated well operating point or nodal-analysis result.")

        with st.expander('View all eligible synthetic pumps'):
            pump_table = pd.DataFrame(candidates)[['pump', 'stages', 'relative_flow', 'efficiency', 'installed_head_m', 'shaft_kw', 'electrical_kw', 'minimum_motor_rating_kw']].rename(columns={
                'pump': 'Pump model', 'stages': 'Stages', 'relative_flow': 'Requested flow / BEP',
                'efficiency': 'Modeled efficiency', 'installed_head_m': 'Installed head (m)',
                'shaft_kw': 'Shaft power (kW)', 'electrical_kw': 'Modeled electrical input (kW)',
                'minimum_motor_rating_kw': 'Minimum motor shaft-power rating (kW)'})
            st.dataframe(pump_table, hide_index=True, use_container_width=True, column_config={
                'Stages': st.column_config.NumberColumn(format='%d'), 'Requested flow / BEP': st.column_config.NumberColumn(format='%.2f'),
                'Modeled efficiency': st.column_config.NumberColumn(format='percent'), 'Installed head (m)': st.column_config.NumberColumn(format='%.0f'),
                'Shaft power (kW)': st.column_config.NumberColumn(format='%.1f'), 'Modeled electrical input (kW)': st.column_config.NumberColumn(format='%.1f'),
                'Minimum motor shaft-power rating (kW)': st.column_config.NumberColumn(format='%.1f')})
    elif load['head_m'] > 0:
        st.error('No fictional pump covers this rate at the selected frequency. Change the target or extend the catalog.')
    st.caption('Stage rounding adds head. Actual operating flow requires a pump/system-curve intersection; motor rating is shaft power plus margin, not electrical input.')

with analogs:
    st.subheader('Synthetic historical comparison')
    history = synthetic_history()
    k = st.slider('Historical neighbors', 3, 20, 8)
    neighbors, votes, outside = compare(well, history, k)
    st.write(f'Nearest-neighbor suggestion at historical 60 Hz: **{votes.index[0]}** ({votes.iloc[0]:.0%} of neighbor labels).')
    st.caption('Vote share describes neighboring synthetic labels only; it is not confidence, reliability, or probability of success. Current-frequency engineering eligibility takes precedence.')
    if outside:
        st.warning('Coverage warning — outside synthetic feature coverage: ' + ', '.join(outside))
    shown = neighbors[['well_id', 'pump', 'distance', 'flow_bpd', 'depth_ft', 'sg', 'viscosity_cp', 'intake_psi', 'tubing_id_in', 'head_m']].copy()
    shown['proximity'] = 1 / (1 + shown['distance'])
    proximity = shown[['well_id', 'pump', 'proximity']].rename(columns={'well_id': 'Synthetic well', 'pump': 'Pump model', 'proximity': 'Descriptive proximity'})
    st.bar_chart(proximity, x='Synthetic well', y='Descriptive proximity', color='Pump model', horizontal=True)
    st.caption('Descriptive proximity = 1 / (1 + standardized distance); it is not confidence or success probability.')
    shown = shown.rename(columns={'well_id': 'Synthetic well', 'pump': 'Pump model', 'distance': 'Standardized distance', 'flow_bpd': 'Liquid rate (bbl/day)', 'depth_ft': 'Depth (ft)', 'sg': 'Specific gravity', 'viscosity_cp': 'Viscosity (cP)', 'intake_psi': 'Intake pressure (psig)', 'tubing_id_in': 'Tubing ID (in)', 'head_m': 'Required head (m)'})
    st.dataframe(shown.drop(columns='proximity'), hide_index=True, use_container_width=True)
    st.download_button('Download synthetic history CSV', history.to_csv(index=False), 'synthetic_history.csv', 'text/csv')

with assumptions:
    st.markdown('''Steady incompressible liquid with constant density and viscosity. Pump intake and wellhead pressures use the same gauge reference. Vertical depth sets elevation head; measured tubing length sets friction. Equal endpoint velocity heads; minor losses omitted.

Darcy–Weisbach friction uses 64/Re for laminar flow and the Haaland approximation for turbulent flow, with interpolation between Reynolds numbers 2300 and 4000. Tubing roughness is fixed at 0.045 mm.

Pump head = elevation rise + pressure-head difference + friction head. Hydraulic power = density × gravity × flow × head. Fictional pump curves use affinity scaling at constant geometry.

Before field design: verify inflow/drawdown, multiphase outflow, free gas and gas separation, viscosity corrections, net positive suction head, motor cooling, temperature, cable/drive losses, casing clearance, thrust, shaft/stage limits, materials and sand handling. These are not evaluated here.''')
    st.json(load)

st.download_button('Download design JSON', json.dumps({'synthetic_demo': True, 'well': asdict(well), 'frequency_hz': frequency, 'motor_efficiency': motor_eff, 'motor_margin': margin, 'duty': load, 'candidates': candidates}, indent=2), 'esp_screening_design.json', 'application/json')
