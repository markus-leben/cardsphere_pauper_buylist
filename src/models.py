"""Shared data models. A Card represents one CardSet printing from AllPrintings."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PricePoints:
    normal: Optional[float] = None
    foil: Optional[float] = None
    etched: Optional[float] = None


@dataclass
class PriceList:
    currency: str = "USD"
    retail: Optional[PricePoints] = None
    buylist: Optional[PricePoints] = None

@dataclass
class MtgGoldfishRatings:
    pauper: Optional[int] = None

@dataclass
class Identifiers:
    """Subset of MTGJson Identifiers fields useful for price lookups and Cardsphere targeting."""
    scryfall_id: Optional[str] = None
    scryfall_oracle_id: Optional[str] = None
    tcgplayer_product_id: Optional[str] = None
    tcgplayer_etched_product_id: Optional[str] = None
    cardsphere_id: Optional[str] = None
    cardsphere_foil_id: Optional[str] = None
    cardsphere_etched_id: Optional[str] = None # sparsely used for edge case cards where they had foil and/or nonfoil and etched in the same collector #
    card_kingdom_id: Optional[str] = None
    card_kingdom_foil_id: Optional[str] = None
    card_kingdom_etched_id: Optional[str] = None
    mtgo_id: Optional[str] = None
    mtgo_foil_id: Optional[str] = None
    mtg_arena_id: Optional[str] = None
    multiverse_id: Optional[str] = None


@dataclass
class Card:
    """
    One CardSet printing from MTGJson AllPrintings.

    Required fields mirror the CardSet required properties.
    Fields annotated by later sources (tcg_price, cardsphere_offer, etc.)
    start as None and are filled in as each source is processed.
    """
    # --- Required CardSet fields ---
    uuid: str
    name: str
    set_code: str
    number: str                         # collector number
    mana_value: float
    colors: list[str]
    color_identity: list[str]
    finishes: list[str]                 # nonfoil / foil / etched
    availability: list[str]             # paper / mtgo / arena / etc.
    border_color: str
    frame_version: str
    type_line: str                      # MTGJson field: "type"
    types: list[str]
    supertypes: list[str]
    subtypes: list[str]
    legalities: dict[str, str]          # format -> "Legal" / "Banned" / "Restricted"
    identifiers: Identifiers

    # --- Optional CardSet fields ---
    layout: Optional[str] = None
    mana_cost: Optional[str] = None
    face_mana_value: Optional[float] = None
    text: Optional[str] = None
    power: Optional[str] = None
    toughness: Optional[str] = None
    loyalty: Optional[str] = None
    defense: Optional[str] = None       # battle cards
    side: Optional[str] = None          # a/b for multi-face cards
    face_name: Optional[str] = None
    artist: Optional[str] = None
    flavor_text: Optional[str] = None
    watermark: Optional[str] = None
    security_stamp: Optional[str] = None
    original_text: Optional[str] = None
    original_type: Optional[str] = None

    keywords: list[str] = field(default_factory=list)
    frame_effects: list[str] = field(default_factory=list)
    promo_types: list[str] = field(default_factory=list)
    printings: list[str] = field(default_factory=list)     # all set codes for this card
    variations: list[str] = field(default_factory=list)    # alternate-art UUIDs in same set
    other_face_ids: list[str] = field(default_factory=list)
    booster_types: list[str] = field(default_factory=list)

    # Boolean flags
    is_reserved: bool = False
    is_promo: bool = False
    is_reprint: bool = False
    is_full_art: bool = False
    is_funny: bool = False
    is_textless: bool = False
    is_alternative: bool = False        # alternate version (e.g. Buy-a-Box promo)
    is_online_only: bool = False
    is_rebalanced: bool = False         # Alchemy rebalance
    is_oversized: bool = False
    is_game_changer: bool = False

    # EDHREC — available directly from MTGJson
    edhrec_rank: int = 9999999
    edhrec_saltiness: Optional[float] = None

    # --- Annotated by later sources ---
    prices: dict[str, PriceList] = field(default_factory=dict)  # paper vendor → PriceList
    cardsphere_offers_normal: list[float] = field(default_factory=list)
    cardsphere_offers_foil: list[float] = field(default_factory=list)
    cardsphere_offers_etched: list[float] = field(default_factory=list)
    mtggoldfish_ratings: MtgGoldfishRatings = field(default_factory=MtgGoldfishRatings)

    def is_legal_in(self, fmt: str) -> bool:
        return self.legalities.get(fmt.lower()) == "Legal"

    def is_paper(self) -> bool:
        return "paper" in self.availability

    def has_nonfoil(self) -> bool:
        return "nonfoil" in self.finishes

    def has_foil(self) -> bool:
        return "foil" in self.finishes or "etched" in self.finishes


@dataclass
class BuylistEntry:
    name: str
    set_code: str
    finish: str                          # "nonfoil" / "foil" / "etched"
    condition: str
    quantity: int
    price: float                         # calculated target buylist price
    offer: float                         # cardspheres '% of card to cap max offer at' field
    reason: Optional[str] = None
    scryfall_id: Optional[str] = None
    cardsphere_id: Optional[str] = None
    language: str = "EN"
    other_columns: dict[str, str] = field(default_factory=dict)
