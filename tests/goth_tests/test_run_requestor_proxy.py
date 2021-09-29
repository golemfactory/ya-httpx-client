import asyncio
import logging
import os
from pathlib import Path

import pytest

from goth.configuration import load_yaml
from goth.runner.log import configure_logging
from goth.runner import Runner
from goth.runner.probe import RequestorProbe

from .assertions import assert_no_errors

import requests

from ..sample_requests import sample_requests
from ..utils import assert_requests_equal

logger = logging.getLogger("goth.test.run_proxy")


@pytest.fixture(scope='module')
def event_loop():
    """This overrides `pytest.asyncio` fixture"""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='module')
async def requestor_proxy(
    project_dir: Path, log_dir: Path, goth_config_path: Path
) -> None:
    """Test function that uses this fixture will be able to communicate with
    `examples/requestor_proxy/requestor_proxy.py` script running in a goth subnet"""

    goth_config = load_yaml(goth_config_path)
    requestor_script_path = project_dir / "examples" / "requestor_proxy" / "requestor_proxy.py"
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
        ) as (cmd_task, cmd_monitor):
            cmd_monitor.add_assertion(assert_no_errors)

            await cmd_monitor.wait_for_pattern(".*STARTED ON provider.*", timeout=200)
            logger.info("STARTED!")

            yield

            #   TODO - how to stop the server gracefully?
            #   Now ctrl+C does this.


@pytest.mark.parametrize('src_req', sample_requests)
def test_correct_request(requestor_proxy, src_req: requests.Request):
    """Send a request to the echo server. Expect 200 and data that will contain
    all the information necessary to recreate the source request.
    This assumes `src_req.url` matches the echo url, this is not checked"""
    prepped = src_req.prepare()
    session = requests.Session()

    res = session.send(prepped)
    assert res.status_code == 200

    echo_data = res.json()
    assert echo_data.get('echo') == 'echo'

    echo_req = requests.Request(**echo_data['req'])

    assert_requests_equal(src_req, prepped, echo_req)


def test_404(requestor_proxy):
    res = requests.get('http://localhost:5000/nope')
    assert res.status_code == 404


def test_405(requestor_proxy):
    res = requests.post('http://localhost:5000')
    assert res.status_code == 405


def test_500(requestor_proxy):
    res = requests.get('http://localhost:5000/bug')
    assert res.status_code == 500


def test_headers(requestor_proxy):
    res = requests.get('http://localhost:5000/echo/')
    assert res.status_code == 200

    #   NOTE: those headers are also modified by locally running requestor_proxy
    #   (e.g. `hypercorn-h11` server header is added).
    expected_headers = {
        'server': 'gunicorn, hypercorn-h11',
        'date': '*',
        'connection': 'close',
        'content-type': 'application/json',
        'content-length': '*',
    }

    got_headers = dict(res.headers)
    assert set(expected_headers.keys()) == set(got_headers.keys())
    for key, val in expected_headers.items():
        if val != '*':
            assert got_headers[key] == val


def test_headers_2(requestor_proxy):
    res = requests.get('http://localhost:5000')
    assert res.status_code == 200
    assert res.headers.get('foo') == 'bar'
