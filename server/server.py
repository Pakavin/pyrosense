from pipeline import app
import boto3
import os
import time

from dotenv import load_dotenv
load_dotenv()
#--------------- Credentials Configuration ---------------#
region_name = os.environ['REGION_NAME_2']
aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID']
aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']
#---------------------------------------------------------#

### Client setting ###
s3_resource = boto3.resource('s3',
    region_name=region_name,
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key
)


def main():
    for bucket in s3_resource.buckets.all():

        object = list(bucket.objects.all())[-1]

        path = os.path.splitext(object.key)
        if path[1]:
            filepath = path[0].split('/')[-1] + path[1]
            device = path[0].split('/')[0]

            print(device + " | " + filepath)

            s3_resource.Bucket(bucket.name).download_file(object.key, filepath)
            app.invoke({ "device": device, "filepath": filepath })
            s3_resource.Object(bucket.name, object.key).delete()

if __name__ == "__main__":
    while True:
        main()
        time.sleep(5)