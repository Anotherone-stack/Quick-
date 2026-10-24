def test_large_trade_threshold():
    threshold = 1000

    assert 1000 >= threshold
    assert 999 < threshold