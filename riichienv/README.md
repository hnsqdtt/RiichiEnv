# RiichiEnv Core

**High-Performance Research Environment for Riichi Mahjong**

`riichienv` は、Rust による高速な麻雀シミュレーションと、Python (Gym) API を提供する研究用ライブラリです。

## ✨ Features

- **高速シミュレーション**: Rust 実装により、非常に高速な状態遷移とロールアウトが可能。
- **並列化 (VecEnv)**: `step_batch` による数千卓規模の並列実行をサポート。
- **柔軟なルールセット**: 4人麻雀/3人麻雀、赤ドラ、ウマ/オカなどのルール設定が可能。
- **Gym 互換 API**: 強化学習の標準的なインターフェース (`reset`, `step`, `step_batch`) を提供。
- **mjai プロトコル**: 学習環境として必要な mjai メッセージの解釈と生成をサポート。

## 📦 Installation

This package requires **Rust** to build the core extension.

```bash
# Using uv (Recommended)
uv sync
# or
uv pip install .

# Using pip
pip install .
```

## 🚀 Usage

様々なゲームルームに対応可能です。デフォルトは1局終了4人麻雀の試合を実行します。

```python
from riichienv import RiichiEnv
from riichienv.agents import RandomAgent

agent = RandomAgent()
env = RiichiEnv()
obs_dict = env.reset()
while not env.done():
    actions = {player_id: agent.act(obs)
               for player_id, obs in obs_dict.items()}
    obs_dict = env.step(actions)

scores, points = env.scores(), env.points()
```

1局試合は場風や初期スコア、供託金、本場など、引数で設定可能です。

```python
from riichienv import RiichiEnv
from riichienv.agents import RandomAgent

env = RiichiEnv(
    round_wind=0,
    initial_scores=[25000, 25000, 25000, 25000],
    kyotaku=0,
    honba=0,
)
obs_dict = env.reset()
while not env.done():
    actions = {player_id: agent.act(obs)
               for player_id, obs in obs_dict.items()}
    obs_dict = env.step(actions)

scores, points = env.scores(), env.points()
```

半荘4人麻雀サドンデスあり飛びありのルールで試合を実行する場合は以下のように実行します。
以下の場合では1局終了時ではなく、半荘試合が終了したタイミングで `env.done()` が `True` になります。

```python
from riichienv import RiichiEnv
from riichienv.agents import RandomAgent
from riichienv.game_mode import GameType

agent = RandomAgent()
env = RiichiEnv(game_type=GameType.YON_HANCHAN)
obs_dict = env.reset()
while not env.done():
    actions = {player_id: agent.act(obs)
               for player_id, obs in obs_dict.items()}
    obs_dict = env.step(actions)

scores, points = env.scores(), env.points()
```

Mortal の mjai Bot とイベント処理フローの互換性を持ちます。

```python
import json

from riichienv import RiichiEnv
from riichienv.game_mode import GameType

from model import load_model

class MortalAgent:
    def __init__(self, player_id: int):
        self.player_id = player_id
        # Load `libriichi.mjai.Bot` instance
        self.model = load_model(player_id, "./mortal_v4.pth")

    def act(self, obs) -> Action:
        events = obs.new_events()
        resp = None
        for i, ev in enumerate(events):
            resp = self.model.react(json.dumps(ev, separators=(",", ":")))

        action = obs.select_action_from_mjai(resp)
        assert action is not None, f"No response despite legal actions: {obs.legal_actions()}"
        return action

env = RiichiEnv(game_type=GameType.YON_HANCHAN, mjai_mode=True)
agents = {pid: MortalAgent(pid) for pid in range(4)}
obs_dict = env.reset()
while not env.done():
    actions = {pid: agents[pid].act(obs) for pid, obs in obs_dict.items()}
    obs_dict = env.step(actions)

print("FINISHED")

```

## 🛠 Development

- **Python**: 3.13+
- **Rust**: Nightly (recommended)
- **Build System**: `maturin`

```bash
# Developers build
uv run maturin develop
```
