"""
Pirelli F1 Preview Data Downloader
Downloads Pirelli Preview pages and extracts downforce ratings (1-5 scale)
"""

import os
import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class PirelliTrackData:
    """Data extracted from Pirelli Preview"""

    track_name: str
    year: int
    downforce_level: Optional[int] = None
    brake_severity: Optional[int] = None
    url: str = ""
    raw_text: str = ""


# 2024 F1 Calendar with Pirelli URL slugs
RACE_MAPPING_2024 = {
    "bahrain": "bahrain",
    "saudi-arabia": "saudi-arabian",
    "japan": "japanese",
    "china": "chinese",
    "miami": "miami",
    "monaco": "monaco",
    "canada": "canadian",
    "spain": "spanish",
    "austria": "austrian",
    "uk": "british",
    "hungary": "hungarian",
    "belgium": "belgian",
    "netherlands": "dutch",
    "italy": "italian",
    "azerbaijan": "azerbaijan",
    "singapore": "singapore",
    "usa": "united-states",
    "mexico": "mexican",
    "brazil": "brazilian",
    "qatar": "qatari",
    "abu-dhabi": "abu-dhabi",
    "las-vegas": "las-vegas",
}

# Track names for 2025 (similar to 2024)
RACE_MAPPING_2025 = {
    "australia": "australian",
    "china": "chinese",
    "japan": "japanese",
    "bahrain": "bahrain",
    "saudi-arabia": "saudi-arabian",
    "miami": "miami",
    "monaco": "monaco",
    "canada": "canadian",
    "spain": "spanish",
    "austria": "austrian",
    "uk": "british",
    "hungary": "hungarian",
    "belgium": "belgian",
    "netherlands": "dutch",
    "italy": "italian",
    "azerbaijan": "azerbaijan",
    "singapore": "singapore",
    "usa": "united-states",
    "mexico": "mexican",
    "brazil": "brazilian",
    "qatar": "qatari",
    "abu-dhabi": "abu-dhabi",
    "las-vegas": "las-vegas",
}


def get_race_names_2024():
    """Return the list of 2024 F1 Grand Prix races."""
    return list(RACE_MAPPING_2024.keys())


def get_race_names_2025():
    """Return the list of 2025 F1 Grand Prix races."""
    return list(RACE_MAPPING_2025.keys())


def generate_url_candidates(year: int, race_slug: str):
    """Generate possible URL patterns for a given race."""
    base = "https://press.pirelli.com/"
    # Try multiple URL patterns - Pirelli has used various formats over years
    patterns = [
        # Current/recent formats
        f"{year}-{race_slug}-grand-prix--preview/",
        f"{year}-{race_slug}-grand-prix---preview/",
        f"{year}-{race_slug}-grand-prix-preview/",
        f"{year}-{race_slug}-gp---preview/",
        f"{year}-{race_slug}-gp--preview/",
        f"{year}-{race_slug}-gp-preview/",
        # 2023-2024 formats
        f"{year}-{race_slug}-grand-prix-preview/",
        f"2024-{race_slug}-gp-preview/",
        f"2023-{race_slug}-gp-preview/",
        # Without year prefix (some older pages)
        f"{race_slug}-grand-prix-preview/",
        f"{race_slug}-gp-preview/",
    ]
    return [urljoin(base, pattern) for pattern in patterns]


def find_valid_url(year: int, race_slug: str):
    """Find the correct URL pattern that returns a 200 status code."""
    for url in generate_url_candidates(year, race_slug):
        try:
            response = requests.get(
                url,
                timeout=15,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            if response.status_code == 200:
                print(f"  Found valid URL: {url}")
                return url
        except requests.exceptions.RequestException as e:
            continue
    return None


def extract_downforce_data(url: str, track_key: str, year: int) -> PirelliTrackData:
    """Extract downforce and brake severity ratings from Pirelli Preview page."""
    try:
        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        soup = BeautifulSoup(response.text, "html.parser")

        # Get all text content for analysis
        text_content = soup.get_text(separator=" ", strip=True)

        data = PirelliTrackData(
            track_name=track_key,
            year=year,
            url=url,
            raw_text=text_content[:2000],  # Store first 2000 chars for reference
        )

        # Look for downforce level patterns
        # Pirelli uses format like "DOWNFORCE LEVEL 3" or "Level: 3" or "Downforce: 3/5"
        downforce_patterns = [
            r"downforce\s*level\s*(\d)",
            r"downforce:\s*(\d)",
            r"downforce\s*(\d)\s*/\s*5",
            r"level\s*(\d)\s*downforce",
            r"df\s*level\s*(\d)",
        ]

        for pattern in downforce_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                data.downforce_level = int(match.group(1))
                break

        # Look for brake severity patterns
        brake_patterns = [
            r"brake\s*severity\s*(\d)",
            r"braking\s*severity\s*(\d)",
            r"brake\s*level\s*(\d)",
            r"brake\s*(\d)\s*/\s*5",
        ]

        for pattern in brake_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                data.brake_severity = int(match.group(1))
                break

        return data

    except Exception as e:
        print(f"  Error extracting data from {url}: {e}")
        return PirelliTrackData(track_name=track_key, year=year, url=url)


def download_pirelli_data(year: int, output_file: str):
    """Download Pirelli Preview data for a given year and extract downforce ratings."""
    if year == 2024:
        race_mapping = RACE_MAPPING_2024
    elif year == 2025:
        race_mapping = RACE_MAPPING_2025
    else:
        print(f"Year {year} not supported")
        return []

    results = []

    print(f"\n{'=' * 60}")
    print(f"Downloading Pirelli {year} F1 Preview Data")
    print(f"{'=' * 60}")

    for track_key, race_slug in race_mapping.items():
        print(f"\nProcessing {year} {track_key.title()} Grand Prix...")

        valid_url = find_valid_url(year, race_slug)
        if valid_url:
            data = extract_downforce_data(valid_url, track_key, year)
            results.append(data)

            if data.downforce_level:
                print(f"  [OK] Downforce Level: {data.downforce_level}/5")
            else:
                print(f"  [--] Downforce level not found")

            if data.brake_severity:
                print(f"  [OK] Brake Severity: {data.brake_severity}/5")

            time.sleep(1)  # Be respectful with requests
        else:
            print(f"  [--] No valid URL found for {track_key}")
            # Still add placeholder
            results.append(PirelliTrackData(track_name=track_key, year=year))

    # Save results to JSON
    output_data = []
    for r in results:
        output_data.append(
            {
                "track": r.track_name,
                "year": r.year,
                "downforce_level": r.downforce_level,
                "brake_severity": r.brake_severity,
                "url": r.url,
            }
        )

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\n[OK] Data saved to {output_file}")
    return results


def main():
    """Main function to download Pirelli data for multiple years."""
    # Download 2024 data
    results_2024 = download_pirelli_data(2024, "pirelli_2024_data.json")

    time.sleep(2)

    # Download 2025 data
    results_2025 = download_pirelli_data(2025, "pirelli_2025_data.json")

    # Print summary
    print(f"\n{'=' * 60}")
    print("SUMMARY - Pirelli Downforce Levels (1-5)")
    print(f"{'=' * 60}")

    print("\n2024 Season:")
    for r in results_2024:
        df = r.downforce_level if r.downforce_level else "?"
        print(f"  {r.track_name.title()}: {df}/5")

    print("\n2025 Season:")
    for r in results_2025:
        df = r.downforce_level if r.downforce_level else "?"
        print(f"  {r.track_name.title()}: {df}/5")


if __name__ == "__main__":
    main()
