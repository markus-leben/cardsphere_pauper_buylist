from typing import Optional

from src.models import BuylistEntry, Card, PricePoints

def build_buylist(
    cards: list[Card]
) -> list[BuylistEntry]:
  entries: list[BuylistEntry] = []
  for card in cards:
    if card.name.lower() in ['plains', 'island', 'swamp', 'mountain', 'forest']:
      continue
    for finish in card.finishes:
      price = getattr(card.prices.get("tcgplayer").retail, 'foil' if finish == 'foil' else 'normal' if finish == 'nonfoil' else 'etched')
      if price is None:
        continue
      elif price < 1:
        continue
      else:
        price *= 0.5
      entries.append(BuylistEntry(
                    name=card.name,
                    set_code=card.set_code,
                    finish=finish,
                    condition="NM",
                    quantity=99,
                    price=price,
                    offer=200,
                    scryfall_id=card.identifiers.scryfall_id,
                    cardsphere_id=
                        card.identifiers.cardsphere_id if finish == "nonfoil"
                        else card.identifiers.cardsphere_foil_id if finish == "foil"
                        else card.identifiers.cardsphere_etched_id if finish == "etched"
                        else "",
                    reason="pauper relevant"
                ))

  return entries
