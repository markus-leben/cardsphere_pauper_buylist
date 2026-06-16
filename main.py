
from src.sources.mtgjson import annotate_prices as annotate_mtgjson_prices, load_cards
from src.exporter import to_csv
from src.models import Card
from src.sources import mtgoldfish
from src.buylist import build_buylist
from src.exporter import to_csv

def _has_mtggoldfish_pauper_rating(card: Card):
    return card.mtggoldfish_ratings.pauper is not None

def _tcg_price_qualifies(card: Card, min_price: float = 2.00) -> bool:
    pl = card.prices.get("tcgplayer")
    if not pl or not pl.retail:
        return False
    r = pl.retail
    return any(p is not None and p >= min_price for p in (r.normal, r.foil, r.etched))

def gather_card_data(force: bool = False) -> list[Card]:
    """Pull data from all sources and return annotated Card objects."""
    # 1. Load all CardSet printings from AllIdentifiers (keyed by UUID)
    print("Loading MTGJson AllIdentifiers...")
    cards_by_uuid = load_cards()

    # 2. Annotate MTGGoldfish format-staple rankings
    print("Loading MTGGoldfish format-staple rankings...")
    mtgoldfish.annotate_ratings(list(cards_by_uuid.values()), force=force, fetch_broadly=True)

    # 3. Annotate MTGJson prices from AllPricesToday
    annotate_mtgjson_prices(cards_by_uuid, force=force)

    candidates = [
        c for c in cards_by_uuid.values()
            if c.is_paper()
            and _has_mtggoldfish_pauper_rating(c)
            and c.identifiers.tcgplayer_product_id
            and c.identifiers.scryfall_id
            and (c.identifiers.cardsphere_id or c.identifiers.cardsphere_foil_id or c.identifiers.cardsphere_etched_id)
            # etched ids can be hinky, be sure to sanity check this
            and _tcg_price_qualifies(c)
    ]
    return candidates



def main() -> None:
  cards = gather_card_data()


  entries = build_buylist(cards)
  to_csv(entries, 'buylist.csv')


if __name__ == "__main__":
    main()