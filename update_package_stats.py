"""Refresh the PyPI download statistics shown on CV/python_packages.html.

Release metadata comes from PyPI; download counts come from pepy.tech, whose
project pages embed both an all-time total and a per-day series.  The snapshot is
written to CV/package_stats.json and then rendered into the download table and
the inline per-package counts of CV/python_packages.html.

The JSON snapshot is committed, so its git history is the download record over
time.  Run with the project interpreter:

    ~/Documents/py_venv/bin/python update_package_stats.py
"""
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "CV" / "python_packages.html"
SNAPSHOT = ROOT / "CV" / "package_stats.json"

# (PyPI project name, display name, anchor id on the page).  The page holds the
# prose; this list only drives the table and the inline counts.
PACKAGES = [
    ("ModelSEEDpy-freiburgermsu", "ModelSEEDpy-freiburgermsu", "modelseedpy"),
    ("dFBApy", "dFBApy", "dfbapy"),
    ("commscores", "CommScores", "commscores"),
    ("BiGG-SABIO", "BiGG-SABIO", "bigg-sabio"),
    ("OptlangHelper", "OptlangHelper", "optlanghelper"),
    ("Codons", "Codons", "codons"),
    ("gpusw", "gpusw", "gpusw"),
    ("ChemW", "ChemW", "chemw"),
    ("ROSSpy", "ROSSpy", "rosspy"),
    ("hillfit", "hillfit", "hillfit"),
    ("PDIpy", "PDIpy", "pdipy"),
]

STATS_BEGIN = "<!-- STATS:BEGIN -->"
STATS_END = "<!-- STATS:END -->"
RECENT_WINDOW = 30  # days
UA = {"User-Agent": "andrewfreiburger.com package-stats refresh"}
MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")


def fetch(url, attempts=5):
    """GET a URL as text, backing off on rate limits and transient failures."""
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(request, timeout=40) as response:
                return response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503) or attempt == attempts - 1:
                raise
        except urllib.error.URLError:
            if attempt == attempts - 1:
                raise
        time.sleep(3 * 2 ** attempt)
    raise RuntimeError(f"exhausted attempts for {url}")


def pypi_metadata(package):
    data = json.loads(fetch(f"https://pypi.org/pypi/{package}/json"))
    info = data["info"]
    releases = {v: files for v, files in data["releases"].items() if files}
    uploads = sorted(files[0]["upload_time_iso_8601"] for files in releases.values())
    urls = info.get("project_urls") or {}
    return {
        "name": info["name"],
        "version": info["version"],
        "summary": info["summary"],
        "releases": len(releases),
        "first_release": uploads[0][:10] if uploads else None,
        "last_release": uploads[-1][:10] if uploads else None,
        "repository": urls.get("Repository") or urls.get("Homepage") or info.get("home_page"),
        "documentation": urls.get("Documentation"),
    }


def extract_object(text, opening):
    """Return the JSON object that starts at the brace at or after `opening`."""
    start = text.index("{", opening)
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:index + 1])
    raise RuntimeError("unbalanced braces in the embedded download series")


def pepy_downloads(package):
    """All-time total and recent-window total, from the pepy.tech project page.

    Both numbers come from the one source so that the columns are comparable:
    pepy counts every PyPI download event, mirrors and CI installs included.
    """
    text = fetch(f"https://pepy.tech/projects/{package.lower()}").replace('\\"', '"')
    match = re.search(r'"totalDownloads":\s*(\d+)\s*,\s*"downloads":\s*\{', text)
    if not match:
        raise RuntimeError(
            f"no totalDownloads/downloads payload on the pepy.tech page for {package} — "
            "their markup likely changed; fix the pattern rather than publishing a blank"
        )
    daily = extract_object(text, match.end() - 1)
    cutoff = (date.today() - timedelta(days=RECENT_WINDOW)).isoformat()
    recent = sum(sum(versions.values()) for day, versions in daily.items() if day >= cutoff)
    return int(match.group(1)), recent


def collect():
    records = []
    for package, display, anchor in PACKAGES:
        print(f"fetching {package} ...", flush=True)
        record = {"package": package, "display": display, "anchor": anchor}
        record.update(pypi_metadata(package))
        record["total_downloads"], record["recent_downloads"] = pepy_downloads(package)
        records.append(record)
        time.sleep(1)  # stay friendly to both services
    return records


def pretty_month(iso_date):
    parsed = datetime.strptime(iso_date, "%Y-%m-%d")
    return f"{MONTHS[parsed.month - 1]} {parsed.year}"


def render_table(records, as_of):
    """One bar per package, sized against the largest total and sorted by it."""
    ranked = sorted(records, key=lambda record: record["total_downloads"], reverse=True)
    peak = max(record["total_downloads"] for record in ranked)
    rows = "\n".join(
        f'                <tr>\n'
        f'                  <th scope="row"><a href="#{record["anchor"]}">{record["display"]}</a></th>\n'
        f'                  <td class="bar-cell"><span class="bar-track">'
        f'<span class="bar" style="width: {100 * record["total_downloads"] / peak:.1f}%"></span>'
        f'</span></td>\n'
        f'                  <td class="num">{record["total_downloads"]:,}</td>\n'
        f'                  <td class="num">{record["recent_downloads"]:,}</td>\n'
        f'                </tr>'
        for record in ranked
    )
    return f"""{STATS_BEGIN}
            <!-- Generated by update_package_stats.py — edit that script, not this block. -->
            <table class="downloads">
              <caption>All-time and recent PyPI downloads of each package.</caption>
              <thead>
                <tr>
                  <th scope="col">Package</th>
                  <th scope="col" class="bar-head">Relative to my most-downloaded package</th>
                  <th scope="col" class="num">All time</th>
                  <th scope="col" class="num">Last {RECENT_WINDOW} days</th>
                </tr>
              </thead>
              <tbody>
{rows}
              </tbody>
              <tfoot>
                <tr>
                  <th scope="row">{len(records)} packages</th>
                  <td class="bar-cell"></td>
                  <td class="num">{sum(r["total_downloads"] for r in records):,}</td>
                  <td class="num">{sum(r["recent_downloads"] for r in records):,}</td>
                </tr>
              </tfoot>
            </table>
{" " * 12}{STATS_END}"""


def substitute(html, pattern, value, description):
    html, count = re.subn(pattern, lambda match: match.group(1) + value + match.group(2), html)
    if not count:
        sys.exit(f"{PAGE} is missing the {description} placeholder")
    return html


def update_page(records, as_of):
    html = PAGE.read_text(encoding="utf-8")

    start, end = html.find(STATS_BEGIN), html.find(STATS_END)
    if start == -1 or end == -1:
        sys.exit(f"{PAGE} is missing the {STATS_BEGIN} / {STATS_END} markers")
    html = html[:start] + render_table(records, as_of) + html[end + len(STATS_END):]

    totals = {
        "packages": str(len(records)),
        "total": f"{sum(record['total_downloads'] for record in records):,}",
        "asof": pretty_month(as_of),
    }
    for stat, value in totals.items():
        html = substitute(html, rf'(<span data-stat="{stat}">)[^<]*(</span>)', value,
                          f'data-stat="{stat}"')

    for record in records:
        for field, key in [("downloads", "total_downloads"), ("version", "version"),
                           ("releases", "releases"), ("released", "last_release")]:
            raw = record[key]
            if field == "downloads":
                value = f"{raw:,}"
            elif field == "released":
                value = pretty_month(raw)
            elif field == "releases":
                value = f"{raw} release" + ("" if raw == 1 else "s")
            else:
                value = str(raw)
            html = substitute(
                html,
                rf'(<span data-{field}="{re.escape(record["package"])}">)[^<]*(</span>)',
                value, f'data-{field}="{record["package"]}"',
            )
        if f'id="{record["anchor"]}"' not in html:
            sys.exit(f'{PAGE} has no id="{record["anchor"]}" section for {record["package"]}')

    PAGE.write_text(html, encoding="utf-8")


def main():
    as_of = date.today().isoformat()
    records = collect()
    SNAPSHOT.write_text(
        json.dumps({"as_of": as_of, "recent_window_days": RECENT_WINDOW, "packages": records},
                   indent=2) + "\n",
        encoding="utf-8",
    )
    update_page(records, as_of)
    total = sum(record["total_downloads"] for record in records)
    print(f"\n{len(records)} packages · {total:,} downloads · snapshot {as_of}")
    print(f"wrote {SNAPSHOT.relative_to(ROOT)} and {PAGE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
