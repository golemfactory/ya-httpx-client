import logging
import os
from pathlib import Path
from typing import List

import pytest

from goth.configuration import load_yaml, Override
from goth.runner.log import configure_logging
from goth.runner import Runner
from goth.runner.probe import RequestorProbe

from .assertions import assert_no_errors


logger = logging.getLogger("goth.test.run_echo_server")


@pytest.mark.asyncio
async def test_run_echo_server(
    project_dir: Path, log_dir: Path, goth_config_path: Path
) -> None:
    goth_config = load_yaml(goth_config_path)
    requestor_script_path = project_dir / "tests" / "goth_tests" / "requestor_echo_server.py"
    configure_logging(log_dir)
    runner = Runner(
        base_log_dir=log_dir,
        compose_config=goth_config.compose_config,
    )

    async with runner(goth_config.containers):

        requestor = runner.get_probes(probe_type=RequestorProbe)[0]

        async with requestor.run_command_on_host(
            f"{requestor_script_path} goth",
            env=os.environ,
        ) as (_cmd_task, cmd_monitor):
            cmd_monitor.add_assertion(assert_no_errors)
            logger.info("Requestor script finished")
