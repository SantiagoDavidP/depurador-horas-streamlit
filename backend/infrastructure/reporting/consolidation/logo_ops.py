from __future__ import annotations

from ._logo_anchor import LogoAnchorMixin
from ._logo_header import LogoHeaderMixin
from ._logo_normalize_a import LogoNormalizeAMixin
from ._logo_normalize_b import LogoNormalizeBMixin
from ._logo_paths import LogoPathsMixin


class LogoOpsMixin(
    LogoPathsMixin,
    LogoAnchorMixin,
    LogoHeaderMixin,
    LogoNormalizeAMixin,
    LogoNormalizeBMixin,
):
    pass


__all__ = ["LogoOpsMixin"]
