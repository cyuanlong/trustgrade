"""Statistics for the evaluation (§5.3).

Small, dependency-light implementations of the paired/proportion tests the paper
reports: Wilson score intervals for proportions, the exact McNemar test on
paired discordants, Fisher's exact test on 2x2 tables, and Cohen's kappa for
inter-rater agreement. Exact (not asymptotic) variants are used because several
cells in the paper are small.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


# ----------------------------------------------------------------------------- #
# Wilson score interval
# ----------------------------------------------------------------------------- #
@dataclass
class Proportion:
    k: int
    n: int

    @property
    def p(self) -> float:
        return self.k / self.n if self.n else float("nan")


def wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score 95% CI for a binomial proportion k/n.

    Preferred over the normal approximation near 0 and 1, which is exactly where
    the paper's safety proportions live (e.g. 84/85, 0/85).
    """
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


# ----------------------------------------------------------------------------- #
# Exact McNemar test (paired binary outcomes)
# ----------------------------------------------------------------------------- #
def _binom_pmf(k: int, n: int, p: float = 0.5) -> float:
    return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the discordant counts b, c.

    b, c are the off-diagonal cells of the paired 2x2 table (cases where the two
    conditions disagree). Under H0 each discordant pair is a fair coin; the exact
    p-value is the two-sided binomial tail. Used for the paired arm comparisons
    (e.g. full gate vs test-only on identical items).
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(_binom_pmf(i, n) for i in range(0, k + 1))
    return min(1.0, 2 * tail)


# ----------------------------------------------------------------------------- #
# Fisher's exact test (2x2)
# ----------------------------------------------------------------------------- #
def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p-value for the 2x2 table [[a, b], [c, d]].

    Sums the hypergeometric probabilities of all tables with the same margins
    that are no more probable than the observed one.
    """
    n = a + b + c + d
    row1, col1 = a + b, a + c

    def hg(x: int) -> float:
        # P(top-left = x) given the fixed margins.
        return (
            math.comb(col1, x)
            * math.comb(n - col1, row1 - x)
            / math.comb(n, row1)
        )

    p_obs = hg(a)
    lo = max(0, row1 + col1 - n)
    hi = min(row1, col1)
    tol = 1e-12
    return min(1.0, sum(hg(x) for x in range(lo, hi + 1) if hg(x) <= p_obs + tol))


# ----------------------------------------------------------------------------- #
# Cohen's kappa (inter-rater agreement)
# ----------------------------------------------------------------------------- #
def cohen_kappa(a: int, b: int, c: int, d: int) -> float:
    """Cohen's kappa for two raters on a binary label, table [[a, b], [c, d]].

    a = both positive, d = both negative, b/c = disagreements. Used for
    decision-stability of the frontier reviewer across its two runs.
    """
    n = a + b + c + d
    if n == 0:
        return float("nan")
    po = (a + d) / n
    p_pos = ((a + b) / n) * ((a + c) / n)
    p_neg = ((c + d) / n) * ((b + d) / n)
    pe = p_pos + p_neg
    return (po - pe) / (1 - pe) if pe != 1 else 1.0
