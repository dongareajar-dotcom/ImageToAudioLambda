import boto3
import urllib.parse
import logging

# Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS Clients
rekognition = boto3.client('rekognition')
polly = boto3.client('polly')
s3 = boto3.client('s3')

# Output bucket
OUTPUT_BUCKET = 'audio-output-bucketpooly'


def lambda_handler(event, context):
    try:
        logger.info(f"Incoming event: {event}")

        records = event.get("Records", [])

        if not records:
            return {
                "statusCode": 400,
                "body": "No S3 records found in event"
            }

        results = []

        for record in records:
            bucket = record["s3"]["bucket"]["name"]
            image_key = urllib.parse.unquote_plus(
                record["s3"]["object"]["key"]
            )

            logger.info(f"Processing file: {image_key} from bucket: {bucket}")

            # -----------------------------
            # Rekognition - Detect Labels
            # -----------------------------
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

            labels = [label['Name'] for label in response.get('Labels', [])]
            logger.info(f"Labels detected: {labels}")

            # -----------------------------
            # Build text
            # -----------------------------
            if labels:
                text = "The image contains " + ", ".join(labels)
            else:
                text = "No objects were detected in the image."

            logger.info(f"Polly text: {text}")

            # -----------------------------
            # Polly - Text to Speech
            # -----------------------------
            speech = polly.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId='Joanna'
            )

            # Safe stream handling
            with speech['AudioStream'] as stream:
                audio_data = stream.read()

            # -----------------------------
            # Save MP3 to S3
            # -----------------------------
            audio_file = image_key.rsplit('.', 1)[0] + '.mp3'

            s3.put_object(
                Bucket=OUTPUT_BUCKET,
                Key=audio_file,
                Body=audio_data,
                ContentType='audio/mpeg'
            )

            logger.info(f"Uploaded MP3: {audio_file}")

            results.append(audio_file)

        return {
            "statusCode": 200,
            "body": f"Successfully processed files: {results}"
        }

    except Exception as e:
        logger.error(f"Lambda error: {str(e)}")

        return {
            "statusCode": 500,
            "body": f"Error processing image: {str(e)}"
        }
