import pytest
import pandas as pd
from backend.math_utils import compute_fibonacci_levels, compute_volume_profile_poc

def test_compute_fibonacci_levels():
    # Arrange
    data = {
        'High': [100, 110, 120, 150, 140, 130],
        'Low': [90, 80, 100, 130, 120, 110]
    }
    df = pd.DataFrame(data)

    # Act
    result = compute_fibonacci_levels(df)

    # Assert
    assert result != {}
    assert result['swing_high'] == 150.0
    assert result['swing_low'] == 80.0
    
    diff = 150.0 - 80.0 # 70
    assert result['levels']['level_0'] == 150.0
    assert result['levels']['level_100'] == 80.0
    # Floating point comparison
    assert round(result['levels']['level_50_0'], 2) == round(150.0 - 0.5 * diff, 2)
    assert round(result['levels']['level_61_8'], 2) == round(150.0 - 0.618 * diff, 2)

def test_compute_fibonacci_empty_df():
    df = pd.DataFrame()
    assert compute_fibonacci_levels(df) == {}

def test_compute_volume_profile_poc():
    # Arrange
    data = {
        'High': [10, 20, 30, 40, 50],
        'Low': [5, 15, 25, 35, 45],
        'Close': [8, 18, 28, 38, 48],
        'Volume': [100, 500, 1000, 200, 50] # 28 is the POC (highest volume)
    }
    # Duplicate data to satisfy len requirement > 10
    df = pd.DataFrame(data).sample(n=15, replace=True, random_state=42)
    
    # We force the highest volume on a specific price point
    df.loc[15] = [30, 25, 28, 50000] # Inject massive volume at close=28

    # Act
    poc = compute_volume_profile_poc(df, bins=10)

    # Assert
    assert poc is not None
    # the POC should be very close to 28 based on the bins
    assert 25 <= poc <= 31

def test_compute_volume_profile_poc_empty():
    df = pd.DataFrame()
    assert compute_volume_profile_poc(df) is None
