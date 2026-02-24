"""
backend/tests/test_options.py — Phase 3.3: Black-Scholes + Max Pain tests
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import math


class TestBlackScholesGreeks:
    def _greeks(self, S, K, T, sigma, option_type, r=0.065):
        try:
            from options import black_scholes_greeks
            return black_scholes_greeks(S, K, T, r, sigma, option_type)
        except ImportError:
            pytest.skip("scipy not installed")

    def test_call_delta_atm(self):
        g = self._greeks(S=500, K=500, T=30/365, sigma=0.25, option_type="CE")
        assert 0.4 < g["delta"] < 0.6   # ATM call delta ≈ 0.5

    def test_put_delta_atm(self):
        g = self._greeks(S=500, K=500, T=30/365, sigma=0.25, option_type="PE")
        assert -0.6 < g["delta"] < -0.4  # ATM put delta ≈ -0.5

    def test_deep_itm_call_delta_near_1(self):
        g = self._greeks(S=600, K=400, T=30/365, sigma=0.20, option_type="CE")
        assert g["delta"] > 0.9

    def test_deep_otm_call_delta_near_0(self):
        g = self._greeks(S=400, K=600, T=30/365, sigma=0.20, option_type="CE")
        assert g["delta"] < 0.05

    def test_theta_is_negative_for_long_call(self):
        g = self._greeks(S=500, K=500, T=30/365, sigma=0.25, option_type="CE")
        assert g["theta"] < 0  # theta is always negative for long options

    def test_vega_positive(self):
        g = self._greeks(S=500, K=500, T=30/365, sigma=0.25, option_type="CE")
        assert g["vega"] > 0

    def test_at_expiry(self):
        g = self._greeks(S=550, K=500, T=0, sigma=0.25, option_type="CE")
        assert g["price"] == pytest.approx(50.0, abs=0.01)  # intrinsic value
        assert g["theta"] == 0.0

    def test_put_call_parity(self):
        """C - P = S - K * e^(-rT) (put-call parity)"""
        S, K, T, sigma, r = 500, 500, 30/365, 0.25, 0.065
        c = self._greeks(S, K, T, sigma, "CE", r)
        p = self._greeks(S, K, T, sigma, "PE", r)
        lhs = c["price"] - p["price"]
        rhs = S - K * math.exp(-r * T)
        assert abs(lhs - rhs) < 1.0  # within ₹1


class TestMaxPain:
    def _max_pain(self, chain):
        from options import calculate_max_pain
        return calculate_max_pain(chain)

    def test_simple_case(self):
        chain = [
            {"strike_price": 500.0, "option_type": "CE", "open_interest": 1000},
            {"strike_price": 500.0, "option_type": "PE", "open_interest": 2000},
            {"strike_price": 600.0, "option_type": "CE", "open_interest": 3000},
            {"strike_price": 600.0, "option_type": "PE", "open_interest": 500},
        ]
        result = self._max_pain(chain)
        assert result is not None
        assert result in [500.0, 600.0]

    def test_empty_chain(self):
        result = self._max_pain([])
        assert result is None

    def test_single_strike(self):
        chain = [{"strike_price": 500.0, "option_type": "CE", "open_interest": 1000}]
        result = self._max_pain(chain)
        assert result is None  # single strike = cannot compute meaningfully
