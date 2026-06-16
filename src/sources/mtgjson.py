"""Download, cache, and parse MTGJson data into Card objects."""
import gzip
import json
import time
from pathlib import Path
from typing import Iterator, Optional

import requests

from src.models import Card, Identifiers, PriceList, PricePoints

MTGJSON_BASE = "https://mtgjson.com/api/v5"
CACHE_DIR = Path(".cache/mtgjson")
CACHE_MAX_AGE = 24 * 3600  # seconds


# ---------------------------------------------------------------------------
# Download / cache helpers
# ---------------------------------------------------------------------------

def _fetch_json(filename: str, force: bool = False) -> dict:
    """Download a gzipped MTGJson file, cache the decompressed JSON locally."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / filename.removesuffix(".gz")

    if cache_path.exists() and not force:
        age = time.time() - cache_path.stat().st_mtime
        if age < CACHE_MAX_AGE:
            print(f"Loading {cache_path} from cache ({age/3600:.1f}h old)...")
            with cache_path.open() as f:
                return json.load(f)
        print(f"Cache is {age/3600:.1f}h old (>{CACHE_MAX_AGE//3600}h), re-downloading...")

    url = f"{MTGJSON_BASE}/{filename}"
    print(f"Downloading {url} ...")
    resp = requests.get(url, timeout=120, stream=True)
    resp.raise_for_status()

    raw = gzip.decompress(resp.content)
    data = json.loads(raw)

    with cache_path.open("w") as f:
        json.dump(data, f)
    print(f"Cached to {cache_path}")

    return data


# ---------------------------------------------------------------------------
# AllIdentifiers parsing  (keyed by UUID → CardSet)
# ---------------------------------------------------------------------------

def _parse_identifiers(raw: dict) -> Identifiers:
    return Identifiers(
        scryfall_id=raw.get("scryfallId"),
        scryfall_oracle_id=raw.get("scryfallOracleId"),
        tcgplayer_product_id=raw.get("tcgplayerProductId"),
        tcgplayer_etched_product_id=raw.get("tcgplayerEtchedProductId"),
        cardsphere_id=raw.get("cardsphereId"),
        cardsphere_foil_id=raw.get("cardsphereFoilId"),
        cardsphere_etched_id=raw.get("cardsphereEtchedId"),
        card_kingdom_id=raw.get("cardKingdomId"),
        card_kingdom_foil_id=raw.get("cardKingdomFoilId"),
        card_kingdom_etched_id=raw.get("cardKingdomEtchedId"),
        mtgo_id=raw.get("mtgoId"),
        mtgo_foil_id=raw.get("mtgoFoilId"),
        mtg_arena_id=raw.get("mtgArenaId"),
        multiverse_id=raw.get("multiverseId"),
    )


def _card_from_raw(raw: dict) -> Card:
    """Convert a raw MTGJson CardSet dict into a Card."""
    return Card(
        uuid=raw["uuid"],
        name=raw["name"],
        set_code=raw["setCode"],
        number=raw["number"],
        mana_value=raw.get("manaValue", 0),
        colors=raw.get("colors", []),
        color_identity=raw.get("colorIdentity", []),
        finishes=raw.get("finishes", []),
        availability=raw.get("availability", []),
        border_color=raw.get("borderColor", ""),
        frame_version=raw.get("frameVersion", ""),
        type_line=raw.get("type", ""),
        types=raw.get("types", []),
        supertypes=raw.get("supertypes", []),
        subtypes=raw.get("subtypes", []),
        legalities=raw.get("legalities", {}),
        identifiers=_parse_identifiers(raw.get("identifiers", {})),
        layout=raw.get("layout"),
        mana_cost=raw.get("manaCost"),
        face_mana_value=raw.get("faceManaValue"),
        text=raw.get("text"),
        power=raw.get("power"),
        toughness=raw.get("toughness"),
        loyalty=raw.get("loyalty"),
        defense=raw.get("defense"),
        side=raw.get("side"),
        face_name=raw.get("faceName"),
        artist=raw.get("artist"),
        flavor_text=raw.get("flavorText"),
        watermark=raw.get("watermark"),
        security_stamp=raw.get("securityStamp"),
        original_text=raw.get("originalText"),
        original_type=raw.get("originalType"),
        keywords=raw.get("keywords", []),
        frame_effects=raw.get("frameEffects", []),
        promo_types=raw.get("promoTypes", []),
        printings=raw.get("printings", []),
        variations=raw.get("variations", []),
        other_face_ids=raw.get("otherFaceIds", []),
        booster_types=raw.get("boosterTypes", []),
        is_reserved=raw.get("isReserved", False),
        is_promo=raw.get("isPromo", False),
        is_reprint=raw.get("isReprint", False),
        is_full_art=raw.get("isFullArt", False),
        is_funny=raw.get("isFunny", False),
        is_textless=raw.get("isTextless", False),
        is_alternative=raw.get("isAlternative", False),
        is_online_only=raw.get("isOnlineOnly", False),
        is_rebalanced=raw.get("isRebalanced", False),
        is_oversized=raw.get("isOversized", False),
        is_game_changer=raw.get("isGameChanger", False),
        edhrec_rank=raw.get("edhrecRank", 9999999),
        edhrec_saltiness=raw.get("edhrecSaltiness"),
    )


EXAMPLE_CARD_PATH = CACHE_DIR / "example_card.json"


def iter_cards(force: bool = False) -> Iterator[Card]:
    """Yield every CardSet Card from AllIdentifiers.json (keyed by UUID)."""
    raw = _fetch_json("AllIdentifiers.json.gz", force=force)
    first = True
    for card_raw in raw["data"].values():
        if first:
            EXAMPLE_CARD_PATH.write_text(json.dumps(card_raw, indent=2))
            first = False
        yield _card_from_raw(card_raw)


def load_cards(force: bool = False) -> dict[str, Card]:
    """Return all cards as a dict keyed by UUID."""
    return {card.uuid: card for card in iter_cards(force=force)}


def _latest(date_prices: Optional[dict]) -> Optional[float]:
    if not date_prices:
        return None
    return date_prices[max(date_prices)]


def _parse_price_points(raw: Optional[dict]) -> Optional[PricePoints]:
    if not raw:
        return None
    return PricePoints(
        normal=_latest(raw.get("normal")),
        foil=_latest(raw.get("foil")),
        etched=_latest(raw.get("etched")),
    )


def _parse_price_list(raw: dict) -> PriceList:
    return PriceList(
        currency=raw.get("currency", "USD"),
        retail=_parse_price_points(raw.get("retail")),
        buylist=_parse_price_points(raw.get("buylist")),
    )


def annotate_prices(cards_by_uuid: dict[str, Card], force: bool = False) -> None:
    """Fetch AllPricesToday.json and populate card.prices (paper vendors only) for each UUID."""
    print("Loading MTGJson AllPricesToday...")
    data = _fetch_json("AllPricesToday.json.gz", force=force)
    prices_by_uuid: dict = data["data"]
    matched = 0
    for uuid, card in cards_by_uuid.items():
        entry = prices_by_uuid.get(uuid)
        if not entry:
            continue
        paper = entry.get("paper", {})
        if paper:
            card.prices = {vendor: _parse_price_list(pl) for vendor, pl in paper.items()}
            matched += 1
    print(f"Annotated prices for {matched}/{len(cards_by_uuid)} cards.")


# ---------------------------------------------------------------------------
# Hello-world demo
# ---------------------------------------------------------------------------

def demo_single_card() -> None:
    """Download AllIdentifiers and pretty-print the first card returned."""
    print("=== MTGJson demo: first card from AllIdentifiers ===\n")
    card = next(iter_cards())
    print(f"Name           : {card.name}")
    print(f"Set            : {card.set_code} #{card.number}")
    print(f"UUID           : {card.uuid}")
    print(f"Mana cost      : {card.mana_cost or '—'}")
    print(f"Mana value     : {card.mana_value}")
    print(f"Type           : {card.type_line}")
    print(f"Colors         : {card.colors or ['Colorless']}")
    print(f"Color identity : {card.color_identity or ['Colorless']}")
    print(f"Finishes       : {card.finishes}")
    print(f"Availability   : {card.availability}")
    print(f"Keywords       : {card.keywords}")
    print(f"Text           :\n  {(card.text or '').replace(chr(10), chr(10) + '  ')}")
    if card.power:
        print(f"P/T            : {card.power}/{card.toughness}")
    if card.loyalty:
        print(f"Loyalty        : {card.loyalty}")
    print(f"EDHREC rank    : {card.edhrec_rank or 'unranked'}")
    print(f"Is reserved    : {card.is_reserved}")
    print(f"Is promo       : {card.is_promo}")
    print(f"Printings      : {', '.join(card.printings[:10])}{'...' if len(card.printings) > 10 else ''}")
    print(f"\nIdentifiers:")
    print(f"  Scryfall       : {card.identifiers.scryfall_id}")
    print(f"  TCGPlayer      : {card.identifiers.tcgplayer_product_id}")
    print(f"  Cardsphere     : {card.identifiers.cardsphere_id}")
    print(f"  Cardsphere foil: {card.identifiers.cardsphere_foil_id}")
    fmt_sample = {k: v for k, v in list(card.legalities.items())[:5]}
    print(f"\nLegalities (sample): {fmt_sample} ...")
