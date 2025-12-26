from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Meld:
    type: str # "chi", "pon", "kan", "nuki"
    tiles: List[int] # 136-based tile IDs
    opened: bool = True
    called_tile: Optional[int] = None # The tile claimed
    who: int = 0 # Relative index? Or absolute? For now mimic mahjong.meld which uses integer (default 0)
    
    # Constants to match mahjong.meld.Meld usage or preferred usage
    CHI = "chi"
    PON = "pon"
    KAN = "kan"
    NUKI = "nuki" # Kita?
