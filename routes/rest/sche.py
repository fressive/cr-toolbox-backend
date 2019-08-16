import flask_restful as restful
from flask import Response, jsonify
from flask_restful import reqparse
from helpers import trainHelper

get_parser = reqparse.RequestParser()
get_parser.add_argument('train', type=str, required=True)
get_parser.add_argument('date', type=str, required=False)

class Scheduler(restful.Resource):
    def get(self):
        train = get_parser.parse_args().get('train')
        date = get_parser.parse_args().get('date')

        code, data = trainHelper.getScheduler(train, date)

        return jsonify({
            "code": code,
            "data": data
        })
