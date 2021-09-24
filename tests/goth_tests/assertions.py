from goth.assertions import EventStream


async def assert_no_errors(output_lines: EventStream[str]):
    """Assert that no output line contains the substring `ERROR`."""
    async for line in output_lines:
        if "ERROR" in line:
            raise AssertionError("Command reported ERROR")
