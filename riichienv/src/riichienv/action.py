from dataclasses import dataclass, field
from enum import IntEnum


class ActionType(IntEnum):
    DISCARD = 0
    CHI = 1
    PON = 2
    DAIMINKAN = 3  # Open Kan
    RON = 4  # Claim win
    RIICHI = 5  # Declare Riichi
    TSUMO = 6  # Self-draw win
    PASS = 7  # Pass on claim
    ANKAN = 8  # Closed Kan
    KAKAN = 9  # Add Kan (Chankan)
    KYUSHU_KYUHAI = 10  # Nine Terminal Abortive Draw


@dataclass
class Action:
    type: ActionType
    tile: int | None = None  # For Discard (tile 136 id) or Claim (target tile if needed)
    consume_tiles: list[int] = field(default_factory=list)  # For Meld (tiles from hand to use)

    def to_dict(self):
        return {"type": self.type.value, "tile": self.tile, "consume_tiles": self.consume_tiles}

    @staticmethod
    def from_dict(d):
        return Action(type=ActionType(d["type"]), tile=d.get("tile"), consume_tiles=d.get("consume_tiles", []))
