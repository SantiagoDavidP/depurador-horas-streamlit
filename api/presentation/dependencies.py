from __future__ import annotations

import threading

from api.infrastructure.auth.azure_ad_user_auth_adapter import AzureADUserAuthAdapter
from api.infrastructure.storage.in_memory_file_store_adapter import InMemoryFileStoreAdapter
from backend.batch_processor import BatchProcessor
from backend.processor import TimeSheetProcessor

processor = TimeSheetProcessor()
batch_processor = BatchProcessor(processor)
_individual_processor_tls = threading.local()
auth_provider = AzureADUserAuthAdapter()
file_store = InMemoryFileStoreAdapter()


def get_individual_thread_processor() -> TimeSheetProcessor:
    thread_processor = getattr(_individual_processor_tls, "processor", None)
    if thread_processor is None:
        thread_processor = TimeSheetProcessor(
            expected_hours_per_day=processor.expected_hours,
            role_validator=processor.role_validator,
        )
        _individual_processor_tls.processor = thread_processor
    return thread_processor
