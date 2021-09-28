from flask import Flask
from ya_httpx_client.serializable_request import Request

HTTP_METHODS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH']
app = Flask(__name__)


@app.route('/', methods=['GET'])
def hello():
    #  Response includes some random header for testing purposes
    return "Hi, this is an echo server", 200, {'Foo': 'bar'}


@app.route('/bug', methods=['GET'])
def oops():
    1 / 0  # ooops --> checks if 500 is handled correctly


@app.route('/echo/', defaults={'_path': ''}, methods=HTTP_METHODS)
@app.route('/echo/<path:_path>', methods=HTTP_METHODS)
def echo(_path):
    '''Whole request is returned (including headers etc) to simplify testing.'''
    req = Request.from_flask_request()
    out_data = {
        'echo': 'echo',
        'req': req.as_dict(),
    }
    return out_data, 200
