#!/usr/bin/env python3
"""Fetch per-country baseline temperatures from CCKP and rebuild temperature-data.json
with correct absolute temperatures per country."""
import json
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).parent

# 1. Fetch per-country baselines (1995-2014 climatology)
print("[1/2] Fetching per-country baseline temperatures...")
url = ("https://cckpapi.worldbank.org/cckp/v1/"
       "cmip6-x0.25_climatology_tas_climatology_annual_1995-2014_"
       "median_historical_ensemble_all_mean/all_countries?_format=json")
req = urllib.request.Request(url, headers={"User-Agent": "CCKP-Dashboard/1.0"})
with urllib.request.urlopen(req, timeout=60) as resp:
    raw = json.loads(resp.read())

baselines_c = {}
for code, val in raw.get("data", {}).items():
    if isinstance(val, dict):
        baselines_c[code] = list(val.values())[0]  # Extract single value
    else:
        baselines_c[code] = val

print(f"  Baselines fetched: {len(baselines_c)} countries")
print(f"  Range: {min(baselines_c.values()):.1f}°C to {max(baselines_c.values()):.1f}°C")
print(f"  Mean: {sum(baselines_c.values())/len(baselines_c):.1f}°C")

# 2. Load existing temperature data and rebuild
print("[2/2] Rebuilding temperature-data.json with per-country baselines...")
with open(DATA_DIR / "temperature-data.json") as f:
    tdata = json.load(f)

# Add baselines
tdata["baselines_c"] = baselines_c

# Add per-country absolute temps in °F for quick access
# absolute_°F = (baseline_°C + anomaly_°C) * 1.8 + 32
tdata["absolute"] = {}
for code, country_data in tdata["data"].items():
    bl = baselines_c.get(code, 14.0)  # Fallback to global avg if unknown
    entry = {}
    for ssp in country_data:
        entry[ssp] = {}
        for year_str, anomaly_c in country_data[ssp].items():
            abs_f = (bl + anomaly_c) * 1.8 + 32
            entry[ssp][year_str] = round(abs_f, 1)
    if entry:
        tdata["absolute"][code] = entry

# Update summaries with absolute °F global means
tdata["summaries_abs_f"] = {}
for ssp, sdata in tdata["summaries"].items():
    tdata["summaries_abs_f"][ssp] = {"global_mean": {}}
    for year_str, anomaly_c in sdata["global_mean"].items():
        abs_f = (14.0 + anomaly_c) * 1.8 + 32  # Global mean still uses 14°C baseline
        tdata["summaries_abs_f"][ssp]["global_mean"][year_str] = round(abs_f, 1)

with open(DATA_DIR / "temperature-data.json", "w") as f:
    json.dump(tdata, f, separators=(",", ":"))

size_kb = round(Path(DATA_DIR / "temperature-data.json").stat().st_size / 1024, 1)
print(f"  Saved temperature-data.json ({size_kb} KB)")
print("  New keys: data, baselines_c, absolute, summaries_abs_f")

# Verify a few
print("\nVerification (SSP2-4.5, 2080):")
for code, name in [("COD", "Congo"), ("IND", "India"), ("CAN", "Canada"), ("SAU", "Saudi Arabia")]:
    bl = baselines_c.get(code, "?")
    anom = tdata["data"].get(code, {}).get("ssp245", {}).get("2080", "?")
    absf = tdata["absolute"].get(code, {}).get("ssp245", {}).get("2080", "?")
    print(f"  {name}: baseline={bl}°C, anomaly=+{anom}°C, absolute={absf}°F")
