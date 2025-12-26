import time
import json

from riichienv import RiichiEnv
from riichienv.agents import RandomAgent


def verify():
    agent = RandomAgent(seed=42)
    env = RiichiEnv(seed=42)
    obs_dict = env.reset()
    
    # Check Secure Wall
    print(f"Wall Digest: {env.wall_digest}")
    print(f"Salt: {env.salt}")

    # Check Initial MJAI
    p0_obs = obs_dict[0]
    print("Initial MJAI events for Player 0:")
    for ev in p0_obs.events:
        print(f">> {json.dumps(ev, separators=(',', ':'))}")
    
    steps = 0
    start_time = time.time()
    
    while not env.done():
        actions = {player_id: agent.act(obs)
                   for player_id, obs in obs_dict.items()}
        obs_dict = env.step(actions)
        steps += 1

    returns = env.rewards()
    duration = time.time() - start_time
    print("-" * 80)
    print(f"Game finished in {steps} steps, {duration:.2f} seconds.")
    print(f"Rewards: {returns}")
    
    # Check final MJAI logs counts
    print(f"Total MJAI events logged: {len(env.mjai_log)}")
    print("Verification Successful!")


if __name__ == "__main__":
    verify()
