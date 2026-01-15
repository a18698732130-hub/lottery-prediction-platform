import pandas as pd
from datetime import datetime
from core.lottery import GameType
from core.db import Database

class Storage:
    def __init__(self):
        self.db = Database()

    def load_bets(self, user_id: str = None) -> pd.DataFrame:
        """Load bets from DB, optionally filtered by user_id"""
        bets = self.db.get_bets(user_id=user_id)
        if not bets:
            return pd.DataFrame()
        return pd.DataFrame(bets)

    def save_bet(self, game_type: GameType, issue: str, reds: list, blues: list, note: str = "", user_id: str = "default"):
        bet_data = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
            "user_id": user_id,
            "game_type": game_type.value,
            "issue": issue,
            "reds": reds,
            "blues": blues,
            "note": note
        }
        self.db.add_bet(bet_data)
        return True

    def update_bet_status(self, bet_id: str, prize_level: str, win_amount: int):
        return self.db.update_bet_status(bet_id, prize_level, win_amount)
