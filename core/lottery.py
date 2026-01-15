from enum import Enum
from dataclasses import dataclass

class GameType(Enum):
    SSQ = "ssq"
    DLT = "dlt"

@dataclass
class LotteryConfig:
    name: str
    cn_name: str
    red_range: tuple[int, int]
    red_count: int
    blue_range: tuple[int, int]
    blue_count: int

GAME_CONFIGS = {
    GameType.SSQ: LotteryConfig(
        name="ssq",
        cn_name="双色球",
        red_range=(1, 33),
        red_count=6,
        blue_range=(1, 16),
        blue_count=1
    ),
    GameType.DLT: LotteryConfig(
        name="dlt",
        cn_name="大乐透",
        red_range=(1, 35),
        red_count=5,
        blue_range=(1, 12),
        blue_count=2
    )
}

def get_config(game_type: GameType) -> LotteryConfig:
    return GAME_CONFIGS[game_type]
