import config
from flask import Flask
from flask_cors import CORS
from flask_restful import Api
from routes.router import route

app = Flask(import_name='cr-toolbox Backend')
cors = CORS(app, resources={r"/api/v1/*": {"origins": "*"}})
api = Api(app)

def main():
    route(api)
    app.run(port=config.port)

if __name__ == '__main__':
    main()
