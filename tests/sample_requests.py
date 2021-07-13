from httpx import Request

SAMPLE_URL = "http://hi.my.name.is.golem"

sample_requests = [
    Request("GET", SAMPLE_URL + '/add/1/2'),
    Request("GET", SAMPLE_URL + '/add/2/3'),
]
