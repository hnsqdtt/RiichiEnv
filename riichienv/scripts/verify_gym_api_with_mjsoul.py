from typing import Any

import riichienv.convert as cvt
from riichienv.action import ActionType, Action
from riichienv.env import Phase
from riichienv import ReplayGame, RiichiEnv, AgariCalculator, Conditions


def main():
    path = "data/game_record_4p_jad_2025-12-14_out/251214-00159f57-b78b-454f-852f-f95a017ce00d.json.gz"
    game = ReplayGame.from_json(path)
    for kyoku in list(game.take_kyokus())[4:]:
        events = kyoku.events()
        env_wall = []
        tid_count = {}
        for event in events:
            if event["name"] == "DealTile":
                tid = cvt.mpsz_to_tid(event["data"]["tile"])
                cnt = 0
                if tid in tid_count:
                    cnt = tid_count[tid]
                    tid_count[tid] += 1
                else:
                    tid_count[tid] = 1
                tid = tid + cnt
                env_wall.append(tid)
        env_wall = list(reversed(env_wall))

        print(events)
        print("-" * 80)
        env = RiichiEnv()
        obs = dict[int, Any] | None
        for event in events:
            match event["name"]:
                case "NewRound":
                    data = event["data"]
                    print(data)
                    dora_indicators = [cvt.mpsz_to_tid(t) for t in data["doras"]]
                    env = RiichiEnv()
                    env.reset()
                    env.mjai_log = [
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
                        env.hands[player_id] = cvt.mpsz_to_tid_list(data[f"tiles{player_id}"][:13])
                    
                    first_actor = data["ju"]
                    raw_first_tile = data["tiles{}".format(first_actor)][13]
                    first_tile = cvt.mpsz_to_mjai(raw_first_tile)
                    env.mjai_log.append({
                        "type": "tsumo",
                        "actor": first_actor,
                        "tile": first_tile,
                    })
                    env.drawn_tile = cvt.mpsz_to_tid(raw_first_tile)
                    env.current_player = first_actor
                    env.active_players = [first_actor]
                    env.wall = env_wall
                    obs_dict = env._get_observations([first_actor])

                case "DiscardTile":
                    # print(">> OBS", obs_dict)
                    # print("--")
                    print(">> EVENT", event)
                    while env.phase != Phase.WAIT_ACT:
                        # Skip action
                        obs_dict = env.step({skip_player_id: Action(ActionType.PASS) for skip_player_id in obs_dict.keys()})

                    # print(">> OBS (AFTER SKIP WAIT_ACT PHASE)", obs_dict)

                    player_id = event["data"]["seat"]
                    candidate_tiles = set([cvt.tid_to_mpsz(a.tile) for a in obs_dict[player_id].legal_actions() if a.type == ActionType.DISCARD])
                    assert player_id == event["data"]["seat"]
                    assert event["data"]["tile"] in candidate_tiles
                    if event["data"]["is_liqi"]:
                        # Riichi declaration
                        print(cvt.tid_to_mpsz_list(obs_dict[player_id].hand))
                        matched_actions = [a for a in obs_dict[player_id].legal_actions() if a.type == ActionType.RIICHI]
                        assert len(matched_actions) == 1, "ActionType.RIICHI not found"
                        action = matched_actions[0]
                        obs_dict = env.step({player_id: action})

                    # Normal discard
                    action = [a for a in obs_dict[player_id].legal_actions() if a.type == ActionType.DISCARD and cvt.tid_to_mpsz(a.tile) == event["data"]["tile"]][0]
                    obs_dict = env.step({player_id: action})

                case "DealTile":
                    pass
                case "LiuJu":
                    print(">> LIUJU", event)
                    # Often happens on current_player's turn if Kyuhsu Kyuhai
                    obs_dict = env._get_observations(env.active_players)
                    for pid, obs in obs_dict.items():
                         print(f">> legal_actions() {pid} {obs.legal_actions()}")
                         
                         # Check for KYUSHU_KYUHAI
                         kyushu_actions = [a for a in obs.legal_actions() if a.type == ActionType.KYUSHU_KYUHAI]
                         if kyushu_actions:
                             print(f">> Player {pid} has KYUSHU_KYUHAI")
                             # Execute it
                             obs_dict = env.step({pid: kyushu_actions[0]})
                             print(f">> Executed KYUSHU_KYUHAI. Done: {env.done()}")
                             break
                    
                case "NoTile":
                    player_id = event["data"]["seat"]
                    print(event)

                case "Hule":
                    # ...
                    active_players = obs_dict.keys()
                    assert env.phase == Phase.WAIT_RESPONSE
                    for hule in event["data"]["hules"]:
                        player_id = hule["seat"]
                        assert player_id in active_players
                        assert obs_dict[player_id]
                        obs = obs_dict[player_id]
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
                        # env.mjai_log[1] is start_kyoku.
                        # We can extract bakaze/oya from there if needed, or from NewRound data.
                        # data["doras"] ...
                        # But env.mjai_log[1] has "bakaze": "E", "oya": 0
                        start_kyoku = env.mjai_log[1]
                        
                        # bakaze: E=0, S=1, W=2, N=3
                        bakaze_str = start_kyoku["bakaze"]
                        bakaze_map = {"E": 0, "S": 1, "W": 2, "N": 3}
                        round_wind = bakaze_map.get(bakaze_str, 0)
                        
                        oya = start_kyoku["oya"]
                        # player_wind: (seat - oya + 4) % 4
                        player_wind_val = (player_id - oya + 4) % 4
                        
                        calc = AgariCalculator(obs.hand).calc(
                            action.tile, 
                            dora_indicators=dora_indicators,
                            ura_indicators=ura_indicators,
                            conditions=Conditions(
                                tsumo=False,
                                riichi=env.riichi_declared[player_id],
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
                        assert calc.agari
                        assert calc.ron_agari == hule["point_rong"]
                        assert calc.han == hule["count"]
                        assert calc.fu == hule["fu"]
                        print(">> AGARI", calc)
                        print("SIMULATOR", env.mjai_log[1])
                        print("ACTUAL", events[0], events[-1])

                case "ChiPengGang":
                    print(">> OBS", obs_dict)
                    print("--")
                    print(">> EVENT", event)
                    player_id = event["data"]["seat"]
                    assert player_id in obs_dict
                    obs = obs_dict[player_id]
                    if event["data"]["type"] == 1:
                        # PON
                        assert len([a for a in obs.legal_actions() if a.type == ActionType.PON])
                        action = Action(
                            ActionType.PON,
                            tile=[cvt.mpsz_to_tid(t) for i, t in enumerate(event["data"]["tiles"]) if event["data"]["froms"][i] != player_id][0],
                            consume_tiles=[cvt.mpsz_to_tid(t) for i, t in enumerate(event["data"]["tiles"]) if event["data"]["froms"][i] == player_id],
                        )
                        obs_dict = env.step({player_id: action})
                        print(">> OBS (AFTER PON)", obs_dict)
                    else:
                        print("BREAK", event)
                        print(">>>OBS", obs_dict)

                case _:
                    print("BREAK", event)
                    print(">>>OBS", obs_dict)
                    break

        break


if __name__ == "__main__":
    main()
