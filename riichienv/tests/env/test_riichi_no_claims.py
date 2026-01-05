from riichienv import Action, ActionType, Phase, RiichiEnv


def setup_env_with_wall():
    env = RiichiEnv()
    # Initialize wall with enough tiles to allow claims (> 14)
    env.wall = list(range(136))
    return env


def test_no_chi_during_riichi():
    env = setup_env_with_wall()
    h2 = [76, 80, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44]
    env.hands = [[0] * 13, [0] * 13, h2, [0] * 13]

    rd = [False, False, True, False]
    env.riichi_declared = rd

    env.phase = Phase.WaitAct
    env.current_player = 1
    env.drawn_tile = 72  # 1s
    env.needs_tsumo = False

    action = Action(ActionType.Discard, 72, [])
    obs_dict = env.step({1: action})

    assert 2 in obs_dict, "Player 2 should be active (Draw/Tsumo) but with NO claims offered"
    obs2 = obs_dict[2]
    actions = obs2.legal_actions()

    chi_actions = [a for a in actions if a.type == ActionType.Chi]
    pon_actions = [a for a in actions if a.type == ActionType.Pon]

    assert len(chi_actions) == 0, f"Chi should NOT be offered during Riichi! Offered: {chi_actions}"
    assert len(pon_actions) == 0, f"Pon should NOT be offered during Riichi! Offered: {pon_actions}"


def test_chi_offered_when_not_in_riichi():
    env = setup_env_with_wall()
    h2 = [76, 80, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44]
    env.hands = [[0] * 13, [0] * 13, h2, [0] * 13]

    env.riichi_declared = [False, False, False, False]

    env.phase = Phase.WaitAct
    env.current_player = 1
    env.drawn_tile = 72  # 1s
    env.needs_tsumo = False

    action = Action(ActionType.Discard, 72, [])
    obs_dict = env.step({1: action})

    assert 2 in obs_dict, f"Player 2 should be in active players when NOT in Riichi, but obs_dict was {obs_dict.keys()}"
    obs2 = obs_dict[2]
    actions = obs2.legal_actions()

    # Debug prints to confirm property names
    if len(actions) > 0:
        print(f"DEBUG: dir(actions[0])={dir(actions[0])}")
        print(f"DEBUG: actions[0].type={actions[0].type}")

    chi_actions = [a for a in actions if a.type == ActionType.Chi]
    assert len(chi_actions) > 0, "Player 2 should have Chi actions when NOT in Riichi"


def test_no_pon_during_riichi():
    env = setup_env_with_wall()
    h2 = [76, 77, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44]
    env.hands = [[0] * 13, [0] * 13, h2, [0] * 13]

    rd = [False, False, True, False]
    env.riichi_declared = rd

    env.phase = Phase.WaitAct
    env.current_player = 1
    env.drawn_tile = 78  # 2s (76, 77, 78, 79 are all 2s)
    env.needs_tsumo = False

    action = Action(ActionType.Discard, 78, [])
    obs_dict = env.step({1: action})

    assert 2 in obs_dict, "Player 2 should be active (Draw/Tsumo) but with NO claims offered"
    obs2 = obs_dict[2]
    actions = obs2.legal_actions()

    chi_actions = [a for a in actions if a.type == ActionType.Chi]
    pon_actions = [a for a in actions if a.type == ActionType.Pon]

    assert len(chi_actions) == 0, f"Chi should NOT be offered during Riichi! Offered: {chi_actions}"
    assert len(pon_actions) == 0, f"Pon should NOT be offered during Riichi! Offered: {pon_actions}"
