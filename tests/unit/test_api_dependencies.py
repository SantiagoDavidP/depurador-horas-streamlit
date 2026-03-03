from api.presentation import dependencies


def test_get_individual_thread_processor_reuses_instance(monkeypatch):
    class _ProcessorStub:
        def __init__(self, expected_hours_per_day=8.0, role_validator=None):
            self.expected_hours = expected_hours_per_day
            self.role_validator = role_validator

    dependencies._individual_processor_tls = type("TLS", (), {})()
    dependencies.processor = _ProcessorStub(expected_hours_per_day=7.5, role_validator="rv")
    monkeypatch.setattr(dependencies, "TimeSheetProcessor", _ProcessorStub)

    p1 = dependencies.get_individual_thread_processor()
    p2 = dependencies.get_individual_thread_processor()
    assert p1 is p2
    assert p1.expected_hours == 7.5
    assert p1.role_validator == "rv"
