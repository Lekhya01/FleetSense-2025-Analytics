"""Download 2025 NYC Yellow Taxi monthly Parquet files and zone lookup."""
from pathlib import Path
import requests

BASE = "https://d37ci6vzurychx.cloudfront.net"
RAW = Path("data/raw")
MONTHS = range(1, 13)


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        print(f"Already downloaded: {destination}")
        return
    print(f"Downloading {url}")
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()
    temp = destination.with_suffix(destination.suffix + ".part")
    with temp.open("wb") as output:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                output.write(chunk)
    temp.replace(destination)
    print(f"Saved: {destination}")


def main() -> None:
    for month in MONTHS:
        name = f"yellow_tripdata_2025-{month:02d}.parquet"
        download_file(f"{BASE}/trip-data/{name}", RAW / name)
    download_file(f"{BASE}/misc/taxi_zone_lookup.csv", RAW / "taxi_zone_lookup.csv")


if __name__ == "__main__":
    main()
