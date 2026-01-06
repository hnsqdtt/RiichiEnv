from riichienv import Action, ActionType, Phase, RiichiEnv


def test_riichi_no_claim():
    env = RiichiEnv(seed=42)
    env.reset()

    # P0 in Riichi
    # P0 in Riichi
    pid = 0
    rd = env.riichi_declared
    rd[pid] = True
    env.riichi_declared = rd

    # Give P0 a pair of 1m (tid 0, 1) to enable potential Pon
    # And 2m, 3m for potential Chi? (Chi only from left player)
    hands = env.hands
    hands[0] = [0, 1, 4, 5, 8] + [20] * 8  # 1m, 1m, 2m, 2m, 3m...
    env.hands = hands

    # P3 discards 1m (tid 2) -> P0 could Pon
    # P0 is next to P3? No, P3->P0. So P0 can also Chi from P3.
    # P3 discards 3m (tid 11) -> P0 could Chi (1m, 2m + 3m)

    hands = env.hands
    hands[3] = [0] * 12 + [2]  # P3 has 1m (tid 2)
    env.hands = hands
    env.current_player = 3

    # Execute discard 1m from P3
    # P0 has pair of 1m. Normal P0 could Pon.
    # But P0 is Riichi. Should not offer Pon.

    # Ensure no Ron (P0 not Tenpai or 1m not Agari)

    # Mock _get_ron_potential to return empty just to be safe strictly about Claims?
    # Or just rely on hands not being Tenpai.

    obs = env.step({env.current_player: Action(ActionType.Discard, 2)})

    # Check legal actions for P0
    # If P0 is active:
    # - If WaitResponse: Only RON allowed.
    # - If WaitAct: Means claim was skipped. Success.

    if 0 in obs:
        if env.phase == Phase.WaitResponse:
            actions = obs[0].legal_actions()
            types = [a.action_type for a in actions]
            assert ActionType.PON not in types
            assert ActionType.CHI not in types
            assert ActionType.DAIMINKAN not in types
            # Must strictly contain only RON and PASS (pass on ron)
            for t in types:
                assert t in [ActionType.RON, ActionType.PASS]
        elif env.phase == Phase.WaitAct:
            # Success: Turned into P0's turn implies PON/CHI opportunity was skipped
            assert env.current_player == 0

    # Test Chi
    # P3 discards 3m (tid 11). P0 has 1m(0), 2m(4). -> Chi possible.
    env.current_player = 3
    hands = env.hands
    hands[3] = [0] * 12 + [11]
    env.hands = hands
    obs = env.step({env.current_player: Action(ActionType.Discard, 11)})

    if 0 in obs:
        if env.phase == Phase.WaitResponse:
            actions = obs[0].legal_actions()
            types = [a.action_type for a in actions]
            assert ActionType.CHI not in types
        elif env.phase == Phase.WaitAct:
            assert env.current_player == 0


def test_pon_available_without_riichi():
    env = RiichiEnv(seed=42)
    env.reset()
    # No Riichi
    hands = env.hands
    hands[0] = [0, 1, 4, 5, 8] + [20] * 8
    hands[3] = [0] * 12 + [2]  # 1m
    env.hands = hands
    env.current_player = 3

    obs = env.step({env.current_player: Action(ActionType.Discard, 2)})

    # Should get WaitResponse with PON
    assert env.phase == Phase.WaitResponse
    assert 0 in obs
    types = [a.action_type for a in obs[0].legal_actions()]
    assert ActionType.PON in types
