import glob
import os
import time
import argparse
from riichienv import ReplayGame

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--logs", default="data/game_record_4p_jad_2025-12-14_out/*.json.gz")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_pattern = os.path.join(script_dir, "..", args.logs)
    
    log_files = glob.glob(logs_pattern)
    if not log_files:
        print(f"No log files found at {logs_pattern}")
        return

    print(f"Found {len(log_files)} log files.")
    
    total_agari = 0
    mismatches = 0
    errors = 0
    total_parse_time = 0
    total_verify_time = 0
    start_time = time.time()

    # YAKUMAN_IDS: 35..51 (translated from Rust)
    yakuman_ids = set(range(35, 51))

    for log_path in log_files:
        try:
            t0 = time.time()
            game = ReplayGame.from_json(log_path)
            t1 = time.time()
            total_parse_time += (t1 - t0)
            
            t0 = time.time()
            # Correct iteration: ReplayGame -> KyokuIterator -> AgariContextIterator
            for kyoku in game.take_kyokus():
                for ctx in kyoku.take_agari_contexts():
                    total_agari += 1
                    
                    actual = ctx.actual
                    
                    expected_han = ctx.expected_han
                    expected_fu = ctx.expected_fu
                    expected_yaku = set(ctx.expected_yaku)
                    
                    # Normalize Yakuman Han (MJAI log uses 1 for 1 unit of Yakuman)
                    # If any expected yaku is a Yakuman and han is small, normalize to 13-multiple
                    is_yakuman = any(y in yakuman_ids for y in expected_yaku)
                    if is_yakuman and expected_han < 13:
                        expected_han *= 13
                        # In Yakuman cases, Fu might be 0 in our engine but non-zero in log
                        actual_fu = actual.fu
                        normalized_expected_fu = 0 if actual.han >= 13 else expected_fu
                    else:
                        actual_fu = actual.fu
                        normalized_expected_fu = expected_fu
                    
                    han_match = actual.han == expected_han
                    fu_match = actual_fu == normalized_expected_fu
                    
                    if not (han_match and fu_match):
                        mismatches += 1
                        print(f"Mismatch in {log_path}:")
                        print(f"  Seat: {ctx.seat}")
                        print(f"  Expected: Han={expected_han}, Fu={expected_fu} (orig)")
                        print(f"  Actual:   Han={actual.han}, Fu={actual.fu}")
                        print(f"  Yaku Expected: {list(ctx.expected_yaku)}")
                        print(f"  Yaku Actual:   {actual.yaku}")

            t1 = time.time()
            total_verify_time += (t1 - t0)

        except Exception as e:
            print(f"Error processing {log_path}: {e}")
            errors += 1

    end_time = time.time()
    duration = end_time - start_time

    print("-" * 20)
    print(f"Processed {total_agari} agari situations in {duration:.2f} seconds.")
    print(f"  Parse time: {total_parse_time:.2f}s")
    print(f"  Verify time: {total_verify_time:.2f}s")
    print(f"Mismatches: {mismatches}")
    print(f"Errors: {errors}")
    if total_agari > 0:
        print(f"Accuracy: {(total_agari - mismatches) / total_agari * 100:.2f}%")
        print(f"Throughput: {total_agari / duration:.2f} agari/sec")

if __name__ == "__main__":
    main()
