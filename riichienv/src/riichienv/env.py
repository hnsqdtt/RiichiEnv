import random
import hashlib
import json
from enum import IntEnum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from .meld import Meld
from .hand import AgariCalculator, Conditions
from .action import Action, ActionType


@dataclass
class Observation:
    player_id: int
    hand: List[int] # 136-based tile IDs
    events: List[Dict[str, Any]] # MJAI events
    prev_events_size: int = 0
    _legal_actions: List[Action] = field(default_factory=list) # Internal storage for legal actions

    def legal_actions(self) -> List[Action]:
        """
        Returns the list of legal actions available to the player.
        """
        return self._legal_actions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "hand": self.hand,
            "events": self.events,
            "prev_events_size": self.prev_events_size,
            "legal_actions": [a.to_dict() for a in self._legal_actions]
        }

    def new_events(self) -> List[Dict[str, Any]]:
        """
        Returns only the new events since the last observation.
        """
        return self.events[self.prev_events_size:]

def _to_mjai_tile(tile_136: int) -> str:
    """
    Convert 136-based tile ID to MJAI tile string.
    0-35: 1m..9m
    36-71: 1p..9p
    72-107: 1s..9s
    108-135: 1z..7z
    Red tiles: 5m (16), 5p (52), 5s (88) -> usually marked 'r' in MJAI (e.g. 5mr)
    But MJai often uses 5mr, 5pr, 5sr.
    
    136 format:
    Man: 0-35. 1m=(0,1,2,3). 5m=(16,17,18,19).
    Pin: 36-71.
    Sou: 72-107.
    Hon: 108-135.
    
    Red conventions in tenhou/mjsoul:
    Depending on rule. Usually 0-index of 5 is red.
    136 indices:
    5m: 16,17,18,19.
    If 16 is red: '5mr'.
    Let's assume standard red rule: 0-th 5 is red.
    """
    kind = tile_136 // 36
    if kind < 3: # Suit
        suit_char = ['m', 'p', 's'][kind]
        offset = tile_136 % 36
        num = offset // 4 + 1
        
        # Check red
        # 5m start at 16. 5p at 52 (36+16). 5s at 88 (72+16).
        # IDs for 5: 16,17,18,19.
        is_red = False
        if num == 5:
            # Assuming 16, 52, 88 are reds (indices 0 of the 5s)
            if tile_136 in [16, 52, 88]:
                is_red = True
        
        return f"{num}{suit_char}{'r' if is_red else ''}"
    else: # Honor
        offset = tile_136 - 108
        num = offset // 4 + 1
        return f"{num}z"


class Phase(IntEnum):
    WAIT_ACT = 0      # Current player's turn (Discard/Tsumo/Kan/Riichi)
    WAIT_RESPONSE = 1 # Other players' turn to claim (Ron/Pon/Chi)


class RiichiEnv:
    def __init__(self, seed: Optional[int] = None):
        self._seed = seed
        self._rng = random.Random(seed)
        
        # Game State
        self.wall: List[int] = []
        self.hands: Dict[int, List[int]] = {} # player_id -> tiles_136
        self.melds: Dict[int, List[Any]] = {} # player_id -> list of Meld objects (Any for now to avoid circular import issue if Meld not imported)
        self.discards: Dict[int, List[int]] = {}
        self.current_player: int = 0
        self.turn_count: int = 0
        self.is_done: bool = False
        self._rewards: Dict[int, float] = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}
        
        # Phases
        self.phase: Phase = Phase.WAIT_ACT
        self.actionable_players: List[int] = [0] # Initially 0
        self.last_discard: Dict[str, Any] = None # {seat, tile_136}
        self.current_claims: Dict[int, List[Action]] = {} # Potential claims for current discard
        
        # Security
        self.wall_digest: str = ""
        self.salt: str = ""
        
        # MJAI Logging
        self.mjai_log: List[Dict[str, Any]] = []
        # Track event counts for each player to support new_events()
        self._player_event_counts: List[int] = [0, 0, 0, 0]
        
        # Current logic state
        self.drawn_tile: Optional[int] = None # The tile currently drawn by current_player
        
    def reset(self) -> Dict[int, Observation]:
        self._rng = random.Random(self._seed) # Reset RNG if seed was fixed? Or continue? Usually new seed or continue.
        # If seed was None, random.Random(None) uses system time.
        
        # Initialize tiles: 136 tiles
        # 0-33 are tile types. Each type has 4 copies.
        # IDs: 0-135. Type = id // 4.
        self.wall = list(range(136))
        self._rng.shuffle(self.wall)
        
        # Secure Wall
        self.salt = ''.join([chr(self._rng.randint(33, 126)) for _ in range(16)]) # Random ASCII salt
        wall_str = ",".join(map(str, self.wall))
        self.wall_digest = hashlib.sha256((wall_str + self.salt).encode('utf-8')).hexdigest()
        
        self.hands = {0: [], 1: [], 2: [], 3: []}
        self.discards = {0: [], 1: [], 2: [], 3: []}
        self._rewards = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}
        self.is_done = False
        self.turn_count = 0
        self.current_player = 0 # Dealer = 0 (East)
        self.phase = Phase.WAIT_ACT
        self.actionable_players = [0]
        self.current_claims = {}
        self.last_discard = None
        self.melds = {0: [], 1: [], 2: [], 3: []}

        self.mjai_log = []
        self._player_event_counts = [0, 0, 0, 0] # Reset counts
        self.mjai_log.append({"type": "start_game", "names": ["Player0", "Player1", "Player2", "Player3"], "id": "local_game_0"})
        
        # Deal 13 tiles to each
        for _ in range(13):
            for pid in range(4):
                self.hands[pid].append(self.wall.pop())
                
        # Dealer draws 14th tile
        self.drawn_tile = self.wall.pop()
        
        # Sort hands for convenience (though 136-ids don't have perfect order, we just keep them list)
        for pid in range(4):
            self.hands[pid].sort()

        # Start Kyoku Event
        # We need to construct tehais
        tehais = []
        for pid in range(4):
            tehais.append([_to_mjai_tile(t) for t in self.hands[pid]])
            
        start_kyoku_event = {
            "type": "start_kyoku",
            "bakaze": "E",
            "kyoku": 1,
            "honba": 0,
            "kyotaku": 0,
            "oya": 0,
            "dora_marker": _to_mjai_tile(self.wall[0]), # Fake dora marker logic: usually wall[5] or similar. Using wall[0] for current simplistic impl.
            "tehais": tehais
        }
        self.mjai_log.append(start_kyoku_event)
        
        # Tsumo Event for Dealer
        tsumo_event = {
            "type": "tsumo",
            "actor": 0,
            "tile": _to_mjai_tile(self.drawn_tile)
        }
        self.mjai_log.append(tsumo_event)

        # Check Tsumo logic...
        
        return self._get_observations(self.actionable_players) # Start state

    def step(self, actions: Dict[int, Action]) -> Dict[int, Observation]:
        """
        Execute one step.
        actions: Map from player_id to Action.
        """
        if self.is_done:
            return self._get_observations([])
            
        # Convert raw dict/int to Action objects if needed
        # Assuming actions is {pid: Action object} or {pid: legacy_int}
        
        # PHASE: WAIT_ACT
        if self.phase == Phase.WAIT_ACT:
            # Expect action from current_player
            action_raw = actions.get(self.current_player)
            if action_raw is None:
                # Should not happen if correctly used
                return self._get_observations(self.actionable_players)
                
            action: Action = action_raw
            
            # ... Discard process ...
            # For now, let's assume we proceed with discard.
            # If ActionType.TSUMO -> End.
            
            # Default logic for discard (same as before but updated)
            # 1. Discard
            discard_tile_id = -1
            
            if action.type == ActionType.TSUMO:
                # Handle tsumo (self-draw win): record the event and stop further processing.
                tsumo_event = {
                    "type": "tsumo",
                    "actor": self.current_player,
                }
                if self.drawn_tile is not None:
                    tsumo_event["pai"] = _to_mjai_tile(self.drawn_tile)

                self.mjai_log.append(tsumo_event)
                # After a tsumo win, no discard should occur; return observations immediately.abs
                
                # Set is_done to True
                self.is_done = True
                
                return self._get_observations([])

            elif action.type == ActionType.DISCARD:
                 discard_tile_id = action.tile

            # Execute discard
            # Remove from hand
            if self.drawn_tile == discard_tile_id:
                self.drawn_tile = None
            else:
                 found = False
                 if self.drawn_tile is not None:
                      self.hands[self.current_player].append(self.drawn_tile)
                      self.drawn_tile = None
                 
                 # Remove discard_tile_id from self.hands
                 # It must exist
                 if discard_tile_id in self.hands[self.current_player]:
                      self.hands[self.current_player].remove(discard_tile_id)
                 else:
                      # Error or fallback
                      pass
                      
            self.discards[self.current_player].append(discard_tile_id)
            self.hands[self.current_player].sort()
            
            # Log Dahai
            dahai_event = {
                 "type": "dahai",
                 "actor": self.current_player,
                 "tile": _to_mjai_tile(discard_tile_id),
                 "tsumogiri": False # TODO: Handle tsumogiri (self-draw)
            }
            self.mjai_log.append(dahai_event)
            
            # Store last discard
            self.last_discard = {"seat": self.current_player, "tile": discard_tile_id}
            
            # Check claims potential
            self.current_claims = {}
            
            # Ron Check (Priority 1)
            ron_potential = []
            for pid in range(4):
                if pid == self.current_player: continue
                # Calc Ron
                res = AgariCalculator(self.hands[pid], self.melds.get(pid, [])).calc(discard_tile_id, conditions=Conditions(tsumo=False))
                if res.agari:
                    ron_potential.append(pid)
                    self.current_claims.setdefault(pid, []).append(Action(ActionType.RON, tile=discard_tile_id))
            
            # Pon/Kan Check (Priority 2)
            # Valid for all other players
            for pid in range(4):
                if pid == self.current_player: continue
                
                # Pon
                pon_opts = self._can_pon(self.hands[pid], discard_tile_id)
                for opt in pon_opts:
                    self.current_claims.setdefault(pid, []).append(Action(ActionType.PON, tile=discard_tile_id, consume_tiles=opt))
                    
                # Kan (Daiminkan)
                kan_opts = self._can_kan(self.hands[pid], discard_tile_id)
                for opt in kan_opts:
                    self.current_claims.setdefault(pid, []).append(Action(ActionType.DAIMINKAN, tile=discard_tile_id, consume_tiles=opt))

            # Chi Check (Priority 3)
            # Only valid for next player
            next_player = (self.current_player + 1) % 4
            chi_opts = self._can_chi(self.hands[next_player], discard_tile_id)
            for opt in chi_opts:
                self.current_claims.setdefault(next_player, []).append(Action(ActionType.CHI, tile=discard_tile_id, consume_tiles=opt))

            if self.current_claims:
                 self.phase = Phase.WAIT_RESPONSE
                 self.actionable_players = list(self.current_claims.keys())
                 self.actionable_players.sort() # generic order
                 
                 return self._get_observations(self.actionable_players)
                 
            # If no response needed -> Next
            self.current_player = (self.current_player + 1) % 4
            if not self.wall:
                 self.is_done = True
                 self.mjai_log.append({"type": "ryukyoku", "reason": ""}) # Exhaustive draw
                 self.mjai_log.append({"type": "end_kyoku"})
                 self.mjai_log.append({"type": "end_game"})
                 return self._get_observations([])
            
            self.drawn_tile = self.wall.pop()
            # Log Tsumo
            tsumo_event = {
                "type": "tsumo",
                "actor": self.current_player,
                "tile": _to_mjai_tile(self.drawn_tile)
            }
            self.mjai_log.append(tsumo_event)

            self.phase = Phase.WAIT_ACT
            self.actionable_players = [self.current_player]
            
            return self._get_observations(self.actionable_players)

        # PHASE: WAIT_RESPONSE
        elif self.phase == Phase.WAIT_RESPONSE:
            # Priority resolution: Ron > Pon/Kan > Chi
            # Collect valid actions
            valid_actions = {} # pid -> Action
            
            for pid in self.actionable_players:
                act = actions.get(pid)
                if act and isinstance(act, Action):
                    # Validate against legal (or current_claims)
                    # For simplicity, check type
                    if act.type in [ActionType.RON, ActionType.PON, ActionType.DAIMINKAN, ActionType.CHI]:
                         valid_actions[pid] = act
            
            # 1. Check Ron
            ronners = [pid for pid, a in valid_actions.items() if a.type == ActionType.RON]
            if ronners:
                # Handle Ron (Multiple Ron possible?)
                # Assuming Head Bump (Atamahane) for now or double ron.
                # Let's implement Atamahane: Start from current_player, find first ronner.
                
                winner = -1
                for i in range(1, 4):
                    p = (self.current_player + i) % 4
                    if p in ronners:
                        winner = p
                        break
                        
                self.is_done = True
                self.mjai_log.append({
                    "type": "hora",
                    "actor": winner,
                    "target": self.current_player,
                    "tile": _to_mjai_tile(self.last_discard["tile"]),
                    # "yakus": ... TODO
                })
                # rewards logic...
                # Note: Currently verification script checks 'end_game' type.
                # step (WAIT_ACT -> Ryukyoku) logs 'end_game'.
                # We should log 'end_game' here too.
                self.mjai_log.append({"type": "end_game"})
                
                return self._get_observations([])

            # 2. Check Pon/Kan
            ponners = [pid for pid, a in valid_actions.items() if a.type in [ActionType.PON, ActionType.DAIMINKAN]]
            if ponners:
                # Should only be one ponner (tiles uniqueness)
                claimer = ponners[0]
                action = valid_actions[claimer]
                
                # Execute Meld
                self._execute_claim(claimer, action)
                
                # Turn moves to claimer
                self.current_player = claimer
                self.phase = Phase.WAIT_ACT # Must discard next
                self.actionable_players = [self.current_player]
                self.drawn_tile = None # No draw after call (except some Kan...)
                
                return self._get_observations(self.actionable_players)

            # 3. Check Chi
            chiers = [pid for pid, a in valid_actions.items() if a.type == ActionType.CHI]
            if chiers:
                 # Only next player can Chi
                 claimer = chiers[0]
                 action = valid_actions[claimer]
                 
                 self._execute_claim(claimer, action)
                 
                 self.current_player = claimer
                 self.phase = Phase.WAIT_ACT
                 self.actionable_players = [self.current_player]
                 self.drawn_tile = None
                 
                 return self._get_observations(self.actionable_players)

            # If no Claim -> Pass -> Next Draw
            self.current_player = (self.current_player + 1) % 4
            self.phase = Phase.WAIT_ACT
            self.actionable_players = [self.current_player]
            
            if self.wall:
                   self.drawn_tile = self.wall.pop()
                   # Log Tsumo
                   tsumo_event = {
                       "type": "tsumo",
                       "actor": self.current_player,
                       "tile": _to_mjai_tile(self.drawn_tile)
                   }
                   self.mjai_log.append(tsumo_event)
                   
                   return self._get_observations(self.actionable_players)
            else:
                   # Ryukyoku
                   self.is_done = True
                   self.mjai_log.append({"type": "ryukyoku", "reason": "fanpai"})
                   self.mjai_log.append({"type": "end_kyoku"})
                   self.mjai_log.append({"type": "end_game"})
                   return self._get_observations([])

        return self._get_observations([])

    def done(self) -> bool:
        return self.is_done

    def rewards(self) -> Dict[int, float]:
        return self._rewards

    def _get_observations(self, player_ids: List[int]) -> Dict[int, Observation]:
        obs_dict = {}
        for pid in player_ids:
            # Construct hand for observation
            # If current player, include drawn tile
            hand = self.hands[pid][:]
            if pid == self.current_player and self.drawn_tile is not None:
                hand.append(self.drawn_tile)
                
            # Filter MJAI events for this player
            filtered_events = []
            for ev in self.mjai_log:
                ev_copy = ev.copy()
                if ev["type"] == "start_kyoku":
                    # Mask tehais of others
                    tehais = ev["tehais"]
                    masked_tehais = []
                    for i, t_list in enumerate(tehais):
                        if i == pid:
                            masked_tehais.append(t_list)
                        else:
                            masked_tehais.append(["?"] * len(t_list))
                    ev_copy["tehais"] = masked_tehais
                elif ev["type"] == "tsumo":
                    # Mask tile if not actor
                    if ev["actor"] != pid:
                        ev_copy["tile"] = "?"
                
                filtered_events.append(ev_copy)
                
            prev_size = self._player_event_counts[pid]
            
            # Legal Actions
            legal = []
            if pid in player_ids: # Calculate legal actions only for actionable players
                 legal = self._get_legal_actions(pid)

            obs_dict[pid] = Observation(
                player_id=pid,
                hand=hand,
                events=filtered_events,
                prev_events_size=prev_size,
                _legal_actions=legal
            )
            # Update count for next time
            self._player_event_counts[pid] = len(filtered_events)
            
        return obs_dict

    def _get_legal_actions(self, pid: int) -> List[Action]:
        actions = []
        hand = self.hands[pid][:]
        
        if self.phase == Phase.WAIT_ACT:
            # pid is current_player
            # Basic Discard: all tiles in hand (plus drawn if exist)
            if self.drawn_tile is not None:
                hand.append(self.drawn_tile)
            # Just return unique tiles to discard? Or all 14?
            # 136-tiles are unique.
            # Usually we return all possible discards.
            for t in hand:
                actions.append(Action(ActionType.DISCARD, tile=t))
            
            # Tsumo logic
            if self.drawn_tile is not None: # Only possible if just drawn
                calc = AgariCalculator(hand, [])
                # Pass drawn_tile as win_tile (it's already in hand, but for calc API constraints...)
                # See earlier note: pass 13 tiles + win_tile.
                # Here 'hand' has 14 tiles.
                # With 14 tiles, if we pass win_tile, wrapper might fail.
                # Let's recreate 13+1.
                hand_13 = hand[:]
                hand_13.remove(self.drawn_tile)
                
                res = AgariCalculator(hand_13, []).calc(self.drawn_tile, conditions=Conditions(tsumo=True))
                if res.agari:
                    actions.append(Action(ActionType.TSUMO))

        elif self.phase == Phase.WAIT_RESPONSE:
            # pid is claiming discard
            actions.append(Action(ActionType.PASS))
            
            # Use cached current_claims
            if pid in self.current_claims:
                 actions.extend(self.current_claims[pid])
                
        return actions

    def _execute_claim(self, pid: int, action: Action):
        """Executes a claim action (PON, CHI, KAN)"""
        # 1. Remove tiles from hand
        hand = self.hands[pid]
        consume = action.consume_tiles
        for t in consume:
            if t in hand:
                hand.remove(t)
            else:
                # Should not happen if confirmed legal
                pass
                
        # 2. Create Meld
        target_tile = action.tile
        tiles = sorted(consume + [target_tile])
        
        # Determine Meld Type
        m_type_const = Meld.PON
        if action.type == ActionType.CHI: m_type_const = Meld.CHI
        elif action.type == ActionType.DAIMINKAN: m_type_const = Meld.KAN
        elif action.type == ActionType.ANKAN: m_type_const = Meld.KAN # Not daiminkan though, handled separately?
        
        # Check calling logic
        meld = Meld(m_type_const, tiles, opened=True, called_tile=target_tile)
        self.melds.setdefault(pid, []).append(meld)
        
        # 3. Log MJAI
        mjai_type = "pon"
        if action.type == ActionType.CHI: mjai_type = "chi"
        elif action.type == ActionType.DAIMINKAN: mjai_type = "kan" 
        
        discarder = self.last_discard['seat'] if self.last_discard else -1
        
        event = {
            "type": mjai_type,
            "actor": pid,
            "target": discarder,
            "tile": _to_mjai_tile(target_tile),
            "consumed": [_to_mjai_tile(t) for t in consume]
        }
        self.mjai_log.append(event)
        
    def _can_pon(self, hand: List[int], tile: int) -> List[List[int]]:
        """Returns list of consume_tiles options for Pon."""
        tile_type = tile // 4
        matches = [t for t in hand if t // 4 == tile_type]
        if len(matches) < 2:
            return []
        return [matches[:2]]

    def _can_kan(self, hand: List[int], tile: int) -> List[List[int]]:
        """Daiminkan"""
        tile_type = tile // 4
        matches = [t for t in hand if t // 4 == tile_type]
        if len(matches) == 3:
            return [matches]
        return []

    def _can_chi(self, hand: List[int], tile: int) -> List[List[int]]:
        """Returns list of consume_tiles options for Chi."""
        t_type = tile // 4
        if t_type >= 27: return [] # Honors check
        
        idx = t_type % 9
        hand_types = sorted(list(set(t // 4 for t in hand)))
        options = []
        
        # Left: T-2, T-1, T
        if idx >= 2:
            if (t_type - 2) in hand_types and (t_type - 1) in hand_types:
                c1 = next(t for t in hand if t // 4 == t_type - 2)
                c2 = next(t for t in hand if t // 4 == t_type - 1)
                options.append([c1, c2])
        # Center: T-1, T, T+1
        if idx >= 1 and idx <= 7:
            if (t_type - 1) in hand_types and (t_type + 1) in hand_types:
                c1 = next(t for t in hand if t // 4 == t_type - 1)
                c2 = next(t for t in hand if t // 4 == t_type + 1)
                options.append([c1, c2])
        # Right: T, T+1, T+2
        if idx <= 6:
            if (t_type + 1) in hand_types and (t_type + 2) in hand_types:
                c1 = next(t for t in hand if t // 4 == t_type + 1)
                c2 = next(t for t in hand if t // 4 == t_type + 2)
                options.append([c1, c2])
        return options

        
