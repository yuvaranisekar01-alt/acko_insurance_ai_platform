import os
import json
import uuid
import datetime
import boto3
from dotenv import load_dotenv

load_dotenv()

S3_BUCKET = os.getenv("S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-2")


def _client():
    # No access keys here: on EC2 the instance's IAM role supplies credentials.
    return boto3.client("s3", region_name=AWS_REGION)


def save_claim_to_s3(image_bytes, original_filename, claim_data):
    """
    Stores the damage photo and the claim form as JSON in S3.
    Paths: claims/images/YYYY/MM/DD/<id>_<filename>
           claims/forms/YYYY/MM/DD/<id>.json
    Returns the two S3 keys. Raises if S3_BUCKET is not configured.
    """
    if not S3_BUCKET:
        raise RuntimeError("S3_BUCKET is not set in .env")

    claim_id = uuid.uuid4().hex[:12]
    today = datetime.datetime.now().strftime("%Y/%m/%d")
    safe_name = os.path.basename(original_filename or "photo.jpg").replace(" ", "_")

    s3 = _client()
    image_key = None
    if image_bytes:
        image_key = f"claims/images/{today}/{claim_id}_{safe_name}"
        s3.put_object(Bucket=S3_BUCKET, Key=image_key, Body=image_bytes)

    form_key = f"claims/forms/{today}/{claim_id}.json"
    body = json.dumps({**claim_data, "image_key": image_key}, default=str, indent=2)
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=form_key,
        Body=body.encode("utf-8"),
        ContentType="application/json",
    )
    return image_key, form_key
