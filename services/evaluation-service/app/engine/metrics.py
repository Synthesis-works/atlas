from typing import List, Dict, Any
from app.pipelines.base import MetricValueModel

class MetricEngine:
    """
    Standardizing post-processor for pipeline metrics.
    Validates, normalizes, and aggregates MetricValueModels.
    """
    def __init__(self, validation_rules: Dict[str, Dict[str, Any]] = None):
        # validation_rules could define min/max for specific metric names
        self.validation_rules = validation_rules or {}

    def validate(self, metrics: List[MetricValueModel]) -> List[MetricValueModel]:
        """Validates metrics against rules (e.g. bounds checking)."""
        validated = []
        for metric in metrics:
            rules = self.validation_rules.get(metric.name, {})
            if "min_value" in rules and metric.value < rules["min_value"]:
                raise ValueError(f"Metric {metric.name} value {metric.value} is below minimum {rules['min_value']}")
            if "max_value" in rules and metric.value > rules["max_value"]:
                raise ValueError(f"Metric {metric.name} value {metric.value} is above maximum {rules['max_value']}")
            validated.append(metric)
        return validated

    def normalize(self, metrics: List[MetricValueModel]) -> List[MetricValueModel]:
        """Normalizes metrics to a standard 0.0 - 1.0 range where possible."""
        normalized_metrics = []
        for metric in metrics:
            # We assume we update the metric in place for this simple implementation
            # In a real app, normalized_value would be a separate field in the DB model.
            # Here MetricValueModel only has 'value', so we assume it represents the raw_value 
            # and normalization is stored elsewhere or we add it. 
            # Wait, the DB has raw_value and normalized_value. Let's add normalized_value to the model.
            if not hasattr(metric, 'normalized_value'):
                metric.normalized_value = metric.value
                
            rules = self.validation_rules.get(metric.name, {})
            if "min_value" in rules and "max_value" in rules:
                min_v = rules["min_value"]
                max_v = rules["max_value"]
                if max_v > min_v:
                    metric.normalized_value = (metric.value - min_v) / (max_v - min_v)
            normalized_metrics.append(metric)
        return normalized_metrics

    def aggregate(self, metrics: List[MetricValueModel]) -> List[MetricValueModel]:
        """Aggregates metrics (e.g., across multiple iterations or attempts).
        For this slice, if there are multiple metrics with the same name, we can compute the mean/sum based on aggregation rule.
        """
        grouped: Dict[str, List[MetricValueModel]] = {}
        for m in metrics:
            grouped.setdefault(m.name, []).append(m)

        aggregated = []
        for name, group in grouped.items():
            if len(group) == 1:
                aggregated.append(group[0])
                continue

            # Perform aggregation
            agg_type = group[0].aggregation
            if agg_type == "mean":
                avg = sum(m.value for m in group) / len(group)
                new_m = group[0].model_copy(update={"value": avg})
                if hasattr(new_m, 'normalized_value') and hasattr(group[0], 'normalized_value'):
                    new_m.normalized_value = sum(m.normalized_value for m in group) / len(group)
                aggregated.append(new_m)
            elif agg_type == "sum":
                total = sum(m.value for m in group)
                new_m = group[0].model_copy(update={"value": total})
                if hasattr(new_m, 'normalized_value') and hasattr(group[0], 'normalized_value'):
                    new_m.normalized_value = sum(m.normalized_value for m in group)
                aggregated.append(new_m)
            else:
                # Default to taking the last one if unsupported
                aggregated.append(group[-1])

        return aggregated

    def process(self, metrics: List[MetricValueModel]) -> List[MetricValueModel]:
        """Runs the full pipeline of validation, normalization, and aggregation."""
        validated = self.validate(metrics)
        normalized = self.normalize(validated)
        return self.aggregate(normalized)
