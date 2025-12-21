import riichienv as rv


def test_agari_calc_from_text():
    hand = rv.AgariCalculator.hand_from_text("123m456p789s111z2z")
    win_tile = rv.parse_tile("2z")

    # Default: Oya (East), Ron Agari
    res = hand.calc(win_tile, conditions=rv.Conditions())
    assert res.agari
    assert res.han == 2
    assert res.fu == 40
    assert res.tsumo_agari_oya == 0
    assert res.tsumo_agari_ko == 0
    assert res.ron_agari == 3900

    # Ko (South)
    res = hand.calc(win_tile, conditions=rv.Conditions(tsumo=True, player_wind=rv.SOUTH))
    assert res.agari
    assert res.han == 2
    assert res.fu == 40
    assert res.tsumo_agari_oya == 1300
    assert res.tsumo_agari_ko == 700
    assert res.ron_agari == 0

    # Oya (East)
    res = hand.calc(win_tile, conditions=rv.Conditions(tsumo=True, player_wind=rv.EAST))
    assert res.agari
    assert res.han == 3
    assert res.fu == 40
    assert res.tsumo_agari_oya == 0
    assert res.tsumo_agari_ko == 2600
    assert res.ron_agari == 0

    # Ron (East)
    res = hand.calc(win_tile, conditions=rv.Conditions(tsumo=False, player_wind=rv.EAST))
    assert res.agari
    assert res.han == 2
    assert res.fu == 40
    assert res.tsumo_agari_oya == 0
    assert res.tsumo_agari_ko == 0
    assert res.ron_agari == 3900

    # Ko (West)
    res = hand.calc(win_tile, conditions=rv.Conditions(tsumo=True, player_wind=rv.WEST))
    assert res.agari
    assert res.han == 2
    assert res.fu == 40
    assert res.tsumo_agari_oya == 1300
    assert res.tsumo_agari_ko == 700
    assert res.ron_agari == 0

    # Ko (North)
    res = hand.calc(win_tile, conditions=rv.Conditions(tsumo=True, player_wind=rv.NORTH))
    assert res.agari
    assert res.han == 2
    assert res.fu == 40
    assert res.tsumo_agari_oya == 1300
    assert res.tsumo_agari_ko == 700
    assert res.ron_agari == 0