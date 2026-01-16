use crate::env::ActionType;
use crate::types::MeldType;

pub const NUM_PLAYERS: usize = 4;

pub const MAX_STATE_TOKENS: usize = 256;
pub const MAX_ACTIONS: usize = 128;
pub const MAX_CONSUME_TILES: usize = 4;

pub const TOKEN_MAIN_DIM: usize = 7;
pub const TOK_TYPE: usize = 0;
pub const TOK_SEAT: usize = 1;
pub const TOK_POS: usize = 2;
pub const TOK_POS2: usize = 3;
pub const TOK_TILE: usize = 4;
pub const TOK_AUX1: usize = 5;
pub const TOK_AUX2: usize = 6;

pub const TOK_CLS: i64 = 0;
pub const TOK_ROUND: i64 = 1;
pub const TOK_SCORE: i64 = 2;
pub const TOK_DORA: i64 = 3;
pub const TOK_DRAWN: i64 = 4;
pub const TOK_HAND: i64 = 5;
pub const TOK_MELD_TILE: i64 = 6;
pub const TOK_RIVER: i64 = 7;

pub const MAX_HAND_TIDS: usize = 14;
pub const MAX_RIVER: usize = 30;
pub const MAX_MELDS: usize = 4;
pub const MAX_MELD_TILES: usize = 4;
pub const MAX_DORA: usize = 5;

pub const ACTION_MAIN_DIM: usize = 6;
pub const ACT_KIND: usize = 0;
pub const ACT_TILE: usize = 1;
pub const ACT_FROM: usize = 2;
pub const ACT_CONSUME_LEN: usize = 3;
pub const ACT_HAS_TILE: usize = 4;
pub const ACT_HAS_FROM: usize = 5;

pub const ACT_DISCARD: i64 = 0;
pub const ACT_CHI: i64 = 1;
pub const ACT_PON: i64 = 2;
pub const ACT_DAIMINKAN: i64 = 3;
pub const ACT_ANKAN: i64 = 4;
pub const ACT_KAKAN: i64 = 5;
pub const ACT_RIICHI: i64 = 6;
pub const ACT_RON: i64 = 7;
pub const ACT_TSUMO: i64 = 8;
pub const ACT_PASS: i64 = 9;
pub const ACT_KYUSHU_KYUHAI: i64 = 10;

pub const TID_NONE: i64 = 136;

pub const RIVER_FLAG_TSUMOGIRI: u8 = 1 << 0;
pub const RIVER_FLAG_RIICHI_TILE: u8 = 1 << 1;
pub const NUM_RIVER_FLAGS: u8 = 4;

pub const RANK_REWARDS: [f32; 4] = [0.9, 0.45, 0.0, -1.35];

pub fn abs_to_rel(p_abs: u8, me: u8) -> u8 {
    ((p_abs as i32 - me as i32).rem_euclid(NUM_PLAYERS as i32)) as u8
}

pub fn meld_kind(meld_type: MeldType) -> i64 {
    match meld_type {
        MeldType::Chi => 1,
        MeldType::Peng => 2,
        MeldType::Gang => 3,
        MeldType::Angang => 4,
        MeldType::Addgang => 5,
    }
}

pub fn action_kind(action_type: ActionType) -> i64 {
    match action_type {
        ActionType::Discard => ACT_DISCARD,
        ActionType::Chi => ACT_CHI,
        ActionType::Pon => ACT_PON,
        ActionType::Daiminkan => ACT_DAIMINKAN,
        ActionType::Ankan => ACT_ANKAN,
        ActionType::Kakan => ACT_KAKAN,
        ActionType::Riichi => ACT_RIICHI,
        ActionType::Ron => ACT_RON,
        ActionType::Tsumo => ACT_TSUMO,
        ActionType::Pass => ACT_PASS,
        ActionType::KyushuKyuhai => ACT_KYUSHU_KYUHAI,
    }
}
