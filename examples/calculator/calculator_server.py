from flask import Flask

app = Flask(__name__)


@app.route('/add/<int:x>/<int:y>', methods=['GET'])
def add(x, y):
    return str(x + y), 200
