import math
from typing import List

def dot_product(v1: List[float], v2: List[float]) -> float:
    return sum(a * b for a, b in zip(v1, v2))

def magnitude(v: List[float]) -> float:
    return math.sqrt(sum(a * a for a in v))

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    mag = magnitude(v1) * magnitude(v2)
    if mag == 0:
        return 0.0
    return dot_product(v1, v2) / mag

def distance(v1: List[float], v2: List[float]) -> float:
    # Uses 1 - cosine_similarity to represent angular distance
    return 1.0 - cosine_similarity(v1, v2)
