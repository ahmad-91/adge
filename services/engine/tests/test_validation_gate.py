from __future__ import annotations

from application.use_cases.run_validation import RunValidationProtocol, ValidationRequestDTO
from adapters.outbound.data.options_history import NullOptionsHistory
from adapters.outbound.pricing.black_scholes_adapter import BlackScholesAdapter


def test_validation_without_data_is_unvalidatable():
    uc = RunValidationProtocol(NullOptionsHistory(), BlackScholesAdapter())
    report = uc.execute(ValidationRequestDTO(min_trades=10))
    assert report.status == "UNVALIDATABLE"
    assert report.phase_a_ok is False
