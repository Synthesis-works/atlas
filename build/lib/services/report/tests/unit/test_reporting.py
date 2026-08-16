from datetime import datetime

from services.report.models.read_models import TrendPointRead
from services.report.strategies.trends import SimpleMovingAverageAnalyzer


def test_simple_moving_average():
    analyzer = SimpleMovingAverageAnalyzer(window_size=3)
    points = [
        TrendPointRead(timestamp=datetime(2023, 1, 1), value=10.0),
        TrendPointRead(timestamp=datetime(2023, 1, 2), value=20.0),
        TrendPointRead(timestamp=datetime(2023, 1, 3), value=30.0),
        TrendPointRead(timestamp=datetime(2023, 1, 4), value=40.0),
    ]

    analysis = analyzer.analyze(points)

    assert analysis.metric_name == "simple_moving_average"
    assert len(analysis.moving_average) == 4

    # First two points don't have enough data for window size 3
    assert analysis.moving_average[0].value == 10.0
    assert analysis.moving_average[1].value == 20.0

    # 3rd point: (10 + 20 + 30) / 3 = 20
    assert analysis.moving_average[2].value == 20.0

    # 4th point: (20 + 30 + 40) / 3 = 30
    assert analysis.moving_average[3].value == 30.0
