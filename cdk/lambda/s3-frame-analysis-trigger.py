"""
Lambda function code that is triggered when a new frame is dropped in the frames bucket.
This frame is analysed against a customer rekognition model.
If the model detects a shark, a message is sent to the SNS topic.
⚠️ DO NOT ever upload an image file to the bucket from this code.
"""
import os

import boto3

topic_arn = os.getenv('TOPIC_ARN')

rekognition = boto3.client('rekognition')
sns = boto3.client('sns')

model = '<model-arn>'

object_of_interest = 'shark'


# lambda function trigger
def handler(event, context):
    if model == '<model-arn>':
        print('Please update the model arn in the code')
        return

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    shark_detection_response = rekognition.detect_labels(
        Image={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        },
        MinConfidence=95
    )

    is_shark_detected = any(
        object_of_interest in label['Name'] for label in shark_detection_response['Labels'])


    # Region: Custom model detection snippet
    # 💬 To use a custom rekognition model, you need to pass the model arn in the request
    # 💬 Then uncomment the following lines
    # shark_detection_response = rekognition.detect_custom_labels(
    #     Image={
    #         'S3Object': {
    #             'Bucket': bucket,
    #             'Name': key
    #         }
    #     },
    #     MinConfidence=95,
    #     ProjectVersionArn=model
    # )
    #
    # is_shark_detected = any(
    #     object_of_interest in label['Name'] for label in shark_detection_response['CustomLabels'])
    # End region


    if is_shark_detected:
        print('Shark detected!')
        # send a message to the SNS topic

        sns.publish(
            TopicArn=topic_arn,
            Message='Shark detected!'
        )
    else:
        print('No shark detected')

    return True
