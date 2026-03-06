from __future__ import annotations

from ._footer_builder import FooterBuilderMixin
from ._individual_business import IndividualBusinessMixin
from ._individual_nova import IndividualNovaMixin


class IndividualSheetMixin(FooterBuilderMixin, IndividualBusinessMixin, IndividualNovaMixin):
    pass


__all__ = ["IndividualSheetMixin"]
