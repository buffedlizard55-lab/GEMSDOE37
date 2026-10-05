"""Exact H0 superlevel persistence for 2-D scalar rasters.

A persistence bar records the birth and merge (death) thresholds of a connected
component in the superlevel filtration {x : f(x) >= t}. The implementation uses
the elder rule and 4- or 8-neighbour pixel connectivity. It intentionally does not
claim that a persistent component is a geological fault; geology and cross-scale
matching are separate validation questions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

import numpy as np

try:  # Numba accelerates the per-pixel union-find on full rasters.
    from numba import njit
except ImportError:  # Small tests can still use the Python implementation.
    njit = None


@dataclass(frozen=True, slots=True)
class PersistenceBar:
    """A finite H0 bar, with the birth component's peak pixel as representative."""

    row: int
    col: int
    birth: float
    death: float
    persistence: float


@dataclass(frozen=True, slots=True)
class ScaleObservation:
    """One per-scale persistence observation in a tracked component."""

    sigma_m: float
    bar: PersistenceBar


@dataclass(frozen=True, slots=True)
class PersistenceTrack:
    """A heuristic spatial match of H0 bars across adjacent smoothing scales.

    ``min_persistence`` is the least threshold-lifetime in this track. The
    diagram-stability margin is ``min_persistence - 2 * epsilon`` for a stated
    sup-norm perturbation bound epsilon. ``sigma_span_m`` is an observed
    smoothing-scale range; matching bars across scales is not itself covered by
    the one-parameter persistence stability theorem.
    """

    observations: tuple[ScaleObservation, ...]
    min_persistence: float
    epsilon: float
    stability_margin: float
    sigma_span_m: float

    @property
    def scale_count(self) -> int:
        return len(self.observations)

    @property
    def peak(self) -> tuple[int, int]:
        middle = self.observations[len(self.observations) // 2]
        return middle.bar.row, middle.bar.col

    @property
    def sigma_values_m(self) -> tuple[float, ...]:
        return tuple(item.sigma_m for item in self.observations)


def _find_root(parent: np.ndarray, vertex: int) -> int:
    """Path-compressing find used by the uncompiled small-array fallback."""
    root = vertex
    while parent[root] != root:
        root = int(parent[root])
    while parent[vertex] != vertex:
        nxt = int(parent[vertex])
        parent[vertex] = root
        vertex = nxt
    return root


def _h0_python(
    order: np.ndarray,
    flat: np.ndarray,
    shape: tuple[int, int],
    connectivity: int,
    min_persistence: float,
    max_bars: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, bool]:
    height, width = shape
    n = flat.size
    parent = np.full(n, -1, dtype=np.int32)
    birth = np.empty(n, dtype=np.float32)
    peak = np.empty(n, dtype=np.int32)
    out_peak = np.empty(max_bars, dtype=np.int32)
    out_birth = np.empty(max_bars, dtype=np.float32)
    out_death = np.empty(max_bars, dtype=np.float32)
    count = 0
    overflow = False

    for raw_vertex in order:
        vertex = int(raw_vertex)
        row, col = divmod(vertex, width)
        parent[vertex] = vertex
        birth[vertex] = flat[vertex]
        peak[vertex] = vertex
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                if connectivity == 4 and dr != 0 and dc != 0:
                    continue
                nr, nc = row + dr, col + dc
                if nr < 0 or nr >= height or nc < 0 or nc >= width:
                    continue
                neighbor = nr * width + nc
                if parent[neighbor] < 0:
                    continue
                root_a = _find_root(parent, vertex)
                root_b = _find_root(parent, neighbor)
                if root_a == root_b:
                    continue
                # Higher birth survives; a smaller flat index breaks exact ties.
                if birth[root_a] > birth[root_b] or (
                    birth[root_a] == birth[root_b] and peak[root_a] < peak[root_b]
                ):
                    elder, younger = root_a, root_b
                else:
                    elder, younger = root_b, root_a
                level = float(flat[vertex])
                lifetime = float(birth[younger]) - level
                if lifetime >= min_persistence:
                    if count < max_bars:
                        out_peak[count] = peak[younger]
                        out_birth[count] = birth[younger]
                        out_death[count] = level
                        count += 1
                    else:
                        overflow = True
                parent[younger] = elder

    return out_peak, out_birth, out_death, count, overflow


if njit is not None:

    @njit(cache=True)
    def _h0_numba(
        order: np.ndarray,
        flat: np.ndarray,
        height: int,
        width: int,
        connectivity: int,
        min_persistence: float,
        max_bars: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, bool]:
        n = flat.size
        parent = np.full(n, -1, dtype=np.int32)
        birth = np.empty(n, dtype=np.float32)
        peak = np.empty(n, dtype=np.int32)
        out_peak = np.empty(max_bars, dtype=np.int32)
        out_birth = np.empty(max_bars, dtype=np.float32)
        out_death = np.empty(max_bars, dtype=np.float32)
        count = 0
        overflow = False

        for pos in range(order.size):
            vertex = int(order[pos])
            row = vertex // width
            col = vertex - row * width
            parent[vertex] = vertex
            birth[vertex] = flat[vertex]
            peak[vertex] = vertex

            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    if dr == 0 and dc == 0:
                        continue
                    if connectivity == 4 and dr != 0 and dc != 0:
                        continue
                    nr = row + dr
                    nc = col + dc
                    if nr < 0 or nr >= height or nc < 0 or nc >= width:
                        continue
                    neighbor = nr * width + nc
                    if parent[neighbor] < 0:
                        continue

                    root_a = vertex
                    while parent[root_a] != root_a:
                        parent[root_a] = parent[parent[root_a]]
                        root_a = parent[root_a]
                    root_b = neighbor
                    while parent[root_b] != root_b:
                        parent[root_b] = parent[parent[root_b]]
                        root_b = parent[root_b]
                    if root_a == root_b:
                        continue

                    if birth[root_a] > birth[root_b] or (
                        birth[root_a] == birth[root_b] and peak[root_a] < peak[root_b]
                    ):
                        elder = root_a
                        younger = root_b
                    else:
                        elder = root_b
                        younger = root_a
                    level = float(flat[vertex])
                    lifetime = float(birth[younger]) - level
                    if lifetime >= min_persistence:
                        if count < max_bars:
                            out_peak[count] = peak[younger]
                            out_birth[count] = birth[younger]
                            out_death[count] = level
                            count += 1
                        else:
                            overflow = True
                    parent[younger] = elder

        return out_peak, out_birth, out_death, count, overflow

else:
    _h0_numba = None


def h0_superlevel_persistence(
    field: np.ndarray,
    valid_mask: np.ndarray | None = None,
    *,
    connectivity: int = 8,
    min_persistence: float = 0.0,
    max_bars: int = 1_000_000,
    require_numba: bool = False,
) -> list[PersistenceBar]:
    """Compute finite H0 bars of a masked 2-D superlevel filtration.

    Bars whose persistence is below ``min_persistence`` are omitted. Essential
    components (those that survive to the bottom of the filtration) are omitted:
    they describe the connected valid domain, not a finite-lived candidate.

    The stability theorem for a tame scalar function states that the bottleneck
    distance between persistence diagrams is bounded by the L-infinity distance
    between the functions. Consequently, a bar with lifetime greater than
    ``2 * epsilon`` cannot be matched to the diagonal under perturbations bounded
    by epsilon. The function does not estimate epsilon; the caller must report
    and justify any bound used.
    """
    values = np.asarray(field, dtype=np.float32)
    if values.ndim != 2:
        raise ValueError(f"field must be 2-D, got shape {values.shape}")
    if connectivity not in (4, 8):
        raise ValueError("connectivity must be 4 or 8")
    if min_persistence < 0 or not np.isfinite(min_persistence):
        raise ValueError("min_persistence must be finite and non-negative")
    if max_bars < 1:
        raise ValueError("max_bars must be positive")
    mask = np.isfinite(values)
    if valid_mask is not None:
        supplied = np.asarray(valid_mask, dtype=bool)
        if supplied.shape != values.shape:
            raise ValueError("valid_mask shape must match field")
        mask &= supplied
    if not np.any(mask):
        return []

    flat = np.ascontiguousarray(values).ravel()
    valid_indices = np.flatnonzero(mask.ravel()).astype(np.int32, copy=False)
    order = valid_indices[np.argsort(-flat[valid_indices], kind="stable")]
    order = np.ascontiguousarray(order, dtype=np.int32)

    if _h0_numba is not None:
        peaks, births, deaths, count, overflow = _h0_numba(
            order,
            flat,
            int(values.shape[0]),
            int(values.shape[1]),
            int(connectivity),
            float(min_persistence),
            int(max_bars),
        )
    else:
        if require_numba:
            raise RuntimeError("Numba is required for full-raster persistence; install the project dependencies")
        peaks, births, deaths, count, overflow = _h0_python(
            order,
            flat,
            values.shape,
            connectivity,
            float(min_persistence),
            int(max_bars),
        )
    if overflow:
        raise RuntimeError(
            f"More than {max_bars:,} bars passed the persistence cutoff; raise the cutoff or max_bars"
        )

    width = values.shape[1]
    bars = [
        PersistenceBar(
            row=int(peaks[i]) // width,
            col=int(peaks[i]) % width,
            birth=float(births[i]),
            death=float(deaths[i]),
            persistence=float(births[i] - deaths[i]),
        )
        for i in range(count)
    ]
    bars.sort(key=lambda bar: (-bar.persistence, -bar.birth, bar.row, bar.col))
    return bars


def match_adjacent_scale_bars(
    bars_by_sigma: Mapping[float, Iterable[PersistenceBar]],
    *,
    max_peak_distance_px: float = 2.0,
    epsilon: float = 0.0,
) -> list[PersistenceTrack]:
    """Greedily track nearby bars at adjacent Gaussian smoothing scales.

    This deterministic spatial matching is an operational cross-scale
    persistence measure, not a proof of multiparameter persistence. At each
    scale, bars are assigned at most once; matches are one-to-one and only
    between consecutive entries in the ordered sigma list.
    """
    if max_peak_distance_px < 0:
        raise ValueError("max_peak_distance_px must be non-negative")
    if epsilon < 0 or not np.isfinite(epsilon):
        raise ValueError("epsilon must be finite and non-negative")
    scales = sorted((float(sigma), list(bars)) for sigma, bars in bars_by_sigma.items())
    if any(not np.isfinite(sigma) or sigma < 0 for sigma, _ in scales):
        raise ValueError("smoothing scales must be finite and non-negative")
    if not scales:
        return []

    active_tracks: list[list[ScaleObservation]] = []
    last_scale_index: list[int] = []
    for scale_index, (sigma_m, bars) in enumerate(scales):
        used_tracks: set[int] = set()
        ordered_bars = sorted(bars, key=lambda b: (-b.persistence, -b.birth, b.row, b.col))
        # Index only tracks that ended at the immediately preceding scale. This
        # keeps matching near-linear in the number of bars rather than O(n^2).
        previous_grid: dict[tuple[int, int], int] = {}
        if scale_index > 0:
            for track_index, track in enumerate(active_tracks):
                if last_scale_index[track_index] == scale_index - 1:
                    previous = track[-1].bar
                    previous_grid[(previous.row, previous.col)] = track_index
        radius = int(np.ceil(max_peak_distance_px))
        for bar in ordered_bars:
            eligible: list[tuple[float, float, int]] = []
            for row in range(bar.row - radius, bar.row + radius + 1):
                for col in range(bar.col - radius, bar.col + radius + 1):
                    track_index = previous_grid.get((row, col))
                    if track_index is None or track_index in used_tracks:
                        continue
                    previous = active_tracks[track_index][-1].bar
                    distance = float(np.hypot(bar.row - row, bar.col - col))
                    if distance <= max_peak_distance_px:
                        eligible.append((distance, -previous.persistence, track_index))
            if eligible:
                _, _, best = min(eligible)
                active_tracks[best].append(ScaleObservation(sigma_m, bar))
                last_scale_index[best] = scale_index
                used_tracks.add(best)
            else:
                active_tracks.append([ScaleObservation(sigma_m, bar)])
                last_scale_index.append(scale_index)
                used_tracks.add(len(active_tracks) - 1)

    output: list[PersistenceTrack] = []
    for observations in active_tracks:
        persistences = [item.bar.persistence for item in observations]
        minimum = min(persistences)
        sigmas = [item.sigma_m for item in observations]
        output.append(
            PersistenceTrack(
                observations=tuple(observations),
                min_persistence=minimum,
                epsilon=float(epsilon),
                stability_margin=minimum - 2.0 * float(epsilon),
                sigma_span_m=max(sigmas) - min(sigmas),
            )
        )
    output.sort(
        key=lambda track: (
            -track.stability_margin,
            -track.scale_count,
            -track.sigma_span_m,
            track.peak,
        )
    )
    return output
