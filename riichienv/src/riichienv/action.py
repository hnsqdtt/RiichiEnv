from enum import IntEnum
from dataclasses import dataclass, field
from typing import List, Optional

class ActionType(IntEnum):
    DISCARD = 0
    CHI = 1
    PON = 2
    DAIMINKAN = 3 # Open Kan
    RON = 4
    RIICHI = 5
    TSUMO = 6
    PASS = 7 # Pass on claim
    ANKAN = 8 # Closed Kan
    KAKAN = 9 # Add Kan (Chankan)

@dataclass
class Action:
    type: ActionType
    tile: Optional[int] = None # For Discard (tile 136 id) or Claim (target tile if needed)
    consume_tiles: List[int] = field(default_factory=list) # For Meld (tiles from hand to use)

    def to_dict(self):
        return {
            "type": self.type.value,
            "tile": self.tile,
            "consume_tiles": self.consume_tiles
        }

    @staticmethod
    def from_dict(d):
        return Action(
            type=ActionType(d["type"]),
            tile=d.get("tile"),
            consume_tiles=d.get("consume_tiles", [])
        )
