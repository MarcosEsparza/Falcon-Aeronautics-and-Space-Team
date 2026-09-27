"""Single-phase, steady-state ESP screening calculations in SI units."""
from dataclasses import dataclass, asdict
import math

G = 9.80665
BPD_TO_M3S = 0.158987294928 / 86400
PSI_TO_PA = 6894.757293168
FT_TO_M = 0.3048

@dataclass(frozen=True)
class Well:
    flow_bpd: float = 2500
    depth_ft: float = 6000
    tubing_length_ft: float = 6500
    tubing_id_in: float = 2.5
    sg: float = 0.95
    viscosity_cp: float = 1.0
    wellhead_psi: float = 150
    intake_psi: float = 900
    roughness_mm: float = 0.045

    def validate(self):
        for name, value in asdict(self).items():
            if not math.isfinite(value) or value < 0:
                raise ValueError(f'{name} must be finite and nonnegative')
        for name in ('flow_bpd', 'depth_ft', 'tubing_length_ft', 'tubing_id_in', 'sg', 'viscosity_cp'):
            if getattr(self, name) == 0:
                raise ValueError(f'{name} must be positive')
        if self.tubing_length_ft < self.depth_ft:
            raise ValueError('Tubing length must be at least the pump vertical depth')
        if self.roughness_mm / 1000 >= self.tubing_id_in * 0.0254:
            raise ValueError('Roughness must be smaller than tubing diameter')


def duty(well):
    """Energy balance from intake to wellhead; equal endpoint velocity heads."""
    well.validate()
    q = well.flow_bpd * BPD_TO_M3S
    rho = well.sg * 1000
    diameter = well.tubing_id_in * 0.0254
    velocity = q / (math.pi * diameter**2 / 4)
    re = rho * velocity * diameter / (well.viscosity_cp * 0.001)
    turbulent = (-1.8 * math.log10((well.roughness_mm / 1000 / diameter / 3.7)**1.11 + 6.9 / re))**-2
    if re <= 2300:
        factor = 64 / re
    elif re >= 4000:
        factor = turbulent
    else:
        weight = (re - 2300) / 1700
        factor = (1 - weight) * 64 / re + weight * turbulent
    friction = factor * well.tubing_length_ft * FT_TO_M / diameter * velocity**2 / (2 * G)
    pressure_head = (well.wellhead_psi - well.intake_psi) * PSI_TO_PA / (rho * G)
    raw_head = well.depth_ft * FT_TO_M + pressure_head + friction
    head = max(0, raw_head)
    return dict(head_m=head, raw_head_m=raw_head, friction_m=friction,
                pressure_head_m=pressure_head, velocity_ms=velocity, reynolds=re,
                friction_factor=factor, hydraulic_kw=rho * G * q * head / 1000)

# Fictional curves at 60 Hz, not manufacturer specifications.
PUMPS = {'SYN-1500': (1500, 8.0, 0.65), 'SYN-3000': (3000, 7.5, 0.70),
         'SYN-6000': (6000, 7.0, 0.73)}


def size_pumps(well, frequency_hz=60.0, motor_efficiency=0.9, margin=0.15):
    if not math.isfinite(frequency_hz) or not 40 <= frequency_hz <= 70:
        raise ValueError('Frequency must be 40–70 Hz')
    if not math.isfinite(motor_efficiency) or not 0 < motor_efficiency <= 1:
        raise ValueError('Motor efficiency must be in (0, 1]')
    if not math.isfinite(margin) or not 0 <= margin <= 1:
        raise ValueError('Motor margin must be in [0, 1]')
    load = duty(well)
    if load['head_m'] == 0:
        return []
    rows = []
    speed = frequency_hz / 60
    for name, (bep, base_head, peak_eff) in PUMPS.items():
        ratio = well.flow_bpd / (bep * speed)
        if not 0.7 <= ratio <= 1.2:
            continue
        stage_head = base_head * (1.25 - 0.25 * ratio**2) * speed**2
        efficiency = peak_eff - 0.35 * (ratio - 1)**2
        stages = math.ceil(load['head_m'] / stage_head)
        installed_head = stages * stage_head
        shaft = well.sg * 1000 * G * well.flow_bpd * BPD_TO_M3S * installed_head / efficiency / 1000
        rows.append(dict(pump=name, stages=stages, relative_flow=ratio,
                         efficiency=efficiency, installed_head_m=installed_head,
                         shaft_kw=shaft, electrical_kw=shaft / motor_efficiency,
                         minimum_motor_rating_kw=shaft * (1 + margin)))
    return sorted(rows, key=lambda row: row['electrical_kw'])
