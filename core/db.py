import sqlite3
import os
from datetime import datetime
import json

DB_PATH = os.path.join("data", "lottery.db")

class Database:
    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        cursor = self.conn.cursor()
        # Bets table with user_id for isolation
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bets (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                game_type TEXT NOT NULL,
                issue TEXT NOT NULL,
                reds TEXT NOT NULL,
                blues TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                prize_level TEXT,
                win_amount INTEGER DEFAULT 0,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Daily Recommendations Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_recommendations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                date_str TEXT NOT NULL,
                game_type TEXT NOT NULL,
                predictions TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Users Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def close(self):
        self.conn.close()

    # --- User Management ---
    def create_user(self, username, password_hash):
        cursor = self.conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_user(self, username):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        return cursor.fetchone()

    # --- Daily Recommendations ---
    
    def get_daily_recommendation(self, user_id: str, date_str: str, game_type: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT predictions FROM daily_recommendations 
            WHERE user_id = ? AND date_str = ? AND game_type = ?
        ''', (user_id, date_str, game_type))
        row = cursor.fetchone()
        if row:
            return json.loads(row['predictions'])
        return None

    def save_daily_recommendation(self, user_id: str, date_str: str, game_type: str, predictions: list):
        # Generate ID
        rec_id = f"{user_id}_{date_str}_{game_type}"
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO daily_recommendations (id, user_id, date_str, game_type, predictions)
            VALUES (?, ?, ?, ?, ?)
        ''', (rec_id, user_id, date_str, game_type, json.dumps(predictions)))
        self.conn.commit()

    # --- CRUD Operations ---

    def add_bet(self, bet_data: dict):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO bets (id, user_id, game_type, issue, reds, blues, status, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            bet_data['id'],
            bet_data['user_id'],
            bet_data['game_type'],
            bet_data['issue'],
            json.dumps(bet_data['reds']), # Store lists as JSON strings
            json.dumps(bet_data['blues']),
            'pending',
            bet_data.get('note', ''),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        self.conn.commit()

    def get_bets(self, user_id: str = None, game_type: str = None):
        query = "SELECT * FROM bets WHERE 1=1"
        params = []
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if game_type:
            query += " AND game_type = ?"
            params.append(game_type)
        
        query += " ORDER BY created_at DESC"
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert rows to list of dicts and parse JSON
        results = []
        for row in rows:
            d = dict(row)
            d['reds'] = json.loads(d['reds'])
            d['blues'] = json.loads(d['blues'])
            results.append(d)
        return results

    def update_bet_status(self, bet_id: str, prize_level: str, win_amount: int):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE bets 
            SET status = 'checked', prize_level = ?, win_amount = ?
            WHERE id = ?
        ''', (prize_level, win_amount, bet_id))
        self.conn.commit()
        return cursor.rowcount > 0
