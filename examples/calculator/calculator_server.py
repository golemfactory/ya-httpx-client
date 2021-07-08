from flask import Flask

app = Flask(__name__)


@app.route('/add/<int:a>/<int:b>', methods=['GET'])
def add(a, b):
    return str(a + b), 200
