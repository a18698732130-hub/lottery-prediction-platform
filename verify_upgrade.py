from core.prize import PrizeCalculator
from core.storage import Storage
from core.analysis import Predictor, calculate_omission
from core.lottery import GameType
from core.data import DataLoader
import os

def test_prize():
    print("Testing Prize Calculator...")
    # SSQ 6+1
    res = PrizeCalculator.calc_ssq(6, 1)
    assert res.amount == 10000000, f"SSQ 6+1 should be 10000000, got {res.amount}"
    
    # DLT 5+2
    res = PrizeCalculator.calc_dlt(5, 2)
    assert res.amount == 10000000, f"DLT 5+2 should be 10000000, got {res.amount}"
    print("✅ Prize Calculator Passed")

def test_storage():
    print("\nTesting Storage...")
    storage = Storage()
    test_id = "test_bet_1"
    # Clean up previous test
    df = storage.load_bets()
    
    storage.save_bet(GameType.SSQ, "2023001", [1,2,3,4,5,6], [1], "Test Note")
    df = storage.load_bets()
    assert not df.empty, "Storage should not be empty after save"
    print("✅ Storage Save Passed")

def test_strategies():
    print("\nTesting Strategies...")
    dl = DataLoader()
    df = dl.load_data(GameType.SSQ)
    
    print("Testing Omission Predict...")
    reds, blues = Predictor.omission_predict(GameType.SSQ, df)
    assert len(reds) == 6
    assert len(blues) == 1
    print(f"Omission Prediction: {reds} + {blues}")
    
    print("Testing Golden Sum Predict...")
    reds, blues = Predictor.golden_sum_predict(GameType.SSQ, df)
    s = sum(reds)
    assert 90 <= s <= 120, f"Golden Sum {s} not in range 90-120"
    print(f"Golden Sum Prediction: {reds} + {blues} (Sum: {s})")
    print("✅ Strategies Passed")

if __name__ == "__main__":
    try:
        test_prize()
        test_storage()
        test_strategies()
        print("\n🎉 All Verification Tests Passed!")
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
