from statsmodels.stats.proportion import proportion_confint


def get_ci(count, n, alpha=0.05, method="wilson"):
    """
    count: Number of passes
    n: Total number of tests
    alpha: Significance level (default 0.05 for 95% CI)
    method: 'wilson' is best for all-around reliability
    """
    if n == 0:
        return 0.0, 0.0
    # Returns (lower_bound, upper_bound)
    low, high = proportion_confint(count, n, alpha=alpha, method=method)
    return low, high
