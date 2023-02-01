# Basic flask app

from flask import Flask, request, jsonify
import os

app = Flask(__name__)


@app.route("/trigger", methods=["POST"])
def trigger():
    print("request data", request.data)
    print("request json", request.json)
    # Basically run the command ./kvs_gstreamer_sample teststream rtsp://localhost:8554/mystream
    # in the terminal as a subprocess
    # and then return the url
    kinesis_stream_name = request.json.get("kinesis_stream_name", "teststream")
    rtsp_src = request.json.get("rtsp_src", "rtsp://rtspserver:8554/mystream")
    command = f"./kvs_gstreamer_sample {kinesis_stream_name} {rtsp_src} &"
    os.system(command)
    return jsonify({"message": "success"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
