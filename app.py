import os
from flask import Flask, send_file, request, jsonify, json
from file_converter import Converter
from fanfiction_net_api import *

app = Flask(__name__)


@app.route("/")
def home():
    return "Hello world"


@app.route("/fanfiction_epub/<story_id>", methods=["GET", "POST"])
def fanfic_to_epub(story_id):
    convert = Converter(int(story_id))
    path = convert.convert_to_epub()
    return send_file(path, as_attachment=True)


@app.route("/download_recs", methods=["GET"])
def get_fanfic_recs():
    download_num = request.args.get('downloads') or 0
    title = request.args.get('title') or 'Magi'
    medium = request.args.get('medium') or 'anime'
    character = request.args.get('character') or ""
    data = FanFiction.get_recommendations(title, medium=medium, character=character, download_num=int(download_num))
    response = app.response_class(
        response=json.dumps(data),
        status=200,
        mimetype='application/json'
    )
    return response


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
    # app.run(debug=True)
