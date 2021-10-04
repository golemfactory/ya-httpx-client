from datetime import datetime, timezone
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def project_dir() -> Path:
    package_dir = Path(__file__).parent.parent
    return package_dir.parent.resolve()


@pytest.fixture(scope="session")
def log_dir() -> Path:
    base_dir = Path("/", "tmp", "goth-tests")
    date_str = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S%z")
    dir_ = base_dir / f"goth_{date_str}"
    dir_.mkdir(parents=True)
    return dir_


@pytest.fixture(scope="session")
def goth_config_path(project_dir) -> Path:  # pylint: disable=W0621
    return project_dir / "tests" / "goth_tests" / "assets" / "goth-config.yml"
