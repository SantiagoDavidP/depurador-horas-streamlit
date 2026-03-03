"""Backend package for the timesheet depuration system."""

from backend.application.processing.models import ProcessorResult
from backend.application.processing.service import TimeSheetProcessor

__all__ = ["ProcessorResult", "TimeSheetProcessor"]
