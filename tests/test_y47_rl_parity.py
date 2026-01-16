import numpy as np
import pytest

import riichienv
from riichienv import ActionType, Phase


NUM_PLAYERS = 4

MAX_STATE_TOKENS = 256
MAX_ACTIONS = 128
MAX_CONSUME_TILES = 4

TOKEN_MAIN_DIM = 7
TOK_TYPE = 0
TOK_SEAT = 1
TOK_POS = 2
TOK_POS2 = 3
TOK_TILE = 4
TOK_AUX1 = 5
TOK_AUX2 = 6

TOK_CLS = 0
TOK_ROUND = 1
TOK_SCORE = 2
TOK_DORA = 3
TOK_DRAWN = 4
TOK_HAND = 5
TOK_MELD_TILE = 6
TOK_RIVER = 7

ACTION_MAIN_DIM = 6
ACT_KIND = 0
ACT_TILE = 1
ACT_FROM = 2
ACT_CONSUME_LEN = 3
ACT_HAS_TILE = 4
ACT_HAS_FROM = 5

ACT_DISCARD = 0
ACT_CHI = 1
ACT_PON = 2
ACT_DAIMINKAN = 3
ACT_ANKAN = 4
ACT_KAKAN = 5
ACT_RIICHI = 6
ACT_RON = 7
ACT_TSUMO = 8
ACT_PASS = 9
ACT_KYUSHU_KYUHAI = 10

MAX_HAND_TIDS = 14
MAX_RIVER = 30
MAX_MELDS = 4
MAX_MELD_TILES = 4
MAX_DORA = 5

TID_NONE = 136
NUM_TIDS = 137

RIVER_FLAG_TSUMOGIRI = 1 << 0
RIVER_FLAG_RIICHI_TILE = 1 << 1
NUM_RIVER_FLAGS = 4

RANK_REWARDS = np.asarray([0.9, 0.45, 0.0, -1.35], dtype=np.float32)


def _abs_to_rel(p_abs: int, me: int) -> int:
    return int((int(p_abs) - int(me)) % NUM_PLAYERS)


def _validate_real_tid(tid: int) -> int:
    tid_i = int(tid)
    if tid_i < 0 or tid_i >= (NUM_TIDS - 1):
        raise ValueError(f"TID out of range: {tid_i}")
    return tid_i


def _maybe_tid(tid: int | None) -> int:
    if tid is None:
        return TID_NONE
    return _validate_real_tid(tid)


def _action_kind(action: object) -> int:
    a_type = getattr(action, "action_type", None)
    if a_type is None:
        raise TypeError("action.action_type missing")
    if a_type == ActionType.DISCARD:
        return ACT_DISCARD
    if a_type == ActionType.CHI:
        return ACT_CHI
    if a_type == ActionType.PON:
        return ACT_PON
    if a_type == ActionType.DAIMINKAN:
        return ACT_DAIMINKAN
    if a_type == ActionType.ANKAN:
        return ACT_ANKAN
    if a_type == ActionType.KAKAN:
        return ACT_KAKAN
    if a_type == ActionType.RIICHI:
        return ACT_RIICHI
    if a_type == ActionType.RON:
        return ACT_RON
    if a_type == ActionType.TSUMO:
        return ACT_TSUMO
    if a_type == ActionType.PASS:
        return ACT_PASS
    if a_type == ActionType.KYUSHU_KYUHAI:
        return ACT_KYUSHU_KYUHAI
    raise ValueError(f"unsupported ActionType: {a_type!r}")


def _pending_kan_actor_abs(env: object) -> int | None:
    pk = getattr(env, "pending_kan", None)
    if pk is None:
        return None
    if isinstance(pk, tuple) and pk:
        return int(pk[0])
    if isinstance(pk, int):
        return int(pk)
    return None


class _PublicRiver:
    def __init__(self) -> None:
        self._river_raw_tids_abs: list[list[int]] = [[] for _ in range(NUM_PLAYERS)]
        self._river_flags_abs: list[list[int]] = [[] for _ in range(NUM_PLAYERS)]
        self._pending_riichi_abs: list[bool] = [False for _ in range(NUM_PLAYERS)]

    def reset(self) -> None:
        self._river_raw_tids_abs = [[] for _ in range(NUM_PLAYERS)]
        self._river_flags_abs = [[] for _ in range(NUM_PLAYERS)]
        self._pending_riichi_abs = [False for _ in range(NUM_PLAYERS)]

    def set_pending_riichi(self, pid_abs: int) -> None:
        self._pending_riichi_abs[int(pid_abs)] = True

    def record_discard_post_step(
        self,
        *,
        env: object,
        actor_abs: int,
        discard_raw: int,
        is_tsumogiri: bool,
    ) -> None:
        last_discard = getattr(env, "last_discard", None)
        if last_discard is None:
            raise RuntimeError("env.last_discard missing after Discard step")
        if int(last_discard[0]) != int(actor_abs) or int(last_discard[1]) != int(discard_raw):
            raise RuntimeError(
                f"env.last_discard mismatch: expected ({actor_abs},{discard_raw}), got {last_discard}"
            )

        river = self._river_raw_tids_abs[int(actor_abs)]
        flags_list = self._river_flags_abs[int(actor_abs)]
        if len(river) != len(flags_list):
            raise RuntimeError("internal error: river/flags length mismatch")
        if len(river) >= MAX_RIVER:
            raise RuntimeError(f"river length overflow: {len(river)} >= MAX_RIVER={MAX_RIVER}")

        flags = 0
        if bool(is_tsumogiri):
            flags |= RIVER_FLAG_TSUMOGIRI
        if self._pending_riichi_abs[int(actor_abs)]:
            flags |= RIVER_FLAG_RIICHI_TILE
            self._pending_riichi_abs[int(actor_abs)] = False
        if flags < 0 or flags >= NUM_RIVER_FLAGS:
            raise RuntimeError(f"internal error: river flags out of range: {flags}")

        river.append(int(discard_raw))
        flags_list.append(int(flags))

    def check_consistency(self, *, env: object) -> None:
        discards = list(getattr(env, "discards"))
        if len(discards) != NUM_PLAYERS:
            raise RuntimeError("env.discards must have length 4")
        for p_abs in range(NUM_PLAYERS):
            env_river = [int(t) for t in list(discards[p_abs])]
            river = list(self._river_raw_tids_abs[p_abs])
            if env_river != river:
                raise RuntimeError(
                    f"river tracker mismatch for pid={p_abs}: env.discards={env_river}, tracker={river}"
                )


def _encode_observation(*, me: int, obs: object, env: object, river: _PublicRiver) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    token_main = np.zeros((MAX_STATE_TOKENS, TOKEN_MAIN_DIM), dtype=np.int64)
    token_scalar = np.zeros((MAX_STATE_TOKENS, 3), dtype=np.float32)
    token_mask = np.zeros((MAX_STATE_TOKENS,), dtype=np.bool_)

    river.check_consistency(env=env)

    cur = 0

    def push() -> int:
        nonlocal cur
        if cur >= MAX_STATE_TOKENS:
            raise ValueError(f"too many state tokens: {cur+1} > MAX_STATE_TOKENS={MAX_STATE_TOKENS}")
        idx = cur
        token_mask[idx] = True
        cur += 1
        return idx

    i = push()
    token_main[i, TOK_TYPE] = TOK_CLS
    token_main[i, TOK_TILE] = TID_NONE

    round_wind = int(getattr(env, "round_wind"))
    oya_abs = int(getattr(env, "oya"))
    honba = int(getattr(env, "honba"))
    kyotaku = int(getattr(env, "riichi_sticks"))
    kyoku_idx = int(getattr(env, "kyoku_idx", 0))

    i = push()
    token_main[i, TOK_TYPE] = TOK_ROUND
    token_main[i, TOK_TILE] = TID_NONE
    token_main[i, TOK_AUX1] = int(round_wind)
    token_main[i, TOK_AUX2] = int(_abs_to_rel(oya_abs, me))
    token_scalar[i, 0] = float(honba) / 20.0
    token_scalar[i, 1] = float(kyotaku) / 20.0
    token_scalar[i, 2] = float(kyoku_idx) / 16.0

    scores = list(getattr(env, "scores")())
    riichi_declared = list(getattr(env, "riichi_declared"))
    double_riichi_declared = list(getattr(env, "double_riichi_declared"))
    melds = list(getattr(env, "melds"))

    for p_abs in range(NUM_PLAYERS):
        p_rel = _abs_to_rel(p_abs, me)
        i = push()
        token_main[i, TOK_TYPE] = TOK_SCORE
        token_main[i, TOK_SEAT] = int(p_rel)
        token_main[i, TOK_TILE] = TID_NONE
        flags = 0
        if bool(riichi_declared[p_abs]):
            flags |= 1
        if bool(double_riichi_declared[p_abs]):
            flags |= 2
        token_main[i, TOK_AUX1] = int(flags)
        token_main[i, TOK_AUX2] = int(len(melds[p_abs]))
        token_scalar[i, 0] = (float(scores[p_abs]) - 25000.0) / 100000.0

    dora_indicators = list(getattr(env, "dora_indicators", []))
    for d_i, raw_tid in enumerate(dora_indicators[:MAX_DORA]):
        i = push()
        token_main[i, TOK_TYPE] = TOK_DORA
        token_main[i, TOK_TILE] = _validate_real_tid(int(raw_tid))
        token_main[i, TOK_AUX1] = int(d_i)

    drawn_tid = None
    if int(getattr(env, "current_player")) == int(me):
        drawn_tid = getattr(env, "drawn_tile", None)
    i = push()
    token_main[i, TOK_TYPE] = TOK_DRAWN
    token_main[i, TOK_TILE] = _maybe_tid(drawn_tid)

    hand_tids = [int(t) for t in list(getattr(obs, "hand", []))]
    if len(hand_tids) > MAX_HAND_TIDS:
        raise ValueError(f"obs.hand too long: {len(hand_tids)} > MAX_HAND_TIDS={MAX_HAND_TIDS}")
    hand_tids.sort()
    for raw_tid in hand_tids:
        i = push()
        token_main[i, TOK_TYPE] = TOK_HAND
        token_main[i, TOK_TILE] = _validate_real_tid(int(raw_tid))

    for p_abs in range(NUM_PLAYERS):
        p_rel = _abs_to_rel(p_abs, me)
        p_melds = list(melds[p_abs])
        if len(p_melds) > MAX_MELDS:
            raise ValueError(f"env.melds[{p_abs}] too long: {len(p_melds)} > MAX_MELDS={MAX_MELDS}")
        for meld_idx, m in enumerate(p_melds):
            kind = int(int(getattr(m, "meld_type")) + 1)
            opened = bool(getattr(m, "opened", False))
            tiles = [int(t) for t in list(getattr(m, "tiles", []))]
            if len(tiles) > MAX_MELD_TILES:
                raise ValueError(f"meld.tiles too long: {len(tiles)} > MAX_MELD_TILES={MAX_MELD_TILES}")
            for tile_slot, raw_tid in enumerate(tiles):
                i = push()
                token_main[i, TOK_TYPE] = TOK_MELD_TILE
                token_main[i, TOK_SEAT] = int(p_rel)
                token_main[i, TOK_POS] = int(meld_idx)
                token_main[i, TOK_POS2] = int(tile_slot)
                token_main[i, TOK_TILE] = _validate_real_tid(int(raw_tid))
                token_main[i, TOK_AUX1] = int(kind)
                token_main[i, TOK_AUX2] = 1 if opened else 0

    for p_abs in range(NUM_PLAYERS):
        p_rel = _abs_to_rel(p_abs, me)
        r_tids = river._river_raw_tids_abs[p_abs]
        r_flags = river._river_flags_abs[p_abs]
        if len(r_tids) != len(r_flags):
            raise RuntimeError("internal error: river tids/flags length mismatch")
        if len(r_tids) > MAX_RIVER:
            raise ValueError(f"river too long: {len(r_tids)} > MAX_RIVER={MAX_RIVER}")
        for ridx, (raw_tid, flags) in enumerate(zip(r_tids, r_flags)):
            if flags < 0 or flags >= NUM_RIVER_FLAGS:
                raise RuntimeError(f"internal error: river flags out of range: {flags}")
            i = push()
            token_main[i, TOK_TYPE] = TOK_RIVER
            token_main[i, TOK_SEAT] = int(p_rel)
            token_main[i, TOK_POS] = int(ridx)
            token_main[i, TOK_TILE] = _validate_real_tid(int(raw_tid))
            token_main[i, TOK_AUX1] = int(flags)

    return token_main, token_scalar, token_mask


def _encode_actions(*, me: int, actions: list[object], env: object) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[object]]:
    action_main = np.zeros((MAX_ACTIONS, ACTION_MAIN_DIM), dtype=np.int64)
    action_consume = np.full((MAX_ACTIONS, MAX_CONSUME_TILES), TID_NONE, dtype=np.int64)
    action_consume_mask = np.zeros((MAX_ACTIONS, MAX_CONSUME_TILES), dtype=np.bool_)
    legal = np.zeros((MAX_ACTIONS,), dtype=np.bool_)

    last_discard = getattr(env, "last_discard", None)
    last_from_abs = int(last_discard[0]) if last_discard is not None else None
    last_from_rel = _abs_to_rel(last_from_abs, me) if last_from_abs is not None else 0

    pending_kan_abs = _pending_kan_actor_abs(env)

    table: list[object] = []
    for a in actions:
        i = len(table)
        if i >= MAX_ACTIONS:
            raise ValueError(f"too many legal actions: {i+1} > MAX_ACTIONS={MAX_ACTIONS}")

        kind = _action_kind(a)

        raw_tile = getattr(a, "tile", None)
        if kind in {ACT_DISCARD, ACT_CHI, ACT_PON, ACT_DAIMINKAN, ACT_ANKAN, ACT_KAKAN}:
            if raw_tile is None:
                raise ValueError("action must have a tile")
            tid = _validate_real_tid(int(raw_tile))
            has_tile = 1
        else:
            tid = TID_NONE
            has_tile = 0

        consume_tiles = [int(t) for t in list(getattr(a, "consume_tiles", []))]
        if len(consume_tiles) > MAX_CONSUME_TILES:
            raise ValueError(f"consume_tiles too long: {len(consume_tiles)} > MAX_CONSUME_TILES={MAX_CONSUME_TILES}")

        action_main[i, ACT_KIND] = int(kind)
        action_main[i, ACT_TILE] = int(tid)
        action_main[i, ACT_HAS_TILE] = int(has_tile)
        action_main[i, ACT_CONSUME_LEN] = int(len(consume_tiles))

        if kind in {ACT_CHI, ACT_PON, ACT_DAIMINKAN} and last_from_abs is not None:
            action_main[i, ACT_FROM] = int(last_from_rel)
            action_main[i, ACT_HAS_FROM] = 1
        elif kind == ACT_RON:
            if last_from_abs is not None:
                action_main[i, ACT_FROM] = int(last_from_rel)
                action_main[i, ACT_HAS_FROM] = 1
            elif pending_kan_abs is not None:
                action_main[i, ACT_FROM] = int(_abs_to_rel(pending_kan_abs, me))
                action_main[i, ACT_HAS_FROM] = 1
            else:
                action_main[i, ACT_FROM] = 0
                action_main[i, ACT_HAS_FROM] = 0
        else:
            action_main[i, ACT_FROM] = 0
            action_main[i, ACT_HAS_FROM] = 0

        for j, t in enumerate(consume_tiles):
            action_consume[i, j] = _validate_real_tid(int(t))
            action_consume_mask[i, j] = True

        legal[i] = True
        table.append(a)

    if not table:
        raise ValueError("no legal actions")

    return action_main, action_consume, action_consume_mask, legal, table


def _advance_after_kyoku_end(env: object, obs_dict: dict[int, object], river: _PublicRiver) -> dict[int, object]:
    if obs_dict or bool(env.done()):
        return obs_dict

    if not bool(getattr(env, "needs_initialize_next_round", False)):
        raise RuntimeError("env returned empty obs_dict but needs_initialize_next_round=False")

    river.reset()

    for _ in range(64):
        obs_dict = env.step({})
        if obs_dict or bool(env.done()):
            return obs_dict
    raise RuntimeError("stuck while advancing to next kyoku (obs_dict stayed empty)")


def test_y47_rl_parity_smoke() -> None:
    seed = 123
    env_old = riichienv.RiichiEnv(game_mode="4p-red-half", seed=seed, skip_mjai_logging=True)
    env_new = riichienv.RiichiEnv(game_mode="4p-red-half", seed=seed, skip_mjai_logging=True)

    river = _PublicRiver()
    river.reset()

    obs_dict = env_old.reset(seed=seed)
    obs_dict = _advance_after_kyoku_end(env_old, obs_dict, river)
    turns_new = env_new.reset_y47(seed=seed)

    for _ in range(64):
        assert set(obs_dict.keys()) == set(turns_new.keys())

        action_index: dict[int, int] = {}
        pending_actions_old: dict[int, object] = {}

        for pid in sorted(obs_dict.keys()):
            obs = obs_dict[pid]
            token_main, token_scalar, token_mask = _encode_observation(me=pid, obs=obs, env=env_old, river=river)
            action_main, action_consume, action_consume_mask, legal_mask, table = _encode_actions(
                me=pid,
                actions=list(obs.legal_actions()),
                env=env_old,
            )

            t = turns_new[pid]
            assert np.array_equal(token_main, np.asarray(t.token_main))
            assert np.array_equal(token_scalar, np.asarray(t.token_scalar))
            assert np.array_equal(token_mask, np.asarray(t.token_mask))
            assert np.array_equal(action_main, np.asarray(t.action_main))
            assert np.array_equal(action_consume, np.asarray(t.action_consume))
            assert np.array_equal(action_consume_mask, np.asarray(t.action_consume_mask))
            assert np.array_equal(legal_mask, np.asarray(t.legal_action_mask))

            action_index[pid] = 0
            pending_actions_old[pid] = table[0]

        active_pids = sorted(obs_dict.keys())
        phase_kind = int(getattr(env_old, "phase", Phase.WaitAct))
        wait_act_discard_ctx: tuple[int, int, bool] | None = None
        wait_act_riichi_pid: int | None = None
        if int(phase_kind) == int(Phase.WaitAct):
            assert len(active_pids) == 1
            only_pid = active_pids[0]
            act = pending_actions_old[only_pid]
            if getattr(act, "action_type") == ActionType.DISCARD:
                discard_raw = int(getattr(act, "tile"))
                drawn_raw = getattr(env_old, "drawn_tile", None)
                is_tsumogiri = (drawn_raw is not None) and (int(drawn_raw) == discard_raw)
                wait_act_discard_ctx = (int(only_pid), int(discard_raw), bool(is_tsumogiri))
            elif getattr(act, "action_type") == ActionType.RIICHI:
                wait_act_riichi_pid = int(only_pid)

        obs_dict = env_old.step(pending_actions_old)
        if wait_act_discard_ctx is not None:
            actor_abs, discard_raw, is_tsumogiri = wait_act_discard_ctx
            river.record_discard_post_step(
                env=env_old,
                actor_abs=actor_abs,
                discard_raw=discard_raw,
                is_tsumogiri=is_tsumogiri,
            )
        if wait_act_riichi_pid is not None:
            river.set_pending_riichi(wait_act_riichi_pid)
        obs_dict = _advance_after_kyoku_end(env_old, obs_dict, river)

        turns_new, rewards_new, done_new = env_new.step_y47(action_index)
        assert bool(done_new) == bool(env_old.done())

        if bool(done_new):
            ranks = list(env_old.ranks())
            rewards_old = np.zeros((NUM_PLAYERS,), dtype=np.float32)
            for p in range(NUM_PLAYERS):
                r = int(ranks[p])
                assert 1 <= r <= NUM_PLAYERS
                rewards_old[p] = float(RANK_REWARDS[r - 1])
            assert np.array_equal(np.asarray(rewards_new, dtype=np.float32), rewards_old)
            break


def test_y47_step_strictness() -> None:
    env = riichienv.RiichiEnv(game_mode="4p-red-half", seed=0, skip_mjai_logging=True)
    with pytest.raises(RuntimeError):
        env.step_y47({})

    turns = env.reset_y47(seed=0)
    active = sorted(dict(turns).keys())
    assert active

    bad_missing = {int(active[0]): 0} if len(active) > 1 else {}
    with pytest.raises(ValueError):
        env.step_y47(bad_missing)

    bad_negative = {int(pid): -1 for pid in active}
    with pytest.raises(ValueError):
        env.step_y47(bad_negative)

