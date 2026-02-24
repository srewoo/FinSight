import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

def compute_fibonacci_levels(df: pd.DataFrame, period: int = 120) -> Dict[str, Optional[float]]:
    """
    Calculate Fibonacci retracement levels based on the high and low over the given period.
    Default period of 120 days (~6 months) is used for significant swing points.
    """
    if df.empty or len(df) < 5:
        return {}

    # Use the relevant subset of data for the swing high/low
    historical_data = df.tail(min(len(df), period))
    
    swing_high = float(historical_data['High'].max())
    swing_low = float(historical_data['Low'].min())
    
    if pd.isna(swing_high) or pd.isna(swing_low) or swing_high == swing_low:
        return {}

    diff = swing_high - swing_low

    # Traditional Fibonacci levels
    levels = {
        "level_0": round(swing_high, 2),                  # 0.0%
        "level_23_6": round(swing_high - 0.236 * diff, 2), # 23.6%
        "level_38_2": round(swing_high - 0.382 * diff, 2), # 38.2%
        "level_50_0": round(swing_high - 0.5 * diff, 2),   # 50.0%
        "level_61_8": round(swing_high - 0.618 * diff, 2), # 61.8%
        "level_78_6": round(swing_high - 0.786 * diff, 2), # 78.6%
        "level_100": round(swing_low, 2),                  # 100.0%
    }
    
    return {
        "swing_high": round(swing_high, 2),
        "swing_low": round(swing_low, 2),
        "levels": levels
    }

def compute_volume_profile_poc(df: pd.DataFrame, bins: int = 20) -> Optional[float]:
    """
    Approximates the Volume Profile Point of Control (POC).
    Groups historical prices into `bins` and finds the price bucket with the highest total volume.
    Returns the median price of that highest-volume bin.
    """
    if df.empty or 'Volume' not in df.columns or len(df) < 10:
        return None
        
    # Drop rows without volume or price
    valid_data = df.dropna(subset=['Close', 'Volume']).copy()
    if valid_data.empty:
        return None

    # Calculate price range and create bins
    min_price = valid_data['Low'].min()
    max_price = valid_data['High'].max()
    
    if min_price == max_price or pd.isna(min_price) or pd.isna(max_price):
        return None

    # Cut the closing prices into bins
    price_bins = pd.cut(valid_data['Close'], bins=bins)
    
    # Sum the volume for each bin
    volume_by_price = valid_data.groupby(price_bins, observed=False)['Volume'].sum()
    
    # Find the bin with the highest volume (Point of Control)
    poc_bin = volume_by_price.idxmax()
    
    # If POC bin is null or invalid
    if pd.isna(poc_bin):
        return None
        
    # The POC price is approximately the middle of that bin
    poc_price = poc_bin.mid
    
    return round(float(poc_price), 2)
