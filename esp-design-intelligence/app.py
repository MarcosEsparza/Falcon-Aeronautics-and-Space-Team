"""Run with: streamlit run app.py."""
from dataclasses import asdict
import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from engineering import Well, duty, size_pumps, pump_point
from history import synthetic_history, compare

st.set_page_config(page_title='ESP Design Intelligence', page_icon='⚙', layout='wide')
st.markdown(
    '<style>' + Path(__file__).with_name('dashboard.css').read_text(encoding='utf-8') + '</style>',
    unsafe_allow_html=True,
)
st.markdown('<div class="workspace-eyebrow">ESP / ENGINEERING WORKSPACE <span>•</span> SYNTHETIC DEMO</div>',
            unsafe_allow_html=True)
st.title('ESP Design Intelligence')
st.caption('PRESCRIBED-FLOW SCREENING  /  SYSTEM SENSITIVITY  /  SYNTHETIC HISTORY')
st.warning('Fictional historical wells and pumps are not validated field designs.')


def chart_style(chart, height=280):
    """Apply one consistent presentation style without modifying chart data."""
    return (chart.properties(height=height, padding={'left': 1, 'top': 8, 'right': 6, 'bottom': 1})
            .configure_view(strokeOpacity=0)
            .configure_axis(gridColor='#23353a', domainColor='#466168',
                            tickColor='#466168', labelColor='#c3d6d4',
                            titleColor='#dbece8', labelFontSize=11, titleFontSize=12)
            .configure_legend(labelColor='#d2e2df', titleColor='#8ea9a8',
                              labelFontSize=10, orient='bottom', symbolSize=85)
            .configure(background='transparent'))

with st.sidebar:
    st.markdown('**DESIGN INPUTS**')
    st.caption('Edit conditions to recalculate the screening result.')
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
st.caption(f'CURRENT OPERATING TARGET  /  {flow:,.0f} bbl/day  /  {frequency:.0f} Hz  /  synthetic equipment')
summary = st.columns(4, gap='small')
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
    system_rows = []
    for multiplier in [.8, .9, 1., 1.1, 1.2]:
        point_well = Well(**(asdict(well) | {'flow_bpd': flow * multiplier}))
        system_rows.append({'Liquid rate (bbl/day)': point_well.flow_bpd,
                            'System required head (m)': duty(point_well)['head_m']})
    systems = pd.DataFrame(system_rows)
    requested = pd.DataFrame([{'Liquid rate (bbl/day)': flow, 'Required head (m)': load['head_m']}])
    x = alt.X('Liquid rate (bbl/day):Q', title='Liquid rate (bbl/day)', scale=alt.Scale(zero=False), axis=alt.Axis(tickCount=5))
    system_head = alt.Chart(systems).mark_line(point=True, color='#a4c0c1', strokeDash=[6,4]).encode(x=x, y=alt.Y('System required head (m):Q', title='Head (m)'),
        tooltip=[alt.Tooltip('Liquid rate (bbl/day):Q', format=',.0f'), alt.Tooltip('System required head (m):Q', format=',.1f')])
    requested_point = alt.Chart(requested).mark_point(filled=True, size=135, color='#eaf8f3', stroke='#42ddb0', strokeWidth=2).encode(x=x, y=alt.Y('Required head (m):Q'), tooltip=[alt.Tooltip('Liquid rate (bbl/day):Q', format=',.0f'), alt.Tooltip('Required head (m):Q', format=',.1f')])
    if candidates:
        selected = candidates[0]
        curve_rows = []
        bep_rows = []
        for candidate in candidates:
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
        color = alt.Color(
            'Pump model:N',
            scale=alt.Scale(
                domain=[candidate['pump'] for candidate in candidates],
                range=['#42ddb0', '#89a9ae', '#657f86'][:len(candidates)],
            ),
            legend=alt.Legend(title='Synthetic family', orient='bottom', direction='horizontal'),
        )
        pump_head = alt.Chart(curves).mark_line(strokeWidth=3).encode(x=x, y=alt.Y('Pump head (m):Q', title='Head (m)', scale=alt.Scale(zero=True)), color=color,
            tooltip=['Pump model:N', alt.Tooltip('Liquid rate (bbl/day):Q', format=',.0f'), alt.Tooltip('Pump head (m):Q', format=',.1f')])
        bep_head = alt.Chart(beps).mark_point(shape='diamond', size=110).encode(x=x, y='Pump head (m):Q', color=color, tooltip=['Pump model:N', alt.Tooltip('Liquid rate (bbl/day):Q', format=',.0f')])
        requested_rule = alt.Chart(pd.DataFrame({'Liquid rate (bbl/day)': [flow]})).mark_rule(
            color='#afcdcc', strokeDash=[4, 4]).encode(x=x)
        bep_power = alt.Chart(beps).mark_point(shape='diamond', size=110).encode(
            x=x, y='Shaft horsepower (hp):Q', color=color)
        power = alt.Chart(curves).mark_line(strokeWidth=3).encode(
            x=x,
            y=alt.Y('Shaft horsepower (hp):Q', title='Shaft horsepower (hp)',
                    scale=alt.Scale(zero=True)),
            color=color,
            tooltip=['Pump model:N', alt.Tooltip('Liquid rate (bbl/day):Q', format=',.0f'),
                     alt.Tooltip('Shaft horsepower (hp):Q', format=',.1f')],
        )
        bep_eff = alt.Chart(beps).mark_point(shape='diamond', size=110).encode(
            x=x, y='Modeled efficiency (%):Q', color=color)
        efficiency_chart = alt.Chart(curves).mark_line(strokeWidth=3).encode(
            x=x,
            y=alt.Y('Modeled efficiency (%):Q', title='Modeled efficiency (%)',
                    scale=alt.Scale(zero=False)),
            color=color,
            tooltip=['Pump model:N', alt.Tooltip('Liquid rate (bbl/day):Q', format=',.0f'),
                     alt.Tooltip('Modeled efficiency (%):Q', format='.1f')],
        )

        # A distinct screening comparison: values come from the unchanged ranked candidates.
        electrical = pd.DataFrame([
            {'Pump model': candidate['pump'],
             'Modeled electrical input (kW)': candidate['electrical_kw']}
            for candidate in candidates
        ])
        electrical_chart = alt.Chart(electrical).mark_bar(size=28, cornerRadiusEnd=5).encode(
            x=alt.X('Modeled electrical input (kW):Q',
                    title='Modeled electrical input (kW)', scale=alt.Scale(zero=True)),
            y=alt.Y('Pump model:N', title=None, sort='x'),
            color=alt.condition(
                alt.datum['Pump model'] == selected['pump'],
                alt.value('#42ddb0'), alt.value('#78969a'),
            ),
            tooltip=['Pump model:N',
                     alt.Tooltip('Modeled electrical input (kW):Q', format=',.1f')],
        )

        # Keep a full-width output row: no clipped engineering values on desktop.
        with st.container(border=True):
            introduction, context = st.columns([1.1, 3.6], gap='medium')
            with introduction:
                st.caption('01 / SCREENING RESULT')
                st.markdown(f"### {selected['pump']}")
            with context:
                st.markdown('**Prescribed-flow synthetic screening**')
                st.caption('First eligible synthetic screening result; not a validated field design.')
            values = st.columns(5, gap='small')
            values[0].metric('Estimated stages', f"{selected['stages']:,}")
            values[1].metric('Modeled efficiency', f"{selected['efficiency']:.1%}")
            values[2].metric('Shaft horsepower',
                             f"{selected['shaft_kw'] * 1.34102209:.1f} hp")
            values[3].metric('Electrical input',
                             f"{selected['electrical_kw']:.1f} kW")
            values[4].metric('Motor shaft rating',
                             f"{selected['minimum_motor_rating_kw']:.1f} kW")
            st.caption('Motor shaft rating is the minimum modeled shaft-power rating with '
                       'the selected margin; it is not electrical input.')

        upper_left, upper_right = st.columns(2, gap='medium')
        with upper_left:
            with st.container(border=True):
                st.subheader('Pump and system head')
                st.caption('Prescribed-flow system sensitivity and modeled installed head')
                st.altair_chart(
                    chart_style(pump_head + system_head + requested_point + bep_head),
                    use_container_width=True,
                )
        with upper_right:
            with st.container(border=True):
                st.subheader('Pump shaft horsepower')
                st.caption('Fixed installed stages at the current frequency')
                st.altair_chart(
                    chart_style(power + bep_power + requested_rule),
                    use_container_width=True,
                )
        lower_left, lower_right = st.columns(2, gap='medium')
        with lower_left:
            with st.container(border=True):
                st.subheader('Modeled pump efficiency')
                st.caption('Synthetic efficiency curves with BEP markers')
                st.altair_chart(
                    chart_style(efficiency_chart + bep_eff + requested_rule),
                    use_container_width=True,
                )
        with lower_right:
            with st.container(border=True):
                st.subheader('Eligible family comparison')
                st.caption('Electrical input ranked at the requested operating target')
                st.altair_chart(chart_style(electrical_chart),
                                use_container_width=True)
                if len(candidates) == 1:
                    st.caption('One synthetic family is eligible at these conditions.')

        with st.container(border=True):
            st.markdown('#### Why this synthetic option?')
            reason1, reason2, reason3 = st.columns(3, gap='medium')
            with reason1:
                st.markdown('**01 / Flow envelope**')
                st.caption('Requested flow is within the modeled 70–120% BEP screening band.')
            with reason2:
                st.markdown('**02 / Installed head**')
                st.caption('Rounded stages provide modeled head at the requested rate.')
            with reason3:
                st.markdown('**03 / Electrical input**')
                st.caption('First in the unchanged eligible-family electrical-input ranking.')
        st.caption(
            f"Curves use each pump's fixed installed stage count and {frequency:.0f} Hz "
            "frequency. Diamonds mark BEP; the dashed vertical line marks requested "
            "flow. Only the prescribed 70–120% envelope is plotted. The pump/system "
            "overlay is illustrative—not a validated well operating point or "
            "nodal-analysis result."
        )

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
    else:
        if load['head_m'] > 0:
            st.error('No fictional pump covers this rate at the selected frequency. Change the target or extend the catalog.')
        with st.container(border=True):
            st.subheader('System required head')
            st.altair_chart(chart_style(system_head + requested_point, 330), use_container_width=True)
        st.caption('Prescribed-flow sensitivity from 80–120% of the target rate at fixed boundary pressures. This is not a validated operating point or nodal-analysis prediction.')
    st.caption('Stage rounding adds head. Actual operating flow requires a pump/system-curve intersection; motor rating is shaft power plus margin, not electrical input.')

with analogs:
    st.subheader('Synthetic historical comparison')
    st.caption('02 / HISTORY • FICTIONAL EXAMPLES, NOT FIELD RECORDS')
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
    st.subheader('Model and operating assumptions')
    st.caption('03 / METHOD • PHYSICAL BOUNDARIES AND LIMITATIONS')
    st.markdown('''Steady incompressible liquid with constant density and viscosity. Pump intake and wellhead pressures use the same gauge reference. Vertical depth sets elevation head; measured tubing length sets friction. Equal endpoint velocity heads; minor losses omitted.

Darcy–Weisbach friction uses 64/Re for laminar flow and the Haaland approximation for turbulent flow, with interpolation between Reynolds numbers 2300 and 4000. Tubing roughness is fixed at 0.045 mm.

Pump head = elevation rise + pressure-head difference + friction head. Hydraulic power = density × gravity × flow × head. Fictional pump curves use affinity scaling at constant geometry.

Before field design: verify inflow/drawdown, multiphase outflow, free gas and gas separation, viscosity corrections, net positive suction head, motor cooling, temperature, cable/drive losses, casing clearance, thrust, shaft/stage limits, materials and sand handling. These are not evaluated here.''')
    st.json(load)

st.download_button('Download design JSON', json.dumps({'synthetic_demo': True, 'well': asdict(well), 'frequency_hz': frequency, 'motor_efficiency': motor_eff, 'motor_margin': margin, 'duty': load, 'candidates': candidates}, indent=2), 'esp_screening_design.json', 'application/json')
