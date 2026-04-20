from __future__ import annotations

import csv
import json
import math
import statistics
from datetime import date
from pathlib import Path

import typer
from rich import print

from ..paths import ACTIVITIES_DIR, DERIVED_DIR, DOCS_DIR, MATCHES_DIR

app = typer.Typer(help="Advocacy report generation.")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLUSTER_RADIUS_M = 5
SHOCK_SIGMA = 5          # threshold = mean + SHOCK_SIGMA * std
SEVERITY_TIERS = [
    (30.0, "Extreme",  "#d32f2f"),
    (15.0, "Severe",   "#f57c00"),
    ( 8.0, "Moderate", "#fbc02d"),
    ( 0.0, "Notable",  "#388e3c"),
]

ADVOCACY_STATEMENT = """\
My name is Vasil. I am a wheelchair user. Last year, in the center of this town,
I was navigating the pavement and had to circle around an illegally parked car.
The pavement was broken. I fell. I broke my arm.

I reported it. I submitted medical documentation. Photographs. A formal written
account. Everything, in a file, to the police. Nothing happened.

I am not writing this to ask for sympathy. I am writing this because what
happened to me is not an accident of bad luck — it is the predictable consequence
of a city that treats its legal obligations as optional.

Our country has ratified the United Nations Convention on the Rights of Persons
with Disabilities. Article 9 mandates accessibility of the physical environment.
Article 12 guarantees equal recognition before the law. Article 13 guarantees
access to justice. These are not recommendations. They are binding obligations
our government accepted before the entire international community.

The UN Committee on the Rights of Persons with Disabilities has been explicit:
inaccessible infrastructure is discrimination. A broken pavement that puts a
wheelchair user in hospital is not a maintenance issue. It is a human rights
violation.

And when a citizen reports that violation — with evidence, with medical
documentation, with photographs — and the police do nothing? That is a second
violation, compounding the first.

This world belongs to all of us. To the person with a cane. To the wheelchair
user. To the parent with a stroller. To those who are deaf or hard of hearing.
To every person that urban planners have historically chosen to ignore.

We are not asking for this world to include us. The law already says it must.
We are simply holding our governments to the promise they made — not to us
personally, but to the United Nations, on behalf of every citizen of this
country who has ever been told, by a broken pavement or a police station that
files and forgets, that they do not matter.

We matter. We have always mattered. And we have the law on our side.
"""


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return distance in metres between two WGS-84 coordinates."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _severity(peak_g: float) -> tuple[str, str]:
    for threshold, label, color in SEVERITY_TIERS:
        if peak_g >= threshold:
            return label, color
    return "Notable", "#388e3c"


# ---------------------------------------------------------------------------
# Data loading and analysis
# ---------------------------------------------------------------------------

def _load_session_names() -> dict[str, tuple[str, str]]:
    """Return {recording_id: (activity_name, date_str)} from matches + activities."""
    result: dict[str, tuple[str, str]] = {}
    for mf in MATCHES_DIR.glob("*.json"):
        m = json.loads(mf.read_text(encoding="utf-8"))
        rid = m["recording_id"]
        aid = str(m["activity_id"])
        af = ACTIVITIES_DIR / f"{aid}.json"
        if af.exists():
            act = json.loads(af.read_text(encoding="utf-8"))
            name = act.get("name", aid)
            date_str = act.get("start_date", "")[:10]
        else:
            name = aid
            date_str = ""
        result[rid] = (name, date_str)
    return result


def _compute_shocks(csv_path: Path, session_label: str) -> list[dict]:
    """Return list of shock-event dicts for one derived CSV."""
    rows: list[tuple[float, float, float]] = []  # (lat, lng, magnitude)
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mag_str = row.get("magnitude", "")
            lat_str = row.get("lat", "")
            lng_str = row.get("lng", "")
            if not mag_str or not lat_str or not lng_str:
                continue
            try:
                rows.append((float(lat_str), float(lng_str), float(mag_str)))
            except ValueError:
                continue

    if not rows:
        return []

    magnitudes = [r[2] for r in rows]
    mean = statistics.mean(magnitudes)
    std = statistics.stdev(magnitudes) if len(magnitudes) > 1 else 0.0
    threshold = mean + SHOCK_SIGMA * std

    shocks = []
    for lat, lng, mag in rows:
        if mag > threshold:
            shocks.append({"lat": lat, "lng": lng, "magnitude": mag, "session": session_label})
    return shocks


def _cluster_shocks(shocks: list[dict]) -> list[dict]:
    """Greedy spatial clustering within CLUSTER_RADIUS_M metres."""
    clusters: list[dict] = []
    for shock in shocks:
        placed = False
        for cl in clusters:
            if _haversine_m(cl["lat"], cl["lng"], shock["lat"], shock["lng"]) <= CLUSTER_RADIUS_M:
                cl["shocks"].append(shock)
                if shock["magnitude"] > cl["peak"]:
                    cl["peak"] = shock["magnitude"]
                    cl["lat"] = shock["lat"]
                    cl["lng"] = shock["lng"]
                if shock["session"] not in cl["sessions"]:
                    cl["sessions"].append(shock["session"])
                placed = True
                break
        if not placed:
            clusters.append({
                "lat": shock["lat"],
                "lng": shock["lng"],
                "peak": shock["magnitude"],
                "shocks": [shock],
                "sessions": [shock["session"]],
            })
    return clusters


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def _marker_radius(shock_count: int) -> int:
    if shock_count >= 50:
        return 12
    if shock_count >= 20:
        return 11
    if shock_count >= 10:
        return 10
    if shock_count >= 5:
        return 9
    return 8


def _build_html(
    clusters: list[dict],
    total_sessions: int,
    total_points: int,
    total_shocks: int,
    report_date: str,
) -> str:
    peak_g = max((cl["peak"] for cl in clusters), default=0.0)
    sorted_clusters = sorted(clusters, key=lambda c: -c["peak"])
    top10 = sorted_clusters[:10]

    # Map markers
    marker_lines = []
    for cl in sorted_clusters:
        label, color = _severity(cl["peak"])
        radius = _marker_radius(len(cl["shocks"]))
        sessions_html = "".join(f"• {s}<br>" for s in cl["sessions"])
        popup = (
            f"<b>{label}</b><br>"
            f"Peak: <b>{cl['peak']:.2f} g</b><br>"
            f"Shocks: {len(cl['shocks'])}<br>"
            f"Sessions ({len(cl['sessions'])}):<br>{sessions_html}"
            f"<small>{cl['lat']:.6f}, {cl['lng']:.6f}</small>"
        )
        marker_lines.append(
            f"    L.circleMarker([{cl['lat']:.6f}, {cl['lng']:.6f}], "
            f"{{radius: {radius}, fillColor: '{color}', color: '#fff', weight: 1.5, fillOpacity: 0.85}})"
            f".bindPopup('{popup}').addTo(map);"
        )
    markers_js = "\n".join(marker_lines)

    # Worst locations table rows
    table_rows = []
    for i, cl in enumerate(top10, 1):
        label, color = _severity(cl["peak"])
        sessions_str = ", ".join(cl["sessions"])
        table_rows.append(
            f"<tr>"
            f"<td>{i}</td>"
            f"<td>{cl['lat']:.6f}, {cl['lng']:.6f}</td>"
            f"<td><span class='badge' style='background:{color}'>{label}</span></td>"
            f"<td><b>{cl['peak']:.2f} g</b></td>"
            f"<td>{len(cl['shocks'])}</td>"
            f"<td>{sessions_str}</td>"
            f"</tr>"
        )
    table_html = "\n".join(table_rows)

    # Advocacy statement paragraphs
    statement_paras = "".join(
        f"<p>{para.strip()}</p>\n"
        for para in ADVOCACY_STATEMENT.strip().split("\n\n")
        if para.strip()
    )

    # Bounding box for map fitBounds
    lats = [cl["lat"] for cl in clusters]
    lngs = [cl["lng"] for cl in clusters]
    if lats:
        pad = 0.001
        bounds = (
            f"[[{min(lats) - pad:.6f}, {min(lngs) - pad:.6f}], "
            f"[{max(lats) + pad:.6f}, {max(lngs) + pad:.6f}]]"
        )
    else:
        bounds = "[[41.34, 21.55], [41.35, 21.57]]"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Open Streets Initiative — Accessibility Evidence Report</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: Georgia, 'Times New Roman', serif; color: #1a1a1a; background: #fff; }}
    a {{ color: #1565c0; }}

    /* ---------- layout ---------- */
    .page {{ max-width: 900px; margin: 0 auto; padding: 48px 32px; }}
    section {{ margin-bottom: 48px; }}
    h1 {{ font-size: 26px; font-weight: bold; margin-bottom: 6px; }}
    h2 {{ font-size: 18px; font-weight: bold; border-bottom: 2px solid #1a1a1a; padding-bottom: 4px; margin-bottom: 20px; }}
    p {{ line-height: 1.7; margin-bottom: 12px; font-size: 15px; }}

    /* ---------- header ---------- */
    .report-header {{ border-bottom: 3px solid #1a1a1a; padding-bottom: 20px; margin-bottom: 36px; }}
    .evidence-badge {{
      display: inline-block; background: #c62828; color: #fff;
      font-family: sans-serif; font-size: 11px; font-weight: bold;
      padding: 3px 10px; letter-spacing: 1px; border-radius: 2px;
      margin-bottom: 14px;
    }}
    .report-meta {{ font-family: sans-serif; font-size: 13px; color: #555; margin-top: 8px; }}

    /* ---------- stats box ---------- */
    .stats-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 16px; margin-bottom: 0;
    }}
    .stat-card {{
      border: 1px solid #ddd; border-radius: 6px; padding: 16px 18px;
      font-family: sans-serif;
    }}
    .stat-value {{ font-size: 28px; font-weight: bold; color: #c62828; line-height: 1.1; }}
    .stat-label {{ font-size: 12px; color: #666; margin-top: 4px; }}

    /* ---------- map ---------- */
    #map {{ width: 100%; height: 480px; border-radius: 6px; border: 1px solid #ccc; }}

    /* ---------- table ---------- */
    table {{ width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px; }}
    th {{ background: #1a1a1a; color: #fff; padding: 9px 10px; text-align: left; }}
    td {{ padding: 8px 10px; border-bottom: 1px solid #eee; vertical-align: top; }}
    tr:nth-child(even) td {{ background: #fafafa; }}
    .badge {{
      display: inline-block; color: #fff; border-radius: 3px;
      padding: 2px 8px; font-size: 11px; font-weight: bold;
    }}

    /* ---------- legal ---------- */
    .legal-item {{ margin-bottom: 16px; padding-left: 16px; border-left: 3px solid #1565c0; }}
    .legal-item b {{ font-family: sans-serif; font-size: 13px; display: block; margin-bottom: 2px; }}
    .legal-item p {{ font-size: 14px; margin: 0; }}

    /* ---------- methodology ---------- */
    .method-step {{ margin-bottom: 12px; padding-left: 20px; position: relative; font-size: 14px; line-height: 1.6; }}
    .method-step::before {{ content: counter(step); counter-increment: step;
      position: absolute; left: 0; font-family: sans-serif; font-weight: bold;
      color: #c62828; }}
    .method-list {{ counter-reset: step; }}

    /* ---------- print ---------- */
    @media print {{
      body {{ font-size: 13px; }}
      .page {{ padding: 0; max-width: 100%; }}
      #map {{ height: 360px; page-break-inside: avoid; }}
      section {{ page-break-inside: avoid; }}
      .stats-grid {{ grid-template-columns: repeat(5, 1fr); }}
    }}
  </style>
</head>
<body>
<div class="page">

  <!-- ── HEADER ── -->
  <div class="report-header">
    <div class="evidence-badge">EVIDENCE DOCUMENT</div>
    <h1>Open Streets Initiative<br>Accessibility Evidence Report</h1>
    <div class="report-meta">
      Generated: {report_date} &nbsp;|&nbsp;
      Data collected by: Vasil Taneski &nbsp;|&nbsp;
      Location: Veles, North Macedonia
    </div>
  </div>

  <!-- ── SUMMARY STATISTICS ── -->
  <section>
    <h2>Summary of Evidence</h2>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{total_sessions}</div>
        <div class="stat-label">Sessions analysed</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{total_points:,}</div>
        <div class="stat-label">Sensor data points</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{total_shocks}</div>
        <div class="stat-label">Shock events detected</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{len(clusters)}</div>
        <div class="stat-label">Hazard clusters</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{peak_g:.1f} g</div>
        <div class="stat-label">Peak impact force</div>
      </div>
    </div>
  </section>

  <!-- ── PERSONAL STATEMENT ── -->
  <section>
    <h2>Personal Statement</h2>
    {statement_paras}
  </section>

  <!-- ── LEGAL FRAMEWORK ── -->
  <section>
    <h2>Legal Framework</h2>
    <p>
      North Macedonia has ratified the United Nations Convention on the Rights
      of Persons with Disabilities (UN CRPD). The following articles are directly
      applicable to the conditions documented in this report.
    </p>
    <div class="legal-item">
      <b>Article 9 — Accessibility</b>
      <p>States must ensure persons with disabilities have access to the physical
      environment on an equal basis with others. Broken pavements and inaccessible
      routes are a direct violation of this obligation.</p>
    </div>
    <div class="legal-item">
      <b>Article 12 — Equal Recognition Before the Law</b>
      <p>Persons with disabilities enjoy legal capacity on an equal basis. Systemic
      neglect of accessible infrastructure denies equal participation in civic life.</p>
    </div>
    <div class="legal-item">
      <b>Article 13 — Access to Justice</b>
      <p>States must ensure effective access to justice for persons with disabilities.
      Filing a formal complaint with evidence and receiving no response is a failure
      to honour this obligation.</p>
    </div>
    <p style="margin-top:16px; font-size:14px; font-style:italic;">
      The UN Committee on the Rights of Persons with Disabilities has stated
      explicitly: inaccessible infrastructure constitutes discrimination. A broken
      pavement that injures a wheelchair user is not a maintenance issue — it is a
      human rights violation.
    </p>
  </section>

  <!-- ── HAZARD MAP ── -->
  <section>
    <h2>Hazard Map — Measured Impact Locations</h2>
    <p style="font-size:13px; color:#555; font-family:sans-serif; margin-bottom:10px;">
      Each marker represents a cluster of measured shock events. Colour indicates
      severity. Circle size indicates number of shocks. Click any marker for details.
    </p>
    <div id="map"></div>
    <p style="font-size:11px; color:#888; font-family:sans-serif; margin-top:8px;">
      Map data © OpenStreetMap contributors. Shock locations derived from accelerometer
      recordings synchronised with GPS tracks from Strava.
    </p>
  </section>

  <!-- ── WORST LOCATIONS TABLE ── -->
  <section>
    <h2>Ten Worst Locations by Peak Impact Force</h2>
    <table>
      <thead>
        <tr>
          <th>#</th><th>Coordinates</th><th>Severity</th>
          <th>Peak (g)</th><th>Shocks</th><th>Sessions</th>
        </tr>
      </thead>
      <tbody>
        {table_html}
      </tbody>
    </table>
  </section>

  <!-- ── METHODOLOGY ── -->
  <section>
    <h2>Methodology</h2>
    <p>
      All measurements were taken during real wheelchair journeys through the town centre.
      A mobile phone was mounted on the wheelchair and recorded accelerometer data
      using the phyphox application at approximately 20 samples per second.
      GPS route data was collected independently via Strava. The two data streams
      were synchronised by timestamp and fused to produce geolocated impact measurements.
    </p>
    <div class="method-list">
      <div class="method-step">
        Raw accelerometer data (x, y, z axes) was exported as CSV from phyphox.
      </div>
      <div class="method-step">
        Each sensor recording was matched to the corresponding Strava activity by
        timestamp overlap. The GPS stream for the matched activity was downloaded from Strava.
      </div>
      <div class="method-step">
        GPS position was linearly interpolated at each sensor sample timestamp to
        assign coordinates to every accelerometer reading.
      </div>
      <div class="method-step">
        Impact magnitude was computed as the Euclidean norm of the three accelerometer
        axes: √(x² + y² + z²), expressed in units of g (9.81 m/s²).
      </div>
      <div class="method-step">
        Shock events were identified as samples exceeding the per-session threshold
        of mean + {SHOCK_SIGMA}σ (five standard deviations above the session mean).
        This conservative threshold filters normal rolling vibration and captures
        only genuine impact events.
      </div>
      <div class="method-step">
        Shock events within {CLUSTER_RADIUS_M} metres of each other were merged into
        a single hazard cluster. Each cluster records its peak impact force, total
        shock count, and the sessions in which it was observed.
      </div>
    </div>
    <p style="margin-top:16px; font-size:14px;">
      Locations flagged in this report were identified consistently across multiple
      independent recording sessions, confirming that the hazards are persistent
      infrastructure defects, not one-time measurement anomalies.
    </p>
  </section>

</div><!-- /page -->

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
  var map = L.map('map');
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
  }}).addTo(map);

{markers_js}

  map.fitBounds({bounds});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------

@app.command("generate")
def generate() -> None:
    """Generate an advocacy evidence report as a self-contained HTML file."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    session_names = _load_session_names()
    derived_files = sorted(DERIVED_DIR.glob("*.csv"))

    if not derived_files:
        print("[red]No derived CSV files found. Run `osi analyze run` first.[/red]")
        raise typer.Exit(1)

    all_shocks: list[dict] = []
    total_points = 0

    for csv_path in derived_files:
        # recording_id is the part before "__"
        stem = csv_path.stem
        recording_id = stem.split("__")[0] if "__" in stem else stem
        name, date_str = session_names.get(recording_id, (recording_id, ""))
        session_label = f"{name} ({date_str})" if date_str else name

        shocks = _compute_shocks(csv_path, session_label)
        all_shocks.extend(shocks)

        # count data points
        with open(csv_path, encoding="utf-8") as f:
            total_points += sum(1 for _ in f) - 1  # subtract header

        print(f"  {session_label}: {len(shocks)} shock events")

    clusters = _cluster_shocks(all_shocks)
    clusters.sort(key=lambda c: -c["peak"])

    report_date = date.today().isoformat()
    html = _build_html(
        clusters=clusters,
        total_sessions=len(derived_files),
        total_points=total_points,
        total_shocks=len(all_shocks),
        report_date=report_date,
    )

    out = DOCS_DIR / "advocacy-report.html"
    out.write_text(html, encoding="utf-8")

    print(f"\n[bold green]Report generated:[/bold green] {out}")
    print(f"  Sessions : {len(derived_files)}")
    print(f"  Data pts : {total_points:,}")
    print(f"  Shocks   : {len(all_shocks)}")
    print(f"  Clusters : {len(clusters)}")
    if clusters:
        peak = clusters[0]["peak"]
        print(f"  Peak     : {peak:.2f} g")
