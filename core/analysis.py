import random
import pandas as pd
from collections import Counter
from core.lottery import GameType, get_config
from core.prize import PrizeCalculator

# --- Helper Functions ---

def weighted_sample_without_replacement(population, weights, k):
    """
    Weighted random sample without replacement.
    """
    v = [random.random() ** (1 / w) if w > 0 else 0 for w in weights]
    order = sorted(range(len(population)), key=lambda i: v[i], reverse=True)
    return sorted([population[i] for i in order[:k]])

def calculate_omission(df: pd.DataFrame, max_num: int, prefix: str = 'red') -> dict:
    """
    Calculate current omission for each number.
    """
    omission_counts = {i: 0 for i in range(1, max_num + 1)}
    cols = [c for c in df.columns if prefix in c]
    
    # Iterate backwards from the last row
    reversed_df = df.iloc[::-1]
    
    for num in range(1, max_num + 1):
        count = 0
        for _, row in reversed_df.iterrows():
            row_values = row[cols].values
            if num in row_values:
                break
            count += 1
        omission_counts[num] = count
        
    return omission_counts

def calculate_sum(numbers: list) -> int:
    return sum(numbers)

def check_consecutive(numbers: list) -> int:
    sorted_nums = sorted(numbers)
    count = 0
    for i in range(len(sorted_nums) - 1):
        if sorted_nums[i+1] == sorted_nums[i] + 1:
            count += 1
    return count

# --- Main Classes ---

class Simulator:
    @staticmethod
    def simulate_draw(game_type: GameType):
        config = get_config(game_type)
        reds = sorted(random.sample(range(config.red_range[0], config.red_range[1] + 1), config.red_count))
        blues = sorted(random.sample(range(config.blue_range[0], config.blue_range[1] + 1), config.blue_count))
        return reds, blues

class Predictor:
    @staticmethod
    def random_predict(game_type: GameType, history_df: pd.DataFrame = None):
        return Simulator.simulate_draw(game_type)

    @staticmethod
    def frequency_predict(game_type: GameType, history_df: pd.DataFrame, top_n: int = 100):
        config = get_config(game_type)
        recent = history_df.tail(top_n)
        
        red_cols = [c for c in recent.columns if 'red' in c]
        red_numbers = recent[red_cols].values.flatten()
        red_counts = Counter(red_numbers)
        
        blue_cols = [c for c in recent.columns if 'blue' in c]
        blue_numbers = recent[blue_cols].values.flatten()
        blue_counts = Counter(blue_numbers)
        
        red_pop = list(range(config.red_range[0], config.red_range[1] + 1))
        red_weights = [red_counts.get(float(n), 0.1) for n in red_pop]
        
        blue_pop = list(range(config.blue_range[0], config.blue_range[1] + 1))
        blue_weights = [blue_counts.get(float(n), 0.1) for n in blue_pop]

        pred_reds = weighted_sample_without_replacement(red_pop, red_weights, config.red_count)
        pred_blues = weighted_sample_without_replacement(blue_pop, blue_weights, config.blue_count)
        
        return pred_reds, pred_blues

    @staticmethod
    def omission_predict(game_type: GameType, history_df: pd.DataFrame):
        """
        Predict based on Omission (Gambler's Fallacy Strategy: Pick cold numbers).
        Higher omission = Higher weight.
        """
        config = get_config(game_type)
        
        # Red Omission
        red_omission = calculate_omission(history_df, config.red_range[1], 'red')
        red_pop = list(range(config.red_range[0], config.red_range[1] + 1))
        # Weight = (omission + 1) ^ 2 to emphasize cold numbers
        red_weights = [ (red_omission.get(n, 0) + 1) ** 2 for n in red_pop ]
        
        # Blue Omission
        blue_omission = calculate_omission(history_df, config.blue_range[1], 'blue')
        blue_pop = list(range(config.blue_range[0], config.blue_range[1] + 1))
        blue_weights = [ (blue_omission.get(n, 0) + 1) ** 2 for n in blue_pop ]
        
        pred_reds = weighted_sample_without_replacement(red_pop, red_weights, config.red_count)
        pred_blues = weighted_sample_without_replacement(blue_pop, blue_weights, config.blue_count)
        
        return pred_reds, pred_blues

    @staticmethod
    def composite_predict(game_type: GameType, history_df: pd.DataFrame, seed: int = None):
        """
        Enhanced Smart Trend Strategy (Optimized for ROI):
        1. Blue Ball Focus: High weight on recent hot blue numbers (easier to hit).
        2. Red Ball Kill: Remove 1-2 absolutely coldest numbers to slightly improve odds.
        3. Trend: Boost Repeat Numbers.
        4. Filter: Golden Sum & Consecutive.
        """
        if seed is not None:
            random.seed(seed)

        config = get_config(game_type)
        recent = history_df.tail(100)
        
        # 0. Get Last Draw Numbers (for Repeat Logic)
        last_draw = history_df.iloc[-1]
        last_reds = []
        if game_type == GameType.SSQ:
            last_reds = [int(last_draw[f'red{j}']) for j in range(1, 7)]
        else:
            last_reds = [int(last_draw[f'red{j}']) for j in range(1, 6)]

        # 1. Frequency Analysis
        red_cols = [c for c in recent.columns if 'red' in c]
        red_counts = Counter(recent[red_cols].values.flatten())
        
        blue_cols = [c for c in recent.columns if 'blue' in c]
        blue_counts = Counter(recent[blue_cols].values.flatten())
        
        # 2. Omission Analysis
        red_omission = calculate_omission(history_df, config.red_range[1], 'red')
        blue_omission = calculate_omission(history_df, config.blue_range[1], 'blue')
        
        # Calculate Weights
        red_pop = list(range(config.red_range[0], config.red_range[1] + 1))
        blue_pop = list(range(config.blue_range[0], config.blue_range[1] + 1))
        
        # KILL LOGIC: Remove the bottom 3 coldest red numbers (Highest Omission)
        # Aggressive killing to improve efficiency
        sorted_red_omission = sorted(red_omission.items(), key=lambda x: x[1], reverse=True)
        kill_reds = [x[0] for x in sorted_red_omission[:3]]
        
        # Filter population
        red_pop = [r for r in red_pop if r not in kill_reds]
        
        def get_weight(n, counts, omission, is_repeat=False, is_blue=False):
            freq_w = counts.get(float(n), 0.5) # Base weight from frequency
            omission_val = omission.get(n, 0)
            
            weight = freq_w + 1
            
            # Strategy:
            # For Blue: Chase HOT numbers. Short cycle.
            # For Red: Chase HOT + REPEAT, but protect against extreme COLD.
            
            if is_blue:
                # Blue Strategy: Heavily favor hot numbers (recent 100 draws)
                # Omission doesn't matter as much for Blue in short term
                weight = weight * 3.0 # Increased weight for hot blues
            else:
                # Red Strategy
                # Boost if extremely cold (Omission > 20)
                if omission_val > 20:
                    weight *= 1.5
                
                # Boost if Repeat (Trend)
                if is_repeat:
                    weight *= 2.5 # Increased repeat weight
            
            return weight

        red_weights = [get_weight(n, red_counts, red_omission, n in last_reds, is_blue=False) for n in red_pop]
        blue_weights = [get_weight(n, blue_counts, blue_omission, is_blue=True) for n in blue_pop]
        
        # Define Sum Range
        if game_type == GameType.SSQ:
            target_min, target_max = 80, 130 
        else:
            target_min, target_max = 60, 120
            
        # Retry loop for filtering
        for _ in range(2000): 
            pred_reds = weighted_sample_without_replacement(red_pop, red_weights, config.red_count)
            pred_blues = weighted_sample_without_replacement(blue_pop, blue_weights, config.blue_count)
            
            # Filter 1: Sum
            s = sum(pred_reds)
            if not (target_min <= s <= target_max):
                continue

            # Filter 2: Consecutive
            if check_consecutive(pred_reds) == 0:
                # 60% chance to reject if no consecutive (Relaxed from 80% to allow some variety)
                if random.random() < 0.6: 
                    continue

            # Filter 3: Zone Balance (New)
            # Zone 1: 1-11, Zone 2: 12-22, Zone 3: 23-33 (approx)
            z1 = len([r for r in pred_reds if r <= 11])
            z2 = len([r for r in pred_reds if 11 < r <= 22])
            z3 = len([r for r in pred_reds if r > 22])
            
            # Reject if any zone has > 4 numbers (too clumped) or if all numbers are in 1 zone (impossible)
            if z1 > 4 or z2 > 4 or z3 > 4:
                continue
            if (z1==0 and z2==0) or (z1==0 and z3==0) or (z2==0 and z3==0):
                 # Reject if 2 zones are empty (all in 1 zone)
                 continue
            
            return pred_reds, pred_blues
                
        # Fallback
        return weighted_sample_without_replacement(red_pop, red_weights, config.red_count), \
               weighted_sample_without_replacement(blue_pop, blue_weights, config.blue_count)

    @staticmethod
    def predict_many(game_type: GameType, history_df: pd.DataFrame, count: int = 5, seed_base: int = None):
        predictions = []
        for i in range(count):
            current_seed = seed_base + i if seed_base is not None else None
            predictions.append(Predictor.composite_predict(game_type, history_df, seed=current_seed))
        return predictions

class Backtester:
    @staticmethod
    def run_backtest(game_type: GameType, strategy_func, history_df: pd.DataFrame, test_count: int = 50, bets_per_issue: int = 1, progress_callback=None):
        results = []
        if len(history_df) < test_count + 10:
            return pd.DataFrame() 
            
        start_idx = len(history_df) - test_count
        total_steps = len(history_df) - start_idx
        
        for idx_step, i in enumerate(range(start_idx, len(history_df))):
            # Update progress
            if progress_callback:
                progress_callback(idx_step / total_steps)
                
            history_subset = history_df.iloc[:i]
            current_row = history_df.iloc[i]
            
            # Extract actual
            if game_type == GameType.SSQ:
                act_reds = [int(current_row[f'red{j}']) for j in range(1, 7)]
                act_blues = [int(current_row['blue'])]
            elif game_type == GameType.DLT:
                act_reds = [int(current_row[f'red{j}']) for j in range(1, 6)]
                act_blues = [int(current_row[f'blue{j}']) for j in range(1, 3)]
                
            # Predict multiple bets
            issue_prizes = 0
            issue_hits_summary = []
            
            # IMPORTANT: For backtesting, we should NOT use a fixed seed based on today's date,
            # otherwise every backtest step would produce the same numbers if not handled carefully.
            # But we want randomness relative to the 'issue' being tested.
            # Let's seed based on issue number to make backtest reproducible but different per issue.
            
            # However, strategy_func signature in main.py might not accept seed if we pass the raw function.
            # We need to handle arguments.
            # Simple hack: check if strategy_func accepts seed, or wrap it.
            # But composite_predict is a static method.
            
            for k in range(bets_per_issue):
                try:
                    # Pass seed if it's composite_predict
                    if strategy_func == Predictor.composite_predict:
                        # Seed = Issue Number + Bet Index
                        current_seed = int(current_row['issue']) + k
                        pred_reds, pred_blues = strategy_func(game_type, history_subset, seed=current_seed)
                    else:
                        # Other strategies might not accept seed yet, update them?
                        # For now assume others are random enough or don't support seed in this call
                        # We can inspect or just try/except
                         pred_reds, pred_blues = strategy_func(game_type, history_subset)

                except TypeError:
                     # Fallback for functions that don't take seed
                     pred_reds, pred_blues = strategy_func(game_type, history_subset)
                except Exception as e:
                    print(f"Prediction failed at index {i}: {e}")
                    continue
                
                # Check hits
                red_hits = len(set(pred_reds) & set(act_reds))
                blue_hits = len(set(pred_blues) & set(act_blues))
                
                # Calculate Prize
                prize_res = PrizeCalculator.calculate(game_type, red_hits, blue_hits)
                issue_prizes += prize_res.amount
                issue_hits_summary.append(f"{red_hits}+{blue_hits}")
            
            cost = 2 * bets_per_issue # 2 RMB per bet
            
            results.append({
                'issue': current_row['issue'],
                'bets_count': bets_per_issue,
                'cost': cost,
                'prize': issue_prizes,
                'net_profit': issue_prizes - cost,
                'hits_summary': ", ".join(issue_hits_summary[:5]) + ("..." if bets_per_issue > 5 else ""),
                'actual': (act_reds, act_blues)
            })
            
        return pd.DataFrame(results)
