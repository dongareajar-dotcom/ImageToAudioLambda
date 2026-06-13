import boto3
import urllib.parse
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
rekognition = boto3.client('rekognition')
polly = boto3.client('polly')
s3 = boto3.client('s3')

# Output bucket
OUTPUT_BUCKET = 'audio-output-bucketpooly'


def lambda_handler(event, context):
    try:
        # Get bucket name and object key
        bucket = event['Records'][0]['s3']['bucket']['name']
        image_key = urllib.parse.unquote_plus(
            event['Records'][0]['s3']['object']['key']
        )

        logger.info(f"Processing image: {image_key} from bucket: {bucket}")

        # Detect labels in image
        response = rekognition.detect_labels(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': image_key
                }
            },
            MaxLabels=5,
            MinConfidence=70
        )

        labels = [label['Name'] for label in response['Labels']]

        logger.info(f"Detected labels: {labels}")

        # Create speech text
        if labels:
            text = "The image contains " + ", ".join(labels)
        else:
            text = "No objects were detected in the image."

        logger.info(f"Generated text: {text}")

        # Convert text to speech
        speech = polly.synthesize_speech(
            Text=text,
            OutputFormat='mp3',
            VoiceId='Joanna'
        )

        audio_data = speech['AudioStream'].read()

        # Create output filename
        audio_file = image_key.rsplit('.', 1)[0] + '.mp3'

        # Upload MP3 to output bucket
        s3.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=audio_file,
            Body=audio_data,
            ContentType='audio/mpeg'
        )

        logger.info(f"Audio file uploaded: {audio_file}")

        return {
            'statusCode': 200,
            'body': f'Audio file created successfully: {audio_file}'
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")

        return {
            'statusCode': 500,
            'body': f'Error processing image: {str(e)}'
        }