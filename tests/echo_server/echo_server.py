from flask import Flask
from yagna_requests.serializable_request import Request

HTTP_METHODS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH']
app = Flask(__name__)


@app.route('/', defaults={'path': ''}, methods=HTTP_METHODS)
@app.route('/<path:path>', methods=HTTP_METHODS)
def echo(path):
    '''
    Whole request is returned (including headers etc) to simplify testing.
    Echo server has no non-testing purpose.
    '''
    req = Request.from_flask_request()
    out_data = {
        'echo': 'echo',
        'req': req.as_dict(),
    }
    return out_data, 200
