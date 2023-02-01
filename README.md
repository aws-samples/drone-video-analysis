This repository contains an application that lets you ingest live drone streams and process them in real time. The
application is built using the following technologies:

* Amazon Kinesis Video Streams
* Amazon Rekognition
* Lambda, S3, SNS

The solution has three big components; ingestion, processing of the video stream, and ML analysis of the video stream.

This solution is useful for processing real-time video streams from drones and other video sources. The solution can be
used to detect objects in the video stream, and send alerts to the user when an object is detected.

### CDK Deployment and Usage

The solution is packaged as a CDK stack. The stack be deployed by the following commands

```shell
cd cdk
npm install
cdk deploy
```

This spins up the required resources in your AWS account. The stack creates the following resources:

* Kinesis Video Stream
* Frames storage S3 bucket
* Lambda function to process the video stream
* Streaming Proxy Server to ingest the video stream into Kinesis Video Stream
* All required permissions, security groups, roles and networking resources

### Streaming a video stream

Once the solution is deployed, you can start streaming to the Kinesis Video Stream via the proxy server using your
streaming application (like DJI drone app).

To stream a sample video to the Kinesis Video Stream, you can use the following command:

```shell
ffmpeg -re -stream_loop -1 -i <videofile.mp4> -c copy -f flv \
  rtmp://<ip-address>:1935/__stream_name__
```

To obtain the IP address of the proxy server, you can refer to the CDK stack output.

Ensure a stream with the `__stream_name__` exists. You can use the `stream_name` output from the CDK stack.

### Lambda Configuration

The source code for the lambda function is located in `/cdk/lambda/s3-frame-analysis-trigger.py`

By default, this function will pick up images from the deployed S3 Bucket. It will run the images against the
Rekognition API and send an SNS notification if an object of interest is detected in the image.

If you want to use the custom model, uncomment the code between `Region: Custom model detection snippet`
and `End region` and update the `model_arn` variable with the ARN of your custom model.

Ensure you have configured the SNS topic as an environment variable in the lambda function.

### Custom  model

The following are useful resources to create a custom rekognition model:

* [Amazon Rekognition Custom Labels](https://docs.aws.amazon.com/rekognition/latest/customlabels-dg/what-is.html)
* [Getting started with Amazon Rekognition Custom Labels](https://docs.aws.amazon.com/rekognition/latest/customlabels-dg/getting-started.html)

## Architecture

### Full architecture

![Architecture](./docs/solution-overview.png)

* The solution uses Kinesis Video Streams to ingest the video stream from the drone. The video stream is ingested using
  the Streaming Proxy Server.
* The Streaming Proxy Server is a custom application that is deployed on EC2 to convert between RTMP and Kinesis Video
  Streams.
* Kinesis Video Streams automatically extracts frames from the video stream and stores them in S3.
* The Lambda function is triggered when a new frame is available in S3. The Lambda function uses Amazon Rekognition to
  detect objects in the frame.
* The Lambda function sends an alert to the user when an object of interest is detected in the frame.

### Streaming proxy

It allows you to stream video via RTMP or RTSP protocols. The proxy server is deployed on EC2 and is configured to
ingest the video stream into Kinesis Video Streams. The IP address of the proxy server is output from the CDK stack.
Publish the video stream to

`rtmp://<ip-address>:1935/__stream_name__`

Ensure the `__stream_name__` placeholder matches the Kinesis Video Stream name. The server will automatically start
publishing the stream.

![Streaming proxy](./docs/proxy-server.png)

* The Streaming Proxy Server is a custom application that is deployed on EC2 to convert between RTMP and Kinesis Video
  Streams.
* It uses the [KVS Producer C++ Application](https://github.com/awslabs/amazon-kinesis-video-streams-producer-sdk-cpp)
  to ingest the video stream into Kinesis Video Streams.
* Open source [RTSP Simple Server](https://github.com/aler9/rtsp-simple-server) is used to convert the RTMP stream to
  RTSP stream.

## Datasets

Open source datasets for shark detection model

* [Test dataset](https://universe.roboflow.com/d4ms/sharkspotting-2shbe/dataset/3)
* [Training dataset](https://universe.roboflow.com/augie-doebling/sharkspotting)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

