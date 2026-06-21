#!/usr/bin/env python3
"""
Topographic map generator.

Fetches real elevation data from OpenTopoData (SRTM/ASTER) and renders a
topo map with hillshading, filled contours, and contour labels.

Usage:
  python topo_map.py "Yosemite Valley, California"
  python topo_map.py "Mount Rainier, WA" --radius 15 --contour-interval 100
  python topo_map.py --lat 36.4552 --lon -118.5967 --radius 8 --output kings_canyon.png
  python topo_map.py "Grand Canyon" --radius 20 --grid-size 40 --dataset srtm30m
"""

import argparse
import sys
import time
import re
from pathlib import Path

import numpy as np
import requests
from scipy.ndimage import zoom as ndimage_zoom
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import LightSource, LinearSegmentedColormap
from geopy.geocoders import Nominatim

# Warm brown/tan colormap: dark valley floors -> tawny slopes -> cream peaks -> white snow
_BROWN_TAN_CMAP = LinearSegmentedColormap.from_list(
    "brown_tan",
    [
        "#3B1F0A",  # deep dark brown (lowest)
        "#6B3D1A",  # chestnut brown
        "#9C6535",  # medium warm brown
        "#C49050",  # golden brown
        "#D4AE76",  # warm tan
        "#E6CFA0",  # pale tan / straw
        "#F3E8CC",  # cream
        "#FFFFFF",  # white (peaks / snow)
    ],
    N=256,
)


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

def geocode_location(location_str: str) -> tuple[float, float]:
    geolocator = Nominatim(user_agent="topo_mapper_v1")
    result = geolocator.geocode(location_str, timeout=10)
    if not result:
        raise ValueError(f"Could not find location: {location_str!r}")
    return result.latitude, result.longitude


# ---------------------------------------------------------------------------
# Elevation data
# ---------------------------------------------------------------------------

def _fetch_batch(locations: list[tuple[float, float]], dataset: str) -> list[float]:
    """GET a single batch of ≤100 points from OpenTopoData. Returns elevations list."""
    locations_str = "|".join(f"{lat},{lon}" for lat, lon in locations)
    url = f"https://api.opentopodata.org/v1/{dataset}?locations={locations_str}"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "OK":
        raise RuntimeError(f"OpenTopoData error: {data.get('status')}, {data.get('error', '')}")
    return [r["elevation"] if r["elevation"] is not None else 0.0 for r in data["results"]]


def fetch_elevation_grid(
    lat_center: float,
    lon_center: float,
    radius_km: float,
    grid_size: int,
    dataset: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (lat_grid, lon_grid, elevation_grid), all shape (grid_size, grid_size)."""
    lat_rad = radius_km / 111.0
    lon_rad = radius_km / (111.0 * np.cos(np.radians(lat_center)))

    lats = np.linspace(lat_center - lat_rad, lat_center + lat_rad, grid_size)
    lons = np.linspace(lon_center - lon_rad, lon_center + lon_rad, grid_size)
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")

    points = list(zip(lat_grid.flatten(), lon_grid.flatten()))
    total = len(points)
    batch_size = 100
    num_batches = (total + batch_size - 1) // batch_size

    elevations = []
    for i, start in enumerate(range(0, total, batch_size)):
        batch = points[start : start + batch_size]
        print(f"  Fetching batch {i + 1}/{num_batches} ({len(batch)} points)...", flush=True)
        elevations.extend(_fetch_batch(batch, dataset))
        if start + batch_size < total:
            time.sleep(1.1)  # public API: 1 request/second

    elevation_grid = np.array(elevations).reshape(grid_size, grid_size)
    return lat_grid, lon_grid, elevation_grid


# ---------------------------------------------------------------------------
# Map rendering
# ---------------------------------------------------------------------------

def _smart_contour_interval(elev_min: float, elev_max: float) -> int:
    """Pick a contour interval that gives ~8–15 lines across the range."""
    span = elev_max - elev_min
    if span <= 0:
        return 10
    raw = span / 10
    for step in [5, 10, 20, 25, 50, 100, 200, 250, 500, 1000]:
        if raw <= step:
            return step
    return 1000


def render_topo_map(
    lat_center: float,
    lon_center: float,
    lat_grid: np.ndarray,
    lon_grid: np.ndarray,
    elevation_grid: np.ndarray,
    location_name: str,
    contour_interval: int,
    output_path: Path,
    dpi: int = 150,
) -> None:
    elev_min = float(elevation_grid.min())
    elev_max = float(elevation_grid.max())

    if contour_interval <= 0:
        contour_interval = _smart_contour_interval(elev_min, elev_max)
        print(f"Auto contour interval: {contour_interval}m")

    # Upsample to ~300 pts/side with bicubic interpolation for smooth contours & shading
    raw_size = elevation_grid.shape[0]
    upsample = max(1, 300 // raw_size)
    if upsample > 1:
        elev_fine = ndimage_zoom(elevation_grid, upsample, order=3)
        lat_fine = np.linspace(lat_grid.min(), lat_grid.max(), elev_fine.shape[0])
        lon_fine = np.linspace(lon_grid.min(), lon_grid.max(), elev_fine.shape[1])
        lat_fine_grid, lon_fine_grid = np.meshgrid(lat_fine, lon_fine, indexing="ij")
    else:
        elev_fine, lat_fine_grid, lon_fine_grid = elevation_grid, lat_grid, lon_grid

    fig, ax = plt.subplots(figsize=(13, 10))

    # --- Hillshaded terrain background ---
    ls = LightSource(azdeg=315, altdeg=45)
    terrain_rgb = ls.shade(
        elev_fine,
        cmap=_BROWN_TAN_CMAP,
        blend_mode="soft",
        vert_exag=2,
        vmin=elev_min,
        vmax=elev_max,
    )
    ax.imshow(
        terrain_rgb,
        extent=[lon_fine_grid.min(), lon_fine_grid.max(), lat_fine_grid.min(), lat_fine_grid.max()],
        origin="lower",
        aspect="auto",
        interpolation="bilinear",
    )

    # --- Contour lines (drawn on the fine grid for smooth curves) ---
    first_level = (int(elev_min) // contour_interval) * contour_interval
    levels = np.arange(first_level, elev_max + contour_interval, contour_interval)

    ax.contour(
        lon_fine_grid, lat_fine_grid, elev_fine,
        levels=levels,
        colors="#5C3317",
        linewidths=0.5,
        alpha=0.7,
    )

    # Bold index contours (every 5th), with elevation labels
    major_levels = [l for l in levels if l % (contour_interval * 5) == 0]
    if major_levels:
        cs_major = ax.contour(
            lon_fine_grid, lat_fine_grid, elev_fine,
            levels=major_levels,
            colors="#3B1F0A",
            linewidths=1.5,
            alpha=0.9,
        )
        ax.clabel(
            cs_major,
            levels=major_levels,
            fmt="%dm",
            fontsize=7,
            inline=True,
            inline_spacing=4,
            colors="#3B1F0A",
        )

    # --- Colorbar ---
    sm = plt.cm.ScalarMappable(
        cmap=_BROWN_TAN_CMAP,
        norm=plt.Normalize(vmin=elev_min, vmax=elev_max),
    )
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, shrink=0.65, pad=0.02)
    cbar.set_label("Elevation (m)", fontsize=10)
    cbar.ax.tick_params(labelsize=8)

    # --- Grid & axes ---
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{abs(v):.3f}°{'W' if v < 0 else 'E'}")
    )
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{abs(v):.3f}°{'S' if v < 0 else 'N'}")
    )
    ax.tick_params(axis="both", labelsize=8)
    ax.grid(True, alpha=0.25, color="white", linewidth=0.5, linestyle="--")

    # --- Title ---
    hem_ns = "N" if lat_center >= 0 else "S"
    hem_ew = "E" if lon_center >= 0 else "W"
    ax.set_title(
        f"Topographic Map  —  {location_name}\n"
        f"{abs(lat_center):.4f}°{hem_ns}  {abs(lon_center):.4f}°{hem_ew}  |  "
        f"Elevation {elev_min:.0f}–{elev_max:.0f} m  |  "
        f"Contour interval {contour_interval} m",
        fontsize=11,
        pad=10,
    )

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate topographic maps for any location using real elevation data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "location",
        nargs="?",
        help="Place name (e.g. 'Yosemite Valley'). Omit if using --lat/--lon.",
    )
    p.add_argument("--lat", type=float, help="Center latitude (decimal degrees)")
    p.add_argument("--lon", type=float, help="Center longitude (decimal degrees)")
    p.add_argument(
        "--radius", type=float, default=10.0,
        help="Half-width of the map area in km (default: 10)",
    )
    p.add_argument(
        "--contour-interval", type=int, default=0,
        help="Contour line spacing in meters (default: auto)",
    )
    p.add_argument(
        "--grid-size", type=int, default=30,
        help="Grid resolution per side (default: 30; higher = more detail, more API calls)",
    )
    p.add_argument(
        "--dataset",
        choices=["srtm90m", "srtm30m", "aster30m"],
        default="srtm90m",
        help="Elevation dataset (default: srtm90m; srtm30m for finer detail)",
    )
    p.add_argument(
        "--output", "-o",
        help="Output PNG path (default: <location>.png in current directory)",
    )
    p.add_argument(
        "--dpi", type=int, default=150,
        help="Output image resolution (default: 150)",
    )
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # --- Resolve center ---
    if args.lat is not None and args.lon is not None:
        lat, lon = args.lat, args.lon
        location_name = f"{abs(lat):.4f}°{'N' if lat >= 0 else 'S'}, {abs(lon):.4f}°{'E' if lon >= 0 else 'W'}"
    elif args.location:
        print(f"Geocoding '{args.location}'...")
        try:
            lat, lon = geocode_location(args.location)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        location_name = args.location
        print(f"  Found: {lat:.5f}, {lon:.5f}")
    else:
        parser.error("Provide a location name or both --lat and --lon.")

    # --- Output path ---
    if args.output:
        output_path = Path(args.output)
    else:
        safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", args.location or location_name)[:60]
        output_path = Path(safe + ".png")

    # --- Fetch elevation ---
    total_pts = args.grid_size ** 2
    num_batches = (total_pts + 99) // 100
    print(
        f"Fetching {total_pts} elevation points "
        f"({num_batches} API call{'s' if num_batches != 1 else ''}, "
        f"~{num_batches + 1}s)..."
    )
    try:
        lat_grid, lon_grid, elevation_grid = fetch_elevation_grid(
            lat, lon, args.radius, args.grid_size, args.dataset
        )
    except (requests.RequestException, RuntimeError) as exc:
        print(f"Error fetching elevation data: {exc}", file=sys.stderr)
        sys.exit(1)

    elev_min = elevation_grid.min()
    elev_max = elevation_grid.max()
    print(f"Elevation range: {elev_min:.0f} - {elev_max:.0f} m")

    # --- Render ---
    print("Rendering map...")
    render_topo_map(
        lat, lon,
        lat_grid, lon_grid, elevation_grid,
        location_name,
        args.contour_interval,
        output_path,
        dpi=args.dpi,
    )
    print(f"Saved: {output_path.resolve()}")


if __name__ == "__main__":
    main()
