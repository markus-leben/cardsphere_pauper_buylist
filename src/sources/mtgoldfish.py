"""Fetch format-staple rankings from MTGGoldfish."""
import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from src.models import Card

MTGGOLDFISH_BASE = "https://www.mtggoldfish.com"
STAPLES_URL = MTGGOLDFISH_BASE + "/format-staples/{fmt}/full/{card_type}"
FULL_META_URL = MTGGOLDFISH_BASE + "/metagame/{fmt}/full"

FORMATS = ["pauper"]
CARD_TYPES = ["spells", "creatures", "lands"]

CACHE_PATH = Path(".cache/mtggoldfish_staples.json")
CACHE_MAX_AGE = 24 * 3600
CRAWL_DELAY = 2

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; cardsphere-buylist/1.0)"}


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def _fetch_staples_page(fmt: str, card_type: str, session: requests.Session) -> dict[str, int]:
    """Return {card_name: rank} for one format/card_type page."""
    url = STAPLES_URL.format(fmt=fmt, card_type=card_type)
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", class_="table-staples")
    if not table:
        return {}
    results: dict[str, int] = {}
    for row in table.find_all("tr")[1:]:   # skip header row
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        try:
            rank = int(cells[0].get_text(strip=True))
        except ValueError:
            continue
        name = cells[1].get_text(strip=True)
        if name:
            results[name] = rank
    return results


def _fetch_metagame(fmt:str, session: requests.Session) -> dict[str: int]:
    meta = {}
    url = FULL_META_URL.format(fmt=fmt)
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    deck_links = soup.select('a[href^="/archetype/"][href$="paper"]')
    for deck in deck_links:
        deck_url = deck['href']
        deck_resp = session.get(MTGGOLDFISH_BASE + deck_url, timeout=15)
        deck_resp.raise_for_status()
        deck_soup = BeautifulSoup(deck_resp.text, "html.parser")
        deck_cards = deck_soup.find_all("span", class_="price-card-invisible-label")
        for card in deck_cards:
            meta[card.text] = 51

    return meta


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _load_cache() -> dict[str, dict[str, int]]:
    if CACHE_PATH.exists():
        age = time.time() - CACHE_PATH.stat().st_mtime
        if age < CACHE_MAX_AGE:
            print(f"Loading MTGGoldfish staples from cache ({age / 3600:.1f}h old)...")
            return json.loads(CACHE_PATH.read_text())
        print(f"MTGGoldfish staples cache is {age / 3600:.1f}h old, re-fetching...")
    return {}


def _save_cache(data: dict[str, dict[str, int]]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(data))


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def fetch_all_staples(force: bool = False, staples_only: bool = False) -> dict[str, dict[str, int]]:
    """
    Return {format: {card_name: rank}} for all formats and card types.

    The three card-type pages (spells, creatures, lands) are merged per format;
    each card should appear on exactly one of them.
    Results are cached for 24 hours.
    """
    if not force:
        cached = _load_cache()
        if cached:
            return cached

    session = requests.Session()
    session.headers.update(_HEADERS)
    data: dict[str, dict[str, int]] = {}

    for fmt in FORMATS:
        combined: dict[str, int] = {}
        if not staples_only:
            broad_meta = _fetch_metagame(fmt, session)
            combined.update(broad_meta)


        for card_type in CARD_TYPES:
            print(f"  Fetching MTGGoldfish {fmt}/{card_type}...")
            page_ranks = _fetch_staples_page(fmt, card_type, session)
            combined.update(page_ranks)
            time.sleep(CRAWL_DELAY)
        data[fmt] = combined
        print(f"  {fmt}: {len(combined)} staples indexed")

    _save_cache(data)
    return data


def annotate_ratings(cards: list[Card], force: bool = False, staples_only: bool = False) -> None:
    """Annotate card.mtgoldfish_ratings in-place for every card found in the staples tables."""
    staples = fetch_all_staples(force=force, staples_only=staples_only)
    pauper = staples.get("pauper", {})

    for card in cards:
        r = card.mtggoldfish_ratings
        r.pauper = pauper.get(card.name)
