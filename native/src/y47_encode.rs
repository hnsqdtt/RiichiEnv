use numpy::ndarray::{Array1, Array2};
use numpy::IntoPyArray;
use pyo3::prelude::*;

use crate::env::{Action, RiichiEnv};
use crate::y47_schema as schema;
use crate::y47_turn::Y47Turn;

fn validate_real_tid(tid: u8) -> PyResult<i64> {
    let tid_i = tid as i64;
    if tid_i < 0 || tid_i >= schema::TID_NONE {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "TID out of range: {tid_i}"
        )));
    }
    Ok(tid_i)
}

fn maybe_tid(tid: Option<u8>) -> PyResult<i64> {
    match tid {
        Some(t) => validate_real_tid(t),
        None => Ok(schema::TID_NONE),
    }
}

fn push_token(token_mask: &mut Array1<bool>, cur: &mut usize) -> PyResult<usize> {
    if *cur >= schema::MAX_STATE_TOKENS {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "too many state tokens: {} > MAX_STATE_TOKENS={}",
            *cur + 1,
            schema::MAX_STATE_TOKENS
        )));
    }
    let idx = *cur;
    token_mask[idx] = true;
    *cur += 1;
    Ok(idx)
}

fn encode_observation(env: &RiichiEnv, me: u8, hand: &[u8]) -> PyResult<(Array2<i64>, Array2<f32>, Array1<bool>)> {
    let mut token_main = Array2::<i64>::zeros((schema::MAX_STATE_TOKENS, schema::TOKEN_MAIN_DIM));
    let mut token_scalar = Array2::<f32>::zeros((schema::MAX_STATE_TOKENS, 3));
    let mut token_mask = Array1::<bool>::from_elem(schema::MAX_STATE_TOKENS, false);

    let mut cur = 0usize;

    let i = push_token(&mut token_mask, &mut cur)?;
    token_main[[i, schema::TOK_TYPE]] = schema::TOK_CLS;
    token_main[[i, schema::TOK_TILE]] = schema::TID_NONE;

    let round_wind = env.round_wind as i64;
    let oya_abs = env.oya;
    let honba = env.honba as i64;
    let kyotaku = env.riichi_sticks as i64;
    let kyoku_idx = env.kyoku_idx as i64;

    let i = push_token(&mut token_mask, &mut cur)?;
    token_main[[i, schema::TOK_TYPE]] = schema::TOK_ROUND;
    token_main[[i, schema::TOK_TILE]] = schema::TID_NONE;
    token_main[[i, schema::TOK_AUX1]] = round_wind;
    token_main[[i, schema::TOK_AUX2]] = schema::abs_to_rel(oya_abs, me) as i64;
    token_scalar[[i, 0]] = honba as f32 / 20.0;
    token_scalar[[i, 1]] = kyotaku as f32 / 20.0;
    token_scalar[[i, 2]] = kyoku_idx as f32 / 16.0;

    for p_abs in 0u8..(schema::NUM_PLAYERS as u8) {
        let p_rel = schema::abs_to_rel(p_abs, me) as i64;
        let i = push_token(&mut token_mask, &mut cur)?;
        token_main[[i, schema::TOK_TYPE]] = schema::TOK_SCORE;
        token_main[[i, schema::TOK_SEAT]] = p_rel;
        token_main[[i, schema::TOK_TILE]] = schema::TID_NONE;

        let mut flags = 0i64;
        if env.riichi_declared[p_abs as usize] {
            flags |= 1;
        }
        if env.double_riichi_declared[p_abs as usize] {
            flags |= 2;
        }
        token_main[[i, schema::TOK_AUX1]] = flags;
        token_main[[i, schema::TOK_AUX2]] = env.melds[p_abs as usize].len() as i64;
        token_scalar[[i, 0]] = (env.scores[p_abs as usize] as f32 - 25000.0) / 100000.0;
    }

    for (d_i, &raw_tid) in env.dora_indicators.iter().take(schema::MAX_DORA).enumerate() {
        let i = push_token(&mut token_mask, &mut cur)?;
        token_main[[i, schema::TOK_TYPE]] = schema::TOK_DORA;
        token_main[[i, schema::TOK_TILE]] = validate_real_tid(raw_tid)?;
        token_main[[i, schema::TOK_AUX1]] = d_i as i64;
    }

    let drawn_tid = if env.current_player == me {
        env.drawn_tile
    } else {
        None
    };
    let i = push_token(&mut token_mask, &mut cur)?;
    token_main[[i, schema::TOK_TYPE]] = schema::TOK_DRAWN;
    token_main[[i, schema::TOK_TILE]] = maybe_tid(drawn_tid)?;

    let mut hand_sorted: Vec<u8> = hand.to_vec();
    if hand_sorted.len() > schema::MAX_HAND_TIDS {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "hand too long: {} > MAX_HAND_TIDS={}",
            hand_sorted.len(),
            schema::MAX_HAND_TIDS
        )));
    }
    hand_sorted.sort_unstable();
    for raw_tid in hand_sorted {
        let i = push_token(&mut token_mask, &mut cur)?;
        token_main[[i, schema::TOK_TYPE]] = schema::TOK_HAND;
        token_main[[i, schema::TOK_TILE]] = validate_real_tid(raw_tid)?;
    }

    for p_abs in 0u8..(schema::NUM_PLAYERS as u8) {
        let p_rel = schema::abs_to_rel(p_abs, me) as i64;
        let p_melds = &env.melds[p_abs as usize];
        if p_melds.len() > schema::MAX_MELDS {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "env.melds[{p_abs}] too long: {} > MAX_MELDS={}",
                p_melds.len(),
                schema::MAX_MELDS
            )));
        }
        for (meld_idx, m) in p_melds.iter().enumerate() {
            let kind = schema::meld_kind(m.meld_type);
            let opened = m.opened;
            if m.tiles.len() > schema::MAX_MELD_TILES {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "meld.tiles too long: {} > MAX_MELD_TILES={}",
                    m.tiles.len(),
                    schema::MAX_MELD_TILES
                )));
            }
            for (tile_slot, &raw_tid) in m.tiles.iter().enumerate() {
                let i = push_token(&mut token_mask, &mut cur)?;
                token_main[[i, schema::TOK_TYPE]] = schema::TOK_MELD_TILE;
                token_main[[i, schema::TOK_SEAT]] = p_rel;
                token_main[[i, schema::TOK_POS]] = meld_idx as i64;
                token_main[[i, schema::TOK_POS2]] = tile_slot as i64;
                token_main[[i, schema::TOK_TILE]] = validate_real_tid(raw_tid)?;
                token_main[[i, schema::TOK_AUX1]] = kind;
                token_main[[i, schema::TOK_AUX2]] = if opened { 1 } else { 0 };
            }
        }
    }

    for p_abs in 0u8..(schema::NUM_PLAYERS as u8) {
        let p_rel = schema::abs_to_rel(p_abs, me) as i64;
        let r_tids = &env.discards[p_abs as usize];
        let r_flags = &env.discard_flags[p_abs as usize];
        if r_tids.len() != r_flags.len() {
            return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                "discard_flags length mismatch for pid={p_abs}: discards={} flags={}",
                r_tids.len(),
                r_flags.len()
            )));
        }
        if r_tids.len() > schema::MAX_RIVER {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "river too long: {} > MAX_RIVER={}",
                r_tids.len(),
                schema::MAX_RIVER
            )));
        }
        for (ridx, (&raw_tid, &flags)) in r_tids.iter().zip(r_flags.iter()).enumerate() {
            if flags >= schema::NUM_RIVER_FLAGS {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                    "river flags out of range: {flags}"
                )));
            }
            let i = push_token(&mut token_mask, &mut cur)?;
            token_main[[i, schema::TOK_TYPE]] = schema::TOK_RIVER;
            token_main[[i, schema::TOK_SEAT]] = p_rel;
            token_main[[i, schema::TOK_POS]] = ridx as i64;
            token_main[[i, schema::TOK_TILE]] = validate_real_tid(raw_tid)?;
            token_main[[i, schema::TOK_AUX1]] = flags as i64;
        }
    }

    Ok((token_main, token_scalar, token_mask))
}

fn encode_actions(env: &RiichiEnv, me: u8, actions: &[Action]) -> PyResult<(Array2<i64>, Array2<i64>, Array2<bool>, Array1<bool>)> {
    if actions.is_empty() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "no legal actions",
        ));
    }

    let mut action_main = Array2::<i64>::zeros((schema::MAX_ACTIONS, schema::ACTION_MAIN_DIM));
    let mut action_consume = Array2::<i64>::from_elem(
        (schema::MAX_ACTIONS, schema::MAX_CONSUME_TILES),
        schema::TID_NONE,
    );
    let mut action_consume_mask =
        Array2::<bool>::from_elem((schema::MAX_ACTIONS, schema::MAX_CONSUME_TILES), false);
    let mut legal_action_mask = Array1::<bool>::from_elem(schema::MAX_ACTIONS, false);

    let last_from_abs = env.last_discard.map(|(actor, _)| actor);
    let last_from_rel = last_from_abs.map(|p| schema::abs_to_rel(p, me));
    let pending_kan_actor = env.pending_kan.as_ref().map(|(actor, _)| *actor);

    for (i, a) in actions.iter().enumerate() {
        if i >= schema::MAX_ACTIONS {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "too many legal actions: {} > MAX_ACTIONS={}",
                i + 1,
                schema::MAX_ACTIONS
            )));
        }

        let kind = schema::action_kind(a.action_type);

        let (tid, has_tile) = match kind {
            schema::ACT_DISCARD
            | schema::ACT_CHI
            | schema::ACT_PON
            | schema::ACT_DAIMINKAN
            | schema::ACT_ANKAN
            | schema::ACT_KAKAN => {
                let tile = a.tile.ok_or_else(|| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        "action must have a tile",
                    )
                })?;
                (validate_real_tid(tile)?, 1i64)
            }
            _ => (schema::TID_NONE, 0i64),
        };

        if a.consume_tiles.len() > schema::MAX_CONSUME_TILES {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "consume_tiles too long: {} > MAX_CONSUME_TILES={}",
                a.consume_tiles.len(),
                schema::MAX_CONSUME_TILES
            )));
        }

        action_main[[i, schema::ACT_KIND]] = kind;
        action_main[[i, schema::ACT_TILE]] = tid;
        action_main[[i, schema::ACT_HAS_TILE]] = has_tile;
        action_main[[i, schema::ACT_CONSUME_LEN]] = a.consume_tiles.len() as i64;

        let (from, has_from) = match kind {
            schema::ACT_CHI | schema::ACT_PON | schema::ACT_DAIMINKAN => {
                if let Some(src) = last_from_rel {
                    (src as i64, 1i64)
                } else {
                    (0i64, 0i64)
                }
            }
            schema::ACT_RON => {
                if let Some(src) = last_from_rel {
                    (src as i64, 1i64)
                } else if let Some(src_abs) = pending_kan_actor {
                    (schema::abs_to_rel(src_abs, me) as i64, 1i64)
                } else {
                    (0i64, 0i64)
                }
            }
            _ => (0i64, 0i64),
        };
        action_main[[i, schema::ACT_FROM]] = from;
        action_main[[i, schema::ACT_HAS_FROM]] = has_from;

        for (j, &t) in a.consume_tiles.iter().enumerate() {
            action_consume[[i, j]] = validate_real_tid(t)?;
            action_consume_mask[[i, j]] = true;
        }

        legal_action_mask[i] = true;
    }

    Ok((action_main, action_consume, action_consume_mask, legal_action_mask))
}

pub fn encode_turn(py: Python<'_>, env: &RiichiEnv, me: u8, hand: &[u8], actions: &[Action]) -> PyResult<Y47Turn> {
    let (token_main, token_scalar, token_mask) = encode_observation(env, me, hand)?;
    let (action_main, action_consume, action_consume_mask, legal_action_mask) =
        encode_actions(env, me, actions)?;

    Ok(Y47Turn {
        token_main: token_main.into_pyarray(py).unbind(),
        token_scalar: token_scalar.into_pyarray(py).unbind(),
        token_mask: token_mask.into_pyarray(py).unbind(),
        action_main: action_main.into_pyarray(py).unbind(),
        action_consume: action_consume.into_pyarray(py).unbind(),
        action_consume_mask: action_consume_mask.into_pyarray(py).unbind(),
        legal_action_mask: legal_action_mask.into_pyarray(py).unbind(),
    })
}
