import math
from typing import Tuple

def binomial_confidence_interval_95(successes: int, n: int) -> Tuple[float, float, float]:
    """
    Computes the Wilson score interval for a binomial proportion at 95% confidence.
    Returns: (proportion, lower_bound, upper_bound)
    """
    if n == 0:
        return 0.0, 0.0, 0.0
        
    p = successes / n
    z = 1.96 # 95% confidence
    
    denominator = 1 + z**2/n
    centre_adjusted_probability = p + z**2 / (2*n)
    adjusted_standard_deviation = math.sqrt((p*(1 - p) + z**2 / (4*n)) / n)
    
    lower_bound = (centre_adjusted_probability - z * adjusted_standard_deviation) / denominator
    upper_bound = (centre_adjusted_probability + z * adjusted_standard_deviation) / denominator
    
    # Bound between 0 and 1
    lower_bound = max(0.0, lower_bound)
    upper_bound = min(1.0, upper_bound)
    
    return p, lower_bound, upper_bound
    
def format_ci(successes: int, n: int) -> str:
    p, lower, upper = binomial_confidence_interval_95(successes, n)
    return f"{p*100:.1f}% [{lower*100:.1f}%, {upper*100:.1f}%]"
