import abc

from ..models.read_models import TrendAnalysisRead, TrendPointRead


class TrendAnalyzer(abc.ABC):
    """
    Responsibilities:
    - computing rolling averages
    - weekly/monthly trends
    - regressions
    - improvements
    """

    @abc.abstractmethod
    def analyze(self, data_points: list[TrendPointRead]) -> TrendAnalysisRead:
        pass


class SimpleMovingAverageAnalyzer(TrendAnalyzer):
    def __init__(self, window_size: int = 3):
        self.window_size = window_size

    def analyze(self, data_points: list[TrendPointRead]) -> TrendAnalysisRead:
        # Sort points by timestamp
        sorted_points = sorted(data_points, key=lambda x: x.timestamp)

        ma_points = []
        for i in range(len(sorted_points)):
            if i < self.window_size - 1:
                ma_points.append(
                    TrendPointRead(
                        timestamp=sorted_points[i].timestamp, value=sorted_points[i].value
                    )
                )
            else:
                window = sorted_points[i - self.window_size + 1 : i + 1]
                avg = sum(p.value for p in window) / self.window_size
                ma_points.append(TrendPointRead(timestamp=sorted_points[i].timestamp, value=avg))

        return TrendAnalysisRead(
            metric_name="simple_moving_average", points=sorted_points, moving_average=ma_points
        )
