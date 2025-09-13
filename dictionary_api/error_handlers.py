from flask import jsonify

from . import app


class InvalidApi(Exception):
    status_code = 400

    def __init__(self, message, status_code=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self):
        return dict(error=self.message)


@app.errorhandler(InvalidApi)
def invalid_api_usage(error):
    return jsonify(error.to_dict()), error.status_code
