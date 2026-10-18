import os
import sys

import responsible_receivables_agent


def test_package_imports() -> None:
    assert responsible_receivables_agent.__version__ == "0.1.0"


def test_python_version_and_offline_env() -> None:
    assert sys.version_info[:2] >= (3, 12)
    # The smoke test must not depend on credentials.
    assert os.environ.get("ALLOW_EXTERNAL_CALLS", "false").lower() != "true"
