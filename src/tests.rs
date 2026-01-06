#[cfg(test)]
mod unit_tests {
    use crate::agari::{is_agari, is_chiitoitsu, is_kokushi};
    use crate::score::calculate_score;
    use crate::types::Hand;

    #[test]
    fn test_agari_standard() {
        // Pinfu Tsumo: 123 456 789 m 234 p 55 s
        let tiles = [
            0, 1, 2, // 123m
            3, 4, 5, // 456m
            6, 7, 8, // 789m
            9, 10, 11, // 123p (mapped to 9,10,11)
            18, 18, // 1s pair (mapped to 18)
        ];
        let mut hand = Hand::new(Some(tiles.to_vec()));
        assert!(is_agari(&mut hand), "Should be agari");
    }

    #[test]
    fn test_basic_pinfu() {
        // 123m 456m 789m 123p 11s
        // m: 0-8, p: 9-17, s: 18-26_
        // 123p -> 9, 10, 11
        // 11s -> 18, 18
        let mut hand = Hand::new(None);
        // 123m
        hand.add(0);
        hand.add(1);
        hand.add(2);
        // 456m
        hand.add(3);
        hand.add(4);
        hand.add(5);
        // 789m
        hand.add(6);
        hand.add(7);
        hand.add(8);
        // 123p
        hand.add(9);
        hand.add(10);
        hand.add(11);
        // 11s (pair)
        hand.add(18);
        hand.add(18);

        assert!(is_agari(&mut hand));
    }

    #[test]
    fn test_chiitoitsu() {
        let mut hand = Hand::new(None);
        let pairs = [0, 2, 4, 6, 8, 10, 12];
        for &t in &pairs {
            hand.add(t);
            hand.add(t);
        }
        assert!(is_chiitoitsu(&hand));
        assert!(is_agari(&mut hand));
    }

    #[test]
    fn test_kokushi() {
        let mut hand = Hand::new(None);
        // 1m,9m, 1p,9p, 1s,9s, 1z-7z
        let terminals = [0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32, 33];
        for &t in &terminals {
            hand.add(t);
        }
        hand.add(0); // Double 1m
        assert!(is_kokushi(&hand));
        assert!(is_agari(&mut hand));
    }

    #[test]
    fn test_score_calculation() {
        // Mangan: 30fu 4han -> 7700 or 8000 (usually rounded) -> 2000 base
        // 30 * 2^(2+4) = 30 * 64 = 1920 -> 2000.
        // Ko Tsumo: 2000/4000? No, mangan is 8000 total.
        // Oya pays 4000, ko pays 2000.

        let score = calculate_score(4, 30, false, true); // Ko Tsumo
                                                         // Pay Oya: 2000 * 2 = 4000
                                                         // Pay Ko: 2000 * 1 = 2000
        assert_eq!(score.pay_tsumo_oya, 4000);
        assert_eq!(score.pay_tsumo_ko, 2000);
        assert_eq!(score.total, 8000);
    }

    #[test]
    fn test_tsuu_iisou() {
        use crate::yaku::{calculate_yaku, YakuContext};
        let mut hand = Hand::new(None);
        // 111z, 222z, 333z, 444z, 55z
        for &t in &[27, 28, 29, 30] {
            hand.add(t);
            hand.add(t);
            hand.add(t);
        }
        hand.add(31);
        hand.add(31);

        let res = calculate_yaku(&hand, &[], &YakuContext::default(), 31);
        assert!(res.han >= 13);
        assert!(res.yaku_ids.contains(&39));
    }

    #[test]
    fn test_ryuu_iisou() {
        use crate::yaku::{calculate_yaku, YakuContext};
        let mut hand = Hand::new(None);
        // 234s, 666s, 888s, 6s6s6s (Wait, 6s6s6s is already there)
        // Correct 234s, 666s, 888s, Hatsuz, 6s6s (pair)
        let tiles = [
            19, 20, 21, // 234s
            23, 23, 23, // 666s
            25, 25, 25, // 888s
            32, 32, 32, // Hatsuz
            19, 19, // 2s pair
        ];
        for &t in &tiles {
            hand.add(t);
        }

        let res = calculate_yaku(&hand, &[], &YakuContext::default(), 19);
        assert!(res.han >= 13);
        assert!(res.yaku_ids.contains(&40));
    }

    #[test]
    fn test_daisushii() {
        use crate::yaku::{calculate_yaku, YakuContext};
        let mut hand = Hand::new(None);
        // EEEz, SSSz, WWWz, NNNz, 11m
        for &t in &[27, 28, 29, 30] {
            hand.add(t);
            hand.add(t);
            hand.add(t);
        }
        hand.add(0);
        hand.add(0);

        let res = calculate_yaku(&hand, &[], &YakuContext::default(), 0);
        assert!(res.han >= 26);
        assert!(res.yaku_ids.contains(&50));
    }
}
