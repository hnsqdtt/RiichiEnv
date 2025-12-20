import glob
import os
import time
from riichienv import ReplayGame

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_pattern = os.path.join(script_dir, '../data/game_record_4p_thr_2025-12-14_out/*.json.gz')
    
    log_files = glob.glob(logs_pattern)
    if not log_files:
        print(f"No log files found at {logs_pattern}")
        return

    print(f"Found {len(log_files)} log files.")
    
    total_agari = 0
    mismatches = 0
    errors = 0
    total_kyoku = 0
    
    total_parse_time = 0
    total_verify_time = 0
    start_time = time.time()

    for log_path in log_files:
        try:
            t0 = time.time()
            game = ReplayGame.from_json(log_path)
            t1 = time.time()
            total_parse_time += (t1 - t0)
            
            t0 = time.time()
            num_agari, num_mismatches = game.verify()
            t1 = time.time()
            total_verify_time += (t1 - t0)
            
            total_agari += num_agari
            mismatches += num_mismatches
            total_kyoku += game.num_rounds()
        except Exception as e:
            print(f"Error processing {log_path}: {e}")
            errors += 1

    end_time = time.time()
    duration = end_time - start_time

    print("-" * 20)
    print(f"Processed {total_kyoku} kyoku.")
    print(f"Processed {total_agari} agari situations in {duration:.2f} seconds.")
    print(f"  Parse time: {total_parse_time:.2f}s")
    print(f"  Verify time: {total_verify_time:.2f}s")
    print(f"Mismatches: {mismatches}")
    print(f"Errors: {errors}")
    if total_agari > 0:
        print(f"Performance (total): {total_kyoku / duration:.2f} kyoku/sec")
        print(f"Performance (verify only): {total_kyoku / total_verify_time:.2f} kyoku/sec")
        print(f"Accuracy: {(total_agari - mismatches) / total_agari * 100:.2f}%")

if __name__ == "__main__":
    main()
