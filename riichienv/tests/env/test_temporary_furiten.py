from riichienv import Action, ActionType, AgariCalculator, Conditions, GameType, Meld, MeldType, Phase, RiichiEnv


def test_temporary_furiten_no_yaku():
    """
    Test that a player who has a winning shape (Agari=True) but lacks Yaku
    is still placed in Temporary Furiten (Doujun Furiten) if they skip the win.
    """
    env = RiichiEnv(game_type=GameType.YON_HANCHAN)
    # Use West round so East player wind != round wind (if needed, but here Oya=0 -> East)
    env.reset(bakaze=0, oya=0, honba=0, kyotaku=0)
    # env.reset() sets defaults. Overwrite if needed.
    # round_wind is read-only, set via bakaze in reset.

    # Needs explicit initialization of other fields if reset() doesn't do them exactly as _initialize_round did
    # for the test?
    # reset() handles basic init.

    # Player 1 setup
    pid = 1
    # Hand: 23m, 678m, 33z (West) -> No Yaku
    # Melds: 123p (Chi), 123s (Chi)
    # Tenpai for 1m, 4m.
    # 4m gives NO Yaku (No Tanyao due to 123 melds/terminals, No Yakuhai West pairs).
    # 1m gives Sanshoku (123m, 123p, 123s).

    # Tile IDs:
    # 2m=4, 3m=8
    # 6m=20, 7m=24, 8m=28
    # 3z=116, 117 (West)
    hand = [4, 8, 20, 24, 28, 116, 117]

    # Meld 1: Chi 123p (Open) -> 1p=36, 2p=40, 3p=44
    m1 = Meld(MeldType.Chi, [36, 40, 44], True)
    # Meld 2: Chi 123s (Open) -> 1s=72, 2s=76, 3s=80
    m2 = Meld(MeldType.Chi, [72, 76, 80], True)

    # PyO3 get/set returns copies. Must write back.
    hands = env.hands
    hands[pid] = hand

    melds = env.melds
    melds[pid] = [m1, m2]

    # Step 1: P2 discards 4m (Tile ID 12)
    hands[2] = [12]  # Ensure P2 has the tile to discard
    env.hands = hands
    env.melds = melds

    # Ensure no permanent Furiten
    discards = env.discards
    discards[pid] = []
    env.discards = discards
    # Agari check: 4m completes 23m -> 234m. Hand is complete.
    # But Yaku?
    # AgariCalculator will return agari=True (shape valid) but Yakus might be empty or restricted.
    # Actually, AgariCalculator enforces 1-han in its `agari` boolean property for non-Yakuman.
    # So if Han=0, calc.agari is False.
    # BUT, if calc.agari is False, `_get_ron_potential` would see False and NOT set furiten?
    # Wait. If Yaku Shibari fails, AgariCalculator.agari is False?
    # Let's check AgariCalculator again.
    # Yes, `agari: (has_yaku || yaku_res.yakuman_count > 0) && yaku_res.han >= 1`.
    # So if Han=0 (no Yaku), agari is False.
    #
    # However, if Dora is present (Han > 0) but No Yaku (Yaku Shibari), then Agari=False?
    # The fix implies we must detect "Shape Valid but Yaku Invalid".
    # AgariCalculator generally returns `agari=False` if Yaku Shibari fails.
    # We might need to inspect `yaku_res` internals or `calc` returns enough info?
    # The `res` struct has `agari` bool. If False, we stop.
    #
    # Wait, the bug report says "Probable Furiten".
    # If the hand has shape but no Yaku, is it Furiten? Yes.
    # Does AgariCalculator support checking "Shape only"?
    # Currently `calc` returns `Agari` struct.
    # We might need to check Tsumo/Ron potential without Yaku Shibari?
    # Or, does `RiichiEnv` manually check `han < 1`?
    # Looking at `_get_ron_potential`:
    # `if calc.agari:` -> Then checks `han < 1`.
    # If `calc.agari` is ALREADY False because of Yaku Shibari, then `_get_ron_potential` skips it entirely.
    # So Yaku Shibari must be enforced inside `AgariCalculator`.
    #
    # If `AgariCalculator` returns False for `agari`, `RiichiEnv` thinks "Not a win".
    # If "Not a win", then NO Furiten logic triggers.
    # BUT "Not a win due to Yaku Shibari" SHOULD trigger Furiten.
    # So AgariCalculator needs to distinguish "Invalid Shape" vs "No Yaku".
    # Or we rely on the fact that if we have 1 Han (Dora) but No Yaku,
    # `calc.agari` might be True/False depending on implementation.
    #
    # In this specific test case: P1 has 4m win.
    # Does P1 have Dora? If No Dora -> Han=0.
    # If Han=0, `calc.agari` should be False.
    #
    # We need to give P1 a Dora to make Han >= 1, but NO Yaku.
    # Let's make 8m a Dora. (28 is 8m).
    env.dora_indicators = [24]  # 7m -> 8m is Dora.
    env.needs_tsumo = False  # Force no draw, we are manually in WaitAct

    discard_tile = 12  # 4m
    env.current_player = 2
    env.phase = Phase.WaitAct
    env.active_players = [2]

    # Verify setup via calculator
    calc = AgariCalculator(env.hands[pid], env.melds[pid])
    calc.calc(discard_tile, dora_indicators=env.dora_indicators, conditions=Conditions(tsumo=False))
    # With Dora, Han should be >= 1. But No Yaku.
    # Yaku Shibari requires `has_yaku`.
    # If `AgariCalculator` sets `agari = (has_yaku ...) && han >= 1`.
    # Then `res.agari` will be False.
    #
    # If `res.agari` is False, `_get_ron_potential` skips line 1201.
    # And my fix logic was inserted inside line 1202 (`if calc.agari:`).
    #
    # If `res.agari` is False, my fix WON'T WORK.
    # I verified in reproduction script that `res.agari` was True?
    # "Agari Result on 4m: Agari=True, Han=1, Yaku=[31]" (from previous step 1109 log)
    #
    # Ah! In step 1109, I had NOT set Dora indicators in the script explicitly?
    # Default wall shuffle -> random dora.
    # Wait, in the logs: Yaku=[31]. 31 is DORA.
    # So Random Dora happened to hit? Or `reproduction_furiten.py` didn't set/clear doras?
    # It called `_initialize_round` with defaults.
    #
    # If `res.agari` is TRUE even with ONLY Dora...
    # Then `AgariCalculator` is NOT enforcing Yaku Shibari in its `agari` flag?
    # Let's check `agari_calculator.rs` or `env.py` logic.
    #
    # If `res.agari` is True, my fix logic at line 1202 triggers.
    # `if not calc.yakuman:` -> `non_dora_yaku = ...` -> `if calc.han < 1 or not non_dora_yaku:`
    # This block handles Yaku Shibari ENFORCEMENT in Env.
    # So Env effectively re-checks Yaku Shibari.
    # This confirms my fix location is correct IF `res.agari` is True for Dora-only hands.
    #
    # So for this test, I MUST ensure P1 has a Dora so `res.agari` is True (due to Han>=1),
    # but `non_dora_yaku` is empty.
    # Using 8m as Dora (Indicator 7m=24) is good.

    # Execute Discard Action via Step
    obs = env.step({2: Action(ActionType.DISCARD, tile=discard_tile)})

    # P1 should have NO option to Ron (filtered by Yaku Shibari check in _get_ron_potential)
    p1_acts = []
    if pid in obs:
        p1_acts = [a for a in obs[pid].legal_actions() if a.type == ActionType.RON]
    assert not p1_acts, "P1 should NOT act on 4m (No Yaku)"

    # Important: Did `missed_agari_doujun` get set?
    assert env.missed_agari_doujun[pid], "P1 must generally miss agari (doujun furiten)"

    # Step 2: Next discard 1m (Tile 0) from P3
    # 1m gives Sanshoku. Agari=True, Han>=1 (Sanshoku + Dora).
    # But because of Furiten, P1 cannot Ron.
    env.current_player = 3
    env.active_players = [3]
    discard_tile_2 = 0  # 1m

    # Step directly
    obs = env.step({3: Action(ActionType.DISCARD, tile=discard_tile_2)})

    p1_acts_2 = []
    if pid in obs:
        p1_acts_2 = [a for a in obs[pid].legal_actions() if a.type == ActionType.RON]

    assert not p1_acts_2, "P1 should NOT be able to Ron on 1m due to Temporary Furiten"


if __name__ == "__main__":
    test_temporary_furiten_no_yaku()
