from __future__ import annotations

from ._postprocess_helpers import PostprocessHelpersMixin
from ._postprocess_main import PostprocessMainMixin


class PostprocessMixin(PostprocessHelpersMixin, PostprocessMainMixin):
    pass


__all__ = ["PostprocessMixin"]
