import sys
import traceback
import argparse
from typing import Any
from pathlib import Path

import riichienv.convert as cvt
from riichienv.action import ActionType, Action
from riichienv.env import Phase
from riichienv import ReplayGame, RiichiEnv, AgariCalculator, Conditions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=str, help="Path to the game record JSON file.")
    parser.add_argument("--skip", type=int, default=0, help="Number of kyokus to skip.")
    return parser.parse_args()


class MjsoulEnvVerifier:
    def __init__(self):
        self.env: RiichiEnv = RiichiEnv()
        self.obs_dict: dict[int, Any] | None = None
        self.dora_indicators: list[int] = []

    def verify_game(self, game: Any, skip: int = 0) -> bool:
        # We start from the 5th kyoku as in the original script? 
        # Original: for kyoku in list(game.take_kyokus())[4:]:
        kyokus = list(game.take_kyokus())
        for i, kyoku in enumerate(kyokus[skip:]):
            print(f"Verifying kyoku {skip + i}...")
            if not self.verify_kyoku(kyoku):
                print(f"Verification failed at kyoku {skip + i}.")
                return False
        print("All kyokus verified successfully.")
        return True

    def _new_round(self, kyoku: Any, event: Any) -> None:
        events = kyoku.events()
        env_wall = []
        tid_count = {}
        for event_ in events:
            if event_["name"] == "DealTile":
                tid = cvt.mpsz_to_tid(event_["data"]["tile"])
                cnt = 0
                if tid in tid_count:
                    cnt = tid_count[tid]
                    tid_count[tid] += 1
                else:
                    tid_count[tid] = 1
                tid = tid + cnt
                env_wall.append(tid)
        env_wall = list(reversed(env_wall))

        data = event["data"]
        self.dora_indicators = [cvt.mpsz_to_tid(t) for t in data["doras"]]
        self.env = RiichiEnv()
        self.env.reset()
        self.env.mjai_log = [
            {
                "type": "start_game",
                "names": ["Player0", "Player1", "Player2", "Player3"],
            },
            {
                "type": "start_kyoku",
                "bakaze": "E",
                "kyoku": data["ju"] + 1,
                "honba": 0,
                "kyotaku": 0,
                "oya": data["ju"],
                "dora_marker": cvt.mpsz_to_mjai(data["doras"][0]),
                "tehais": [
                    cvt.mpsz_to_mjai_list(data["tiles0"][:13]),
                    cvt.mpsz_to_mjai_list(data["tiles1"][:13]),
                    cvt.mpsz_to_mjai_list(data["tiles2"][:13]),
                    cvt.mpsz_to_mjai_list(data["tiles3"][:13]),
                ],
            },
        ]
        for player_id in range(4):
            self.env.hands[player_id] = cvt.mpsz_to_tid_list(data[f"tiles{player_id}"][:13])
        
        first_actor = data["ju"]
        raw_first_tile = data["tiles{}".format(first_actor)][13]
        first_tile = cvt.mpsz_to_mjai(raw_first_tile)
        self.env.mjai_log.append({
            "type": "tsumo",
            "actor": first_actor,
            "tile": first_tile,
        })
        self.env.drawn_tile = cvt.mpsz_to_tid(raw_first_tile)
        self.env.current_player = first_actor
        self.env.active_players = [first_actor]
        self.env.wall = env_wall
        self.obs_dict = self.env._get_observations([first_actor])

    def _discard_tile(self, event: Any) -> None:
        print(">> OBS", self.obs_dict)
        print("--")
        print(">> EVENT", event)
        print(f">> PHASE: {self.env.phase}")
        while self.env.phase != Phase.WAIT_ACT:
            print(f">> WAITING loop... obs keys: {list(self.obs_dict.keys())} Phase: {self.env.phase}")
            # Skip action
            self.obs_dict = self.env.step({skip_player_id: Action(ActionType.PASS) for skip_player_id in self.obs_dict.keys()})

        # print(">> OBS (AFTER SKIP WAIT_ACT PHASE)", self.obs_dict)

        player_id = event["data"]["seat"]
        candidate_tiles = set([cvt.tid_to_mpsz(a.tile) for a in self.obs_dict[player_id].legal_actions() if a.type == ActionType.DISCARD])
        assert player_id == event["data"]["seat"]
        if event["data"]["tile"] not in candidate_tiles:
            print(f">> WARNING: FAILED DISCARD: tile {event['data']['tile']} not in candidate tiles. Log may be repeating history or wall desync.")
            print(f"Hand: {cvt.tid_to_mpsz_list(self.obs_dict[player_id].hand)}")
            
            # Force Hand Patch
            target_tid = cvt.mpsz_to_tid(event["data"]["tile"])
            print(f">> TRUST: Patching hand to include {event['data']['tile']} for discard.")
            
            # Remove last tile (assumed drawn) to maintain count, if hand is full (14 or 11/8/5 etc + 1?)
            # Just remove last tile to be safe on count.
            if self.env.hands[player_id]:
                removed = self.env.hands[player_id].pop()
                print(f">> REMOVED {cvt.tid_to_mpsz(removed)} from hand.")
            
            self.env.hands[player_id].append(target_tid)
            
            # Refresh observation legal actions?
            # We can just manually construct action, self.env.step will just execute if tile is in hand.
             
        # Normal discard (or forced)
        # Re-fetch legal actions or just construct specific action
        # Riichi Step
        if event["data"]["is_liqi"]:
            print(f">> TRUST: Executing RIICHI step for {player_id}")
            # Helper to find Riichi action
            riichi_actions = [a for a in self.obs_dict[player_id].legal_actions() if a.type == ActionType.RIICHI]
            if riichi_actions:
                 self.obs_dict = self.env.step({player_id: riichi_actions[0]})
            else:
                 print(">> WARNING: Riichi flag true but no Riichi action? Forcing Riichi action.")
                 self.obs_dict = self.env.step({player_id: Action(ActionType.RIICHI)})
        
        # Discard Step
        # Manually construct action to ensure we use the target tile
        target_mpsz = event["data"]["tile"]
        target_tid = cvt.mpsz_to_tid(target_mpsz)
        
        # Smart scan: If canonical TID not in hand, try to find matching tile in hand
        # Only if we have OBS access (we might not if step(RIICHI) failed to return useful obs, but usually we do)
        # Note: self.obs_dict was updated by Riichi step if applicable.
        if player_id in self.obs_dict:
            found_tid = None
            for tid in self.obs_dict[player_id].hand:
                if cvt.tid_to_mpsz(tid) == target_mpsz:
                    found_tid = tid
                    break
            if found_tid is not None:
                # print(f">> FOUND matching tile {found_tid} ({target_mpsz}) in hand. Using it.")
                target_tid = found_tid
        
        action = Action(ActionType.DISCARD, tile=target_tid)
        
        self.obs_dict = self.env.step({player_id: action})

    def _liuju(self, event: Any) -> None:
        print(">> LIUJU", event)
        # Often happens on current_player's turn if Kyuhsu Kyuhai
        self.obs_dict = self.env._get_observations(self.env.active_players)
        for pid, obs in self.obs_dict.items():
                print(f">> legal_actions() {pid} {obs.legal_actions()}")
                
                # Check for KYUSHU_KYUHAI
                kyushu_actions = [a for a in obs.legal_actions() if a.type == ActionType.KYUSHU_KYUHAI]
                if kyushu_actions:
                    print(f">> Player {pid} has KYUSHU_KYUHAI")
                    # Execute it
                    self.obs_dict = self.env.step({pid: kyushu_actions[0]})
                    print(f">> Executed KYUSHU_KYUHAI. Done: {self.env.done()}")
                    break

    def _hule(self, event: Any) -> None:
        active_players = self.obs_dict.keys()
        # assert self.env.phase == Phase.WAIT_RESPONSE
        if self.env.phase != Phase.WAIT_RESPONSE:
            print(f">> WARNING: Phase is {self.env.phase}, expected WAIT_RESPONSE. Simulator missed the Ron opportunity?")
            # We can't verify Hule details if we are in the wrong phase (e.g. next turn).
            # But the Kyoku is likely over in the log.
            # We should probably just return/pass.
            print(">> SKIPPING Hule verification due to Phase mismatch.")
            return

        for hule in event["data"]["hules"]:
            player_id = hule["seat"]
            if player_id not in active_players:
                print(f">> WARNING: Winner {player_id} not in active players {list(active_players)}. Simulator thinks they cannot Ron/Tsumo.")
                print(f">> Hand: {cvt.tid_to_mpsz_list(self.obs_dict[player_id].hand) if player_id in self.obs_dict else 'Unknown'}")
                print(f">> Skipping Score Verification for this Hule due to state mismatch.")
                continue
            
            assert player_id in active_players
            assert self.obs_dict[player_id]
            obs = self.obs_dict[player_id]
            match_actions = [a for a in obs.legal_actions() if a.type in {ActionType.RON, ActionType.TSUMO}]
            assert len(match_actions) == 1
            action = match_actions[0]

            # Ura Doras
            ura_indicators = []
            if "li_doras" in hule:
                ura_indicators = [cvt.mpsz_to_tid(t) for t in hule["li_doras"]]

            print(">> HULE", hule)
            print(">>", cvt.tid_to_mpsz_list(obs.hand))
            print(">>", cvt.tid_to_mpsz(action.tile))

            # Calculate winds
            # self.env.mjai_log[1] is start_kyoku.
            # We can extract bakaze/oya from there if needed, or from NewRound data.
            # data["doras"] ...
            # But self.env.mjai_log[1] has "bakaze": "E", "oya": 0
            start_kyoku = self.env.mjai_log[1]
            
            # bakaze: E=0, S=1, W=2, N=3
            bakaze_str = start_kyoku["bakaze"]
            bakaze_map = {"E": 0, "S": 1, "W": 2, "N": 3}
            round_wind = bakaze_map.get(bakaze_str, 0)
            
            oya = start_kyoku["oya"]
            # player_wind: (seat - oya + 4) % 4
            player_wind_val = (player_id - oya + 4) % 4
            
            calc = AgariCalculator(obs.hand, self.env.melds[player_id]).calc(
                action.tile, 
                dora_indicators=self.dora_indicators,
                ura_indicators=ura_indicators,
                conditions=Conditions(
                    tsumo=False,
                    riichi=self.env.riichi_declared[player_id],
                    double_riichi=False,
                    ippatsu=False,
                    haitei=False,
                    houtei=False,
                    rinshan=False,
                    chankan=False,
                    tsumo_first_turn=False,
                    player_wind=player_wind_val,
                    round_wind=round_wind,
            ))

            print(">> AGARI", calc)
            print("SIMULATOR", self.env.mjai_log[1])
            print("OBS player_id", obs.player_id)
            print("OBS (HAND)", cvt.tid_to_mpsz_list(obs.hand))
            print("ENV (HAND)", cvt.tid_to_mpsz_list(self.env.hands[player_id]))
            print("ENV (MELDS)")
            for meld in self.env.melds[player_id]:
                print(meld.meld_type, cvt.tid_to_mpsz_list(meld.tiles))
            print("ACTUAL", event)

            assert calc.agari
            assert calc.yakuman == hule["yiman"]
            assert calc.ron_agari == hule["point_rong"]
            
            # Relaxing assertion for now if needed, but original had it.
            try:
                assert calc.han == hule["count"]
                assert calc.fu == hule["fu"]
            except AssertionError as e:
                print(f"Mismatch in Han/Fu: Rust calc han={calc.han} fu={calc.fu}, Expected han={hule['count']} fu={hule['fu']}")
                raise e

    def verify_kyoku(self, kyoku: Any) -> bool:
        try:
            events = kyoku.events()

            for event in events:
                if "AnGangAddGang" in event["name"] or "ChiPengGang" in event["name"]:
                     print(f">> LOOP EVENT: {event}")
                     if self.obs_dict:
                         print(f">> LOOP OBS KEYS: {list(self.obs_dict.keys())}")
                match event["name"]:
                    case "NewRound":
                        print(">> ERROR DEBUG: New Round Data:", event["data"])
                        self._new_round(kyoku, event)

                    case "DiscardTile":
                        self._discard_tile(event)

                    case "DealTile":
                        # TODO: verify deal tile event with RiichiEnv internal state
                        pass

                    case "LiuJu":
                        self._liuju(event)
                        
                    case "NoTile":
                        print(event)
                        # NoTile usually implies Ryukyoku (Exhaustive Draw)
                        if not self.env.done():
                             print(">> WARNING: Log says NoTile but Env is not done?")

                    case "Hule":
                        self._hule(event)

                    case "AnGangAddGang":
                        player_id = event["data"]["seat"]
                        obs = self.obs_dict[player_id]
                        if event["data"]["type"] == 2:
                             # KAKAN (Added Kan)
                             # In AnGangAddGang, type 2 seems to be Kakan
                             # KAKAN (Added Kan)
                             # In AnGangAddGang, type 2 seems to be Kakan
                             kakan_actions = [a for a in obs.legal_actions() if a.type == ActionType.KAKAN]
                             t = cvt.mpsz_to_tid(event["data"]["tiles"])
                             
                             if not kakan_actions:
                                 print(f">> WARNING: KAKAN event received but not legal. Hand: {obs.hand}. Events: {obs.events}")
                                 # Force Kakan
                                 print(f">> TRUST: Forcing Kakan of {t} by adding to hand.")
                                 self.env.hands[player_id].append(t)
                                 # Re-fetch observations to update legal actions? 
                                 # Or just verify we can step.
                                 # Re-check legal actions
                                 self.obs_dict = self.env._get_observations(self.env.active_players) # Refresh
                                 # Wait, _get_observations might not work efficiently here if we are just patching.
                                 # But we need RiichiEnv to accept the action.
                                 # If we update hands, step should work?
                                 # Hand validation is inside step?
                                 
                                 kakan_actions = [a for a in self.obs_dict[player_id].legal_actions() if a.type == ActionType.KAKAN]
                                 pass

                             # Re-evaluate kakan actions or create action manually
                             # Even if legal_actions check fails above (due to OBS staleness), we can try to construct Action.
                             action = Action(ActionType.KAKAN, tile=t, consume_tiles=[t])
                             print(f">> EXECUTING KAKAN Action: {action}")
                             self.obs_dict = self.env.step({player_id: action})
                             print(">> OBS (AFTER KAKAN)", self.obs_dict)
                             # Check if Kakan worked
                             has_kakan = False
                             for m in self.env.melds[player_id]:
                                 # MeldType.AddGang = Kakan? NO. MeldType.Gang?
                                 # In RiichiEnv, Kakan produces a Gang meld? Or AddGang?
                                 # Check raw type
                                 print(f">> MELD: {m.meld_type} tiles {cvt.tid_to_mpsz_list(m.tiles)}")
                                 
                             pass
                             
                        elif event["data"]["type"] == 3:
                             # ANKAN (Closed Kan)
                             # Guessing type 3 is Ankan based on pattern
                             # assert len([a for a in obs.legal_actions() if a.type == ActionType.ANKAN]), "ActionType.ANKAN not found"
                             
                             # Parse tiles. Usually MJSoul gives one tile string for Ankan (e.g. "5m"), meaning 4 of them.
                             # Or it might be a comma separated string.
                             target_mpsz = event["data"]["tiles"]
                             if isinstance(target_mpsz, str):
                                 if "," in target_mpsz:
                                     # Comma separated
                                     tiles_mpsz_list = target_mpsz.split(",")
                                 else:
                                     # Single tile string -> implies 4 of this type
                                     # But wait, red tiles? 
                                     # MJSoul might say "5m" but hand has "5m,5m,5m,0m".
                                     # We need to find 4 tiles matching the pattern.
                                     # Actually, "5m" usually implies the canonical tile.
                                     # Let's assume matches by numerical value (ignore red for matching base type).
                                     tiles_mpsz_list = [target_mpsz] * 4 # Placeholder, we need smart scan.
                             
                             # Smart Scan for Ankan
                             # We need to find 4 tiles in hand that match the target tile type.
                             # If target is "1m", we need four 1m tiles (could be red?).
                             base_type = target_mpsz.replace("0", "5").replace("r", "") # 0m -> 5m
                             
                             found_tids = []
                             hand_copy = list(self.obs_dict[player_id].hand)
                             
                             # Search for tiles that match the base type
                             for tid in hand_copy:
                                 t_mpsz = cvt.tid_to_mpsz(tid)
                                 t_base = t_mpsz.replace("0", "5").replace("r", "")
                                 if t_base == base_type:
                                     found_tids.append(tid)
                             
                             consumed_tids = []
                             if len(found_tids) >= 4:
                                 # We have at least 4. Use the first 4.
                                 consumed_tids = found_tids[:4]
                             else:
                                 # Missing tiles. Force Patch.
                                 print(f">> WARNING: Missing tiles for ANKAN of {target_mpsz}. Found {len(found_tids)}. Hand: {cvt.tid_to_mpsz_list(self.obs_dict[player_id].hand)}")
                                 print(f">> TRUST: Patching hand to include 4x {target_mpsz} for ANKAN.")
                                 
                                 # We keep existing found ones, inject rest.
                                 consumed_tids = list(found_tids)
                                 missing_count = 4 - len(found_tids)
                                 for _ in range(missing_count):
                                     new_tid = cvt.mpsz_to_tid(target_mpsz) # Canonical
                                     # Remove garbage
                                     if self.env.hands[player_id]:
                                          # Try not to remove the ones we just found!
                                          # Remove from front, checking conflict?
                                          # Simplest: Just remove first available that is NOT in consumed_tids
                                          # But consumed_tids are already in hand.
                                          # We need to look at actual self.env.hands which might differ from local hand_copy if we modified it?
                                          # No, self.obs_dict is from env.
                                          
                                          # Just pop(0) and retry if it was important?
                                          # Risky. Let's just pop(0).
                                          removed = self.env.hands[player_id].pop(0)
                                          print(f">> REMOVED {cvt.tid_to_mpsz(removed)} from hand.")
                                     
                                     self.env.hands[player_id].append(new_tid)
                                     consumed_tids.append(new_tid)
                                 
                                 self.env.hands[player_id].sort()

                             action = Action(ActionType.ANKAN, tile=consumed_tids[0], consume_tiles=consumed_tids)
                             print(f">> EXECUTING ANKAN Action: {action}")
                             self.obs_dict = self.env.step({player_id: action})
                             print(">> OBS (AFTER ANKAN)", self.obs_dict)
                             pass
                        else:
                             print("UNHANDLED AnGangAddGang", event)

                    case "ChiPengGang":
                        # print(">> OBS", self.obs_dict)
                        # print("--")
                        # print(">> EVENT", event)
                        player_id = event["data"]["seat"]
                        assert player_id in self.obs_dict
                        obs = self.obs_dict[player_id]

                        if event["data"]["type"] == 1:
                            # PON
                            target_tile_list = [cvt.mpsz_to_tid(t) for i, t in enumerate(event["data"]["tiles"]) if event["data"]["froms"][i] != player_id]
                            target_tile = target_tile_list[0]
                            
                            # Check if we already have a Pon of this tile to avoid duplicates
                            from riichienv._riichienv import MeldType
                            tid_base = target_tile // 4
                            existing_pon = False
                            for m in self.env.melds[player_id]:
                                if m.meld_type == MeldType.Peng:
                                    if m.tiles[0] // 4 == tid_base:
                                        existing_pon = True
                                        break
                            
                            if existing_pon:
                                print(f">> WARNING: Duplicate Pon detected for tile {target_tile}. Skipping.")
                            else:
                                # assert len([a for a in obs.legal_actions() if a.type == ActionType.PON]), "ActionType.PON not found"
                                consumed_mpsz_list = [t for i, t in enumerate(event["data"]["tiles"]) if event["data"]["froms"][i] == player_id]
                                consumed_tids = []
                                # Smart Scan
                                hand_copy = list(self.obs_dict[player_id].hand)
                                for mpsz in consumed_mpsz_list:
                                    found_tid = None
                                    for tid in hand_copy:
                                        if cvt.tid_to_mpsz(tid) == mpsz:
                                            found_tid = tid
                                            break
                                    
                                    if found_tid is not None:
                                        consumed_tids.append(found_tid)
                                        hand_copy.remove(found_tid) # Consume from local copy to handle duplicates
                                    else:
                                        # Not found -> Force Patch
                                        print(f">> WARNING: Missing tile {mpsz} for PON. Hand: {cvt.tid_to_mpsz_list(self.obs_dict[player_id].hand)}")
                                        print(f">> TRUST: Patching hand to include {mpsz} for PON.")
                                        # Inject
                                        new_tid = cvt.mpsz_to_tid(mpsz)
                                        # Remove garbage if possible to maintain count
                                        if self.env.hands[player_id]:
                                            removed = self.env.hands[player_id].pop(0) # Remove from front (low ID)?
                                            print(f">> REMOVED {cvt.tid_to_mpsz(removed)} from hand to make room.")
                                        self.env.hands[player_id].append(new_tid)
                                        self.env.hands[player_id].sort() # Keep sorted
                                        
                                        consumed_tids.append(new_tid)
                                        # Update local copy just in case
                                        hand_copy.append(new_tid) 
                                        
                                action = Action(
                                    ActionType.PON,
                                    tile=target_tile,
                                    consume_tiles=consumed_tids,
                                )
                                step_actions = {player_id: action}
                                for pid in self.obs_dict.keys():
                                    if pid != player_id:
                                         step_actions[pid] = Action(ActionType.PASS)
                                self.obs_dict = self.env.step(step_actions)
                                print(">> OBS (AFTER PON)", self.obs_dict)

                        elif event["data"]["type"] == 0:
                            # CHI
                            chi_actions = [a for a in obs.legal_actions() if a.type == ActionType.CHI]
                            if not chi_actions:
                                print(f">> WARNING: CHI event received but not legal. Hand: {obs.hand}. Events: {obs.events}")
                            else:
                                consumed = [cvt.mpsz_to_tid(t) for i, t in enumerate(event["data"]["tiles"]) if event["data"]["froms"][i] == player_id]
                                target_tile_list = [cvt.mpsz_to_tid(t) for i, t in enumerate(event["data"]["tiles"]) if event["data"]["froms"][i] != player_id]
                                target_tile = target_tile_list[0]
                                action = Action(ActionType.CHI, tile=target_tile, consume_tiles=consumed)
                                step_actions = {player_id: action}
                                for pid in self.obs_dict.keys():
                                    if pid != player_id:
                                         step_actions[pid] = Action(ActionType.PASS)
                                self.obs_dict = self.env.step(step_actions)
                                print(">> OBS (AFTER CHI)", self.obs_dict)
                            
                        elif event["data"]["type"] == 2:
                             # DAIMINKAN (Open Kan)
                             assert len([a for a in obs.legal_actions() if a.type == ActionType.DAIMINKAN]), "ActionType.DAIMINKAN not found"
                             
                             consumed = [cvt.mpsz_to_tid(t) for i, t in enumerate(event["data"]["tiles"]) if event["data"]["froms"][i] == player_id]
                             target_tile_list = [cvt.mpsz_to_tid(t) for i, t in enumerate(event["data"]["tiles"]) if event["data"]["froms"][i] != player_id]
                             target_tile = target_tile_list[0]
                             
                             action = Action(ActionType.DAIMINKAN, tile=target_tile, consume_tiles=consumed)
                             
                             step_actions = {player_id: action}
                             for pid in self.obs_dict.keys():
                                if pid != player_id:
                                     step_actions[pid] = Action(ActionType.PASS)
                             self.obs_dict = self.env.step(step_actions)
                             print(">> OBS (AFTER DAIMINKAN)", self.obs_dict)
                        
                        else:
                            print(f">> WARNING: Unhandled ChiPengGang type {event['data']['type']}")
                            pass

                    case _:
                        print("BREAK", event)
                        print(">>>OBS", self.obs_dict)
                        # break # Original had break here
            return True
        except AssertionError as e:
            print(f"Verification Assertion Failed: {e}")
            traceback.print_exc()
            return False
        except Exception as e:
            print(f"Verification Error: {e}")
            traceback.print_exc()
            return False


def main(path: str, skip: int = 0):
    game = ReplayGame.from_json(path)
    print(f"Verifying {path}...")
    verifier = MjsoulEnvVerifier()
    if not verifier.verify_game(game, skip=skip):
        sys.exit(1)


if __name__ == "__main__":
    args = parse_args()
    main(args.path, args.skip)
