import math


def dot_product(v1: list[float], v2: list[float]) -> float:
    return sum(a * b for a, b in zip(v1, v2))


def magnitude(v: list[float]) -> float:
    return math.sqrt(sum(a * a for a in v))


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    mag = magnitude(v1) * magnitude(v2)
    if mag == 0:
        return 0.0
    return dot_product(v1, v2) / mag


def distance(v1: list[float], v2: list[float]) -> float:
    # Uses 1 - cosine_similarity to represent angular distance
    return 1.0 - cosine_similarity(v1, v2)
