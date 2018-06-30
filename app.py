import os
from flask import Flask
from file_converter import Converter

app = Flask(__name__)


@app.route("/")
def home():
    return "Hello world"


@app.route("/fanfiction_epub/<story_id>", methods=["GET", "POST"])
def fanfic_to_epub(story_id):
    convert = Converter(int(story_id))
    convert.convert_to_epub()
    return "Done converting"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # app.run(host='0.0.0.0', port=port, threaded=True)
    app.run(debug=True)
