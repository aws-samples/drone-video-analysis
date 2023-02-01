import time

import boto3
import json

client = boto3.client('kinesisvideo')

bucket_name = "<bucket-name>"
stream_name = "<stream-name>"
region = "<region>"
sampling_interval = 3_000  # 3 seconds

if __name__ == "__main__":
    client.update_image_generation_configuration(
        # update <placeholders variables>
        StreamName=stream_name,
        ImageGenerationConfiguration={
            'Status': 'ENABLED',
            'ImageSelectorType': 'PRODUCER_TIMESTAMP',
            'DestinationConfig': {
                'Uri': f's3://{bucket_name}/{stream_name}',
                'DestinationRegion': region
            },
            'SamplingInterval': sampling_interval,
            "Format": "JPEG",
        }
    )

    configuration = client.describe_image_generation_configuration(
        StreamName=stream_name
    )

    print(json.dumps(configuration, indent=2))
