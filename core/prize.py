from dataclasses import dataclass
from enum import Enum
from core.lottery import GameType

@dataclass
class PrizeResult:
    level: str      # 奖级 (如 "一等奖")
    amount: int     # 固定奖金金额 (浮动奖通常设为预估值)
    description: str # 描述 (如 "6+1")

class PrizeCalculator:
    @staticmethod
    def calc_ssq(red_hits: int, blue_hits: int) -> PrizeResult:
        """双色球奖金计算"""
        if red_hits == 6 and blue_hits == 1:
            return PrizeResult("一等奖", 10000000, "6+1 (浮动)") # 最高1000万
        elif red_hits == 6 and blue_hits == 0:
            return PrizeResult("二等奖", 300000, "6+0 (浮动)")
        elif red_hits == 5 and blue_hits == 1:
            return PrizeResult("三等奖", 3000, "5+1")
        elif (red_hits == 5 and blue_hits == 0) or (red_hits == 4 and blue_hits == 1):
            return PrizeResult("四等奖", 200, "5+0 或 4+1")
        elif (red_hits == 4 and blue_hits == 0) or (red_hits == 3 and blue_hits == 1):
            return PrizeResult("五等奖", 10, "4+0 或 3+1")
        elif blue_hits == 1:
            return PrizeResult("六等奖", 5, "0+1, 1+1, 2+1")
        else:
            return PrizeResult("未中奖", 0, "未达标")

    @staticmethod
    def calc_dlt(red_hits: int, blue_hits: int) -> PrizeResult:
        """大乐透奖金计算 (常规规则)"""
        if red_hits == 5 and blue_hits == 2:
            return PrizeResult("一等奖", 10000000, "5+2 (浮动)")
        elif red_hits == 5 and blue_hits == 1:
            return PrizeResult("二等奖", 200000, "5+1 (浮动)")
        elif red_hits == 5 and blue_hits == 0:
            return PrizeResult("三等奖", 10000, "5+0")
        elif red_hits == 4 and blue_hits == 2:
            return PrizeResult("四等奖", 3000, "4+2")
        elif red_hits == 4 and blue_hits == 1:
            return PrizeResult("五等奖", 300, "4+1")
        elif red_hits == 3 and blue_hits == 2:
            return PrizeResult("六等奖", 200, "3+2")
        elif red_hits == 4 and blue_hits == 0:
            return PrizeResult("七等奖", 100, "4+0")
        elif (red_hits == 3 and blue_hits == 1) or (red_hits == 2 and blue_hits == 2):
            return PrizeResult("八等奖", 15, "3+1 或 2+2")
        elif (red_hits == 3 and blue_hits == 0) or (red_hits == 1 and blue_hits == 2) or (red_hits == 2 and blue_hits == 1) or (red_hits == 0 and blue_hits == 2):
            return PrizeResult("九等奖", 5, "3+0, 2+1, 1+2, 0+2")
        else:
            return PrizeResult("未中奖", 0, "未达标")

    @staticmethod
    def calculate(game_type: GameType, red_hits: int, blue_hits: int) -> PrizeResult:
        if game_type == GameType.SSQ:
            return PrizeCalculator.calc_ssq(red_hits, blue_hits)
        elif game_type == GameType.DLT:
            return PrizeCalculator.calc_dlt(red_hits, blue_hits)
        else:
            return PrizeResult("未知", 0, "未知彩种")
