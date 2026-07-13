"""Unit tests for the evaluation statistics against textbook values."""
import math

from trustgrade.stats import wilson_ci, mcnemar_exact, fisher_exact, cohen_kappa


def test_wilson_known_interval():
    # 84/85: Wilson 95% CI ~ [0.9363, 0.9979] (matches R binom::binom.confint,
    # method="wilson"). Note this is the Wilson score bound, not Clopper-Pearson.
    lo, hi = wilson_ci(84, 85)
    assert abs(lo - 0.9363) < 0.01
    assert abs(hi - 0.9979) < 0.01


def test_wilson_boundary_zero():
    lo, hi = wilson_ci(0, 85)
    assert lo == 0.0
    assert 0.0 < hi < 0.06  # one-sided upper bound near 4.3%


def test_mcnemar_exact_symmetry_and_value():
    # b=9, c=0 discordants -> two-sided exact p = 2 * 0.5^9 = 0.0039.
    p = mcnemar_exact(9, 0)
    assert abs(p - 2 * 0.5 ** 9) < 1e-9
    assert mcnemar_exact(3, 3) == 1.0
    assert mcnemar_exact(0, 0) == 1.0


def test_fisher_exact_classic_table():
    # Fisher's tea-tasting [[3,1],[1,3]] -> two-sided p ~ 0.486.
    p = fisher_exact(3, 1, 1, 3)
    assert abs(p - 0.4857) < 0.01


def test_fisher_exact_extreme_table():
    # [[85,0],[0,137]] perfectly separated -> p far below 1e-10.
    assert fisher_exact(85, 0, 0, 137) < 1e-10


def test_cohen_kappa_perfect_and_chance():
    assert abs(cohen_kappa(50, 0, 0, 50) - 1.0) < 1e-9
    # independent 50/50 raters -> kappa ~ 0
    assert abs(cohen_kappa(25, 25, 25, 25)) < 1e-9
