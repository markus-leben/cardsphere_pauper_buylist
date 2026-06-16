"""Export a buylist to Cardsphere-compatible CSV."""
import csv
from pathlib import Path

from src.models import BuylistEntry

CS_COLUMNS = ["Quantity", "Name", "Sets", "Conditions", "Languages", "Finishes", "Paused", "Tags", "Limit", "Offer", "Scryfall ID", "Cardsphere ID","Reason"]


def to_csv(entries: list[BuylistEntry], output_path: str | Path) -> None:
    """Write buylist entries to a CSV file ready for Cardsphere import."""
    rows = [_entry_to_row(e) for e in entries]
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CS_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Exported {len(rows)} entries to {output_path}")


def _entry_to_row(entry: BuylistEntry) -> dict:

    return {
        "Name": entry.name,
        "Sets": entry.set_code,
        "Finishes": "F" if entry.finish in ["foil", "etched"] else "N",
        "Languages": entry.language,
        "Conditions": entry.condition,
        "Quantity": entry.quantity,
        "Limit": f"{entry.price:.2f}",
        "Offer": f"{entry.offer:.0f}",
        "Scryfall ID": entry.scryfall_id or "",
        "Cardsphere ID": entry.cardsphere_id or "",
        "Reason": entry.reason,
        "Tags": "",
        "Paused": "P"
    }
