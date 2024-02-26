from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({"Choo Choo": "Welcome to your Flask app 🚅"})


@app.route('/test', methods=['POST'])
def process_data():

    gameStage = req_data['gameStage']



    return jsonify({
        "gameStage": gameStage
    })

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=5000)
