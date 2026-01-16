import time
import schedule
import pandas as pd
from datetime import datetime
from core.data import DataLoader
from core.storage import Storage
from core.prize import PrizeCalculator
from core.lottery import GameType

def run_task():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行定时任务...")
    
    dl = DataLoader()
    storage = Storage()
    
    # Iterate both game types
    for game_type in [GameType.SSQ, GameType.DLT]:
        print(f"正在处理: {game_type.value} ...")
        
        try:
            # 1. Force Update Data
            df = dl.load_data(game_type, force_update=True)
            if df.empty:
                print(f"❌ {game_type.value} 数据更新失败或为空")
                continue
            
            print(f"✅ {game_type.value} 数据已更新，最新期号: {df.iloc[-1]['issue']}")
            
            # 2. Verify Pending Bets (For ALL users)
            # load_bets(user_id=None) returns all bets
            all_bets = storage.load_bets(user_id=None)
            
            if all_bets.empty:
                print(f"  无投注记录")
                continue
                
            # Filter for pending and current game type
            pending = all_bets[(all_bets['status'] == 'pending') & (all_bets['game_type'] == game_type.value)]
            
            if pending.empty:
                print(f"  无待核验记录")
                continue
                
            print(f"  发现 {len(pending)} 条待核验记录，开始核对...")
            
            updates = 0
            for idx, row in pending.iterrows():
                # Match issue
                match = df[df['issue'] == str(row['issue'])]
                if not match.empty:
                    actual_row = match.iloc[0]
                    
                    if game_type == GameType.SSQ:
                        act_reds = [int(actual_row[f'red{j}']) for j in range(1, 7)]
                        act_blues = [int(actual_row['blue'])]
                    else:
                        act_reds = [int(actual_row[f'red{j}']) for j in range(1, 6)]
                        act_blues = [int(actual_row[f'blue{j}']) for j in range(1, 3)]
                    
                    try:
                        # Handle potential string format from CSV/DB if not parsed
                        bet_reds = row['reds']
                        bet_blues = row['blues']
                        
                        # If they are strings (e.g. "[1, 2]"), verify if storage.load_bets parses them
                        # storage.load_bets calls db.get_bets which does json.loads.
                        # So they should be lists.
                        
                        red_hits = len(set(bet_reds) & set(act_reds))
                        blue_hits = len(set(bet_blues) & set(act_blues))
                        
                        prize_res = PrizeCalculator.calculate(game_type, red_hits, blue_hits)
                        
                        storage.update_bet_status(row['id'], prize_res.level, prize_res.amount)
                        updates += 1
                        print(f"    - 订单 {row['id']} (用户 {row['user_id']}): {prize_res.level}")
                        
                    except Exception as e:
                        print(f"    ❌ 核验出错 {row['id']}: {e}")
            
            print(f"  ✅ {game_type.value} 核验完成，更新了 {updates} 条记录")
            
        except Exception as e:
            print(f"❌ 任务执行出错 ({game_type.value}): {e}")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务结束。\n")

if __name__ == "__main__":
    print("🚀 定时任务服务已启动 (每天 21:20 执行)")
    
    # Schedule at 21:20 Beijing Time
    schedule.every().day.at("21:20").do(run_task)
    
    # Also run once on startup for verification (optional, maybe unsafe if data not ready? Let's skip)
    # run_task() 
    
    while True:
        schedule.run_pending()
        time.sleep(60)
