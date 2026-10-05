"""Amazon S3 storage for marksheet PDFs.

No keys in code: boto3 picks up credentials from the EC2 IAM role
(or ~/.aws/credentials when running locally).
"""
import logging

import boto3
from flask import current_app

log = logging.getLogger(__name__)


def _client():
    return boto3.client('s3', region_name=current_app.config['AWS_REGION'])


def enabled():
    return bool(current_app.config.get('S3_BUCKET'))


def upload_pdf(key, data):
    if not enabled():
        return None
    _client().put_object(Bucket=current_app.config['S3_BUCKET'], Key=key, Body=data,
                         ContentType='application/pdf', ServerSideEncryption='AES256')
    log.info('uploaded s3://%s/%s', current_app.config['S3_BUCKET'], key)
    return key


def presigned_url(key, expires=300):
    return _client().generate_presigned_url(
        'get_object', Params={'Bucket': current_app.config['S3_BUCKET'], 'Key': key}, ExpiresIn=expires)
