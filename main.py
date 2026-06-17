import argparse
import json
from pathlib import Path
from src.sources.mtgjson import annotate_prices as annotate_mtgjson_prices, load_cards
from src.exporter import to_csv
from src.models import Card
from src.sources import mtgoldfish
from src.buylist import build_buylist
from src.exporter import to_csv

def load_settings_json() -> dict:
    with Path("settings.json").open() as f:
        return json.load(f)


def parse_args() -> argparse.Namespace:
  p = argparse.ArgumentParser(description="Generate a Cardsphere buylist.")
  p.add_argument("--max-entries", type=int, default=100000,
                  help="Maximum number of buylist entries (default: 100000, i.e. basically infinity)")
  p.add_argument("--min-printing-price", type=float, default=2.0,
                  help="Minimum price on some printing of a given card, (default $2.00)")
  p.add_argument("--min-individual-price", type=float, default=2.0,
                  help="Minimum price on the specific individual printing of a given card, (default $2.00)")
  p.add_argument("--output", default="buylist.csv",
                  help="Output CSV file path (default: buylist.csv)")
  p.add_argument("--no-cache", action="store_true",
                  help="Ignore cached data and re-download")
  p.add_argument("--staples-only", action="store_true",
                  help="Read only the mtggoldfish staples")
  p.add_argument("--ignored_cards", action="append", default=[],
                  help="Append a card name to the list of ignored cards")
  p.add_argument("--other_columns", action="append", default=[],
                  help="Add a column with another card value")
  return p.parse_args()


def get_settings():
  settings = load_settings_json()
  args = parse_args()
  for key, value in vars(args).items():
    if settings.get(key) is None:
      settings[key] = value
    elif type(settings.get(key)) is list and value is not None:
      settings[key] = settings[key] + value
  return settings

def _has_mtggoldfish_pauper_rating(card: Card):
  return card.mtggoldfish_ratings.pauper is not None

def _tcg_price_qualifies(card: Card, min_price: float = 2.00) -> bool:
  pl = card.prices.get("tcgplayer")
  if not pl or not pl.retail:
    return False
  r = pl.retail
  return any(p is not None and p >= min_price for p in (r.normal, r.foil, r.etched))

def gather_card_data(settings: dict) -> list[Card]:
  """Pull data from all sources and return annotated Card objects."""
  # 1. Load all CardSet printings from AllIdentifiers (keyed by UUID)
  print("Loading MTGJson AllIdentifiers...")
  cards_by_uuid = load_cards(force=settings['no_cache'])

  # 2. Annotate MTGGoldfish format-staple rankings
  print("Loading MTGGoldfish format-staple rankings...")
  mtgoldfish.annotate_ratings(list(cards_by_uuid.values()), force=settings['no_cache'], staples_only=settings['staples_only'])

  # 3. Annotate MTGJson prices from AllPricesToday
  annotate_mtgjson_prices(cards_by_uuid, force=settings['no_cache'])

  candidates = [
    c for c in cards_by_uuid.values()
      if c.is_paper()
      and _has_mtggoldfish_pauper_rating(c)
      and c.identifiers.tcgplayer_product_id
      and c.identifiers.scryfall_id
      and (c.identifiers.cardsphere_id or c.identifiers.cardsphere_foil_id or c.identifiers.cardsphere_etched_id)
      # etched ids can be hinky, be sure to sanity check this
      and _tcg_price_qualifies(c, settings['min_printing_price'])
    ]
  return candidates





def main() -> None:
  settings = get_settings()
  cards = gather_card_data(settings)


  entries = build_buylist(cards, minimum_price=settings['min_individual_price'], ignored_cards=settings['ignored_cards'], other_columns=settings['other_columns'])
  to_csv(entries, settings['output'])


if __name__ == "__main__":
  main()