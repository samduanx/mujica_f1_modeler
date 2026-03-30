import pytest


class TestResults:
    """Lightweight TestResults fixture for pytest integration."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def record_pass(self, test_name: str):
        self.passed += 1

    def record_fail(self, test_name: str, reason: str):
        self.failed += 1
        self.errors.append((test_name, reason))


@pytest.fixture
def results():
    return TestResults()
