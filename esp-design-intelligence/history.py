"""Reproducible fictional history and transparent k-nearest-neighbor assistance."""
import numpy as np
import pandas as pd
from engineering import Well, duty, size_pumps

FEATURES = ['flow_bpd', 'depth_ft', 'sg', 'viscosity_cp', 'intake_psi', 'tubing_id_in']


def synthetic_history(n=240, seed=42):
    if n < 5:
        raise ValueError('At least five records are required')
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        depth = rng.uniform(3500, 8500)
        well = Well(flow_bpd=rng.uniform(1100, 6800), depth_ft=depth,
                    tubing_length_ft=depth * 1.08, sg=rng.uniform(.82, 1.08),
                    viscosity_cp=rng.uniform(.7, 5), intake_psi=rng.uniform(500, 1500),
                    tubing_id_in=float(rng.choice([2.5, 3, 3.5])))
        candidates = size_pumps(well)
        rows.append(dict(well_id=f'SYN-{i+1:04}', **well.__dict__,
                         head_m=duty(well)['head_m'],
                         pump=candidates[0]['pump'] if candidates else 'No eligible pump',
                         synthetic=True))
    return pd.DataFrame(rows)


def compare(well, history, k=8):
    """Equal-weight standardized Euclidean distance, using historical scales only."""
    well.validate()
    if not 1 <= k <= len(history):
        raise ValueError('Neighbor count must be between 1 and history size')
    x = history[FEATURES].astype(float)
    if not np.isfinite(x.to_numpy()).all() or len(x) < 2:
        raise ValueError('History requires at least two finite feature rows')
    scale = x.std(ddof=0).replace(0, 1)
    query = pd.Series({f: getattr(well, f) for f in FEATURES})
    distance = np.sqrt((((x - query) / scale)**2).sum(axis=1))
    nearest = history.assign(distance=distance).sort_values('distance', kind='stable').head(k)
    outside = [f for f in FEATURES if query[f] < x[f].min() or query[f] > x[f].max()]
    votes = nearest['pump'].value_counts(normalize=True)
    return nearest, votes, outside
