from riichienv import Action, ActionType, Meld, MeldType, Phase, RiichiEnv


def test_chankan_stale_claims_repro():
    """
    Reproduce Match 27 Step 267 inconsistency.
    P2 discards 7p (60) -> P0 has Pon offer with 61, 62.
    All pass.
    P3 tsutmos 6p (59), kakans 59. (P3 has Pon meld 56, 57, 58).
    P0 has 6p sequence wait (4p-5p).
    P0 should have Ron (Chankan) offer on 59.
    """
    env = RiichiEnv()
    env.reset()

    # 4p: 48, 49, 50, 51
    # 5p: 52, 53, 54, 55
    # 6p: 56, 57, 58, 59
    # 7p: 60, 61, 62, 63

    # P0 Hand: 13 tiles. (Tanyao)
    # 222m: 4, 5, 6
    # 333m: 8, 9, 10
    # 444m: 12, 13, 14
    # 77p: 61, 62 (Wait on 60,63 but furiten)
    # 4p-5p: 49, 53 (Wait on 3p=44-47 or 6p=56-59)
    # Total: 3+3+3+2+2 = 13 tiles.
    hands = env.hands
    hands[0] = [4, 5, 6, 8, 9, 10, 12, 13, 14, 61, 62, 49, 53]
    env.hands = hands

    # P3 has 6p Pon. 6p: 56, 57, 58, 59.
    melds = env.melds
    melds[3] = [Meld(MeldType.Peng, [56, 57, 58], True)]
    env.melds = melds

    # P0 furiten for 7p (60)
    discards = env.discards
    discards[0] = [60]
    env.discards = discards

    # 1. P2 discards 7p (63). (P0 has 61, 62).
    # Wait, P2 discard 7p (63). P0 (61, 62) should have Pon.
    env.current_player = 2
    env.phase = Phase.WaitAct
    obs = env.step({2: Action(ActionType.Discard, 63)})
    assert 0 in obs
    print("Step 1: P0 has Pon offer on 7p")

    # 2. All pass.
    env.step({0: Action(ActionType.PASS), 1: Action(ActionType.PASS), 3: Action(ActionType.PASS)})
    assert env.current_player == 3
    print("Step 2: All passed, now P3 turn")

    # 3. P3 draws 6p (59) and kakans.
    env.drawn_tile = 59
    h3 = env.hands
    h3[3] = [59]
    env.hands = h3

    obs = env.step({3: Action(ActionType.Kakan, 59, [56, 57, 58])})

    assert 0 in obs, f"P0 should be active for Chankan. Phase: {env.phase}, Active: {env.active_players}"
    action_types = [a.action_type for a in obs[0].legal_actions()]
    print(f"P0 legal actions: {action_types}")

    assert ActionType.Ron in action_types, f"P0 should have Ron offered. Actions: {action_types}"
    assert ActionType.Pon not in action_types, f"P0 should NOT have stale Pon offered. Actions: {action_types}"


if __name__ == "__main__":
    test_chankan_stale_claims_repro()
