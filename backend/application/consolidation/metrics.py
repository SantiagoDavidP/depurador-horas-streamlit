from __future__ import annotations

from ._metrics_cleanup import MetricsCleanupMixin
from ._metrics_extract import MetricsExtractMixin
from ._metrics_rates import MetricsRatesMixin


class MetricsMixin(MetricsExtractMixin, MetricsCleanupMixin, MetricsRatesMixin):
    pass


__all__ = ["MetricsMixin"]
