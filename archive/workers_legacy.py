"""
workers.py

Module containing picklable CPU-bound worker functions intended to be submitted
to a ProcessPoolExecutor. Keep functions at module top-level so they are
picklable by multiprocessing.
"""

import math

def heavy_work(n):
    """CPU-bound work: compute sum of squares up to n to simulate load.
    Returns the computed sum.
    """
    s = 0
    for i in range(1, n + 1):
        s += i * i
    return s

def cpu_heavy_prime_count(limit):
    """Count primes up to `limit` (naive) to generate CPU load."""
    def is_prime(x):
        if x < 2:
            return False
        if x % 2 == 0:
            return x == 2
        r = int(math.sqrt(x))
        i = 3
        while i <= r:
            if x % i == 0:
                return False
            i += 2
        return True
    count = 0
    for k in range(2, limit + 1):
        if is_prime(k):
            count += 1
    return count
