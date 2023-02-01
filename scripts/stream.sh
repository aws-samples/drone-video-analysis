# start streaming a local video to the rtsp proxy server
# ffmpeg is a cross-platform solution to record, convert and stream audio and video
# stream the video called drone.mp4 in a loop to the proxy server
ffmpeg -re -stream_loop -1 -i <videofile.mp4> -c copy -f flv \
  rtmp://<ip-address>:1935/__stream_name__