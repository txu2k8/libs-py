# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/16 16:07
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""boto3 objs
S3
EC2
Boto 3 Documentation:
https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
"""

import os
import urllib3
import datetime
import threading
import boto3
from boto3.s3 import transfer
from botocore.exceptions import ClientError
from botocore.client import Config

from libs import log
from libs.retry import retry

urllib3.disable_warnings()

# =============================
# --- Global Value
# =============================
logger = log.get_logger()
KB = 1024
MB = 1024 * KB
GB = 1024 * MB
TB = 1024 * GB


class ProgressPercentage(object):
    """
    Progress Percentage: as a optional Callback parameter for boto3
    """
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        # To simplify, assume this is hooked up to a single filename
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            logger.info("\r%s  %s / %s  (%.2f%%)" % (
                self._filename, self._seen_so_far, self._size, percentage))


class S3Obj(object):
    """
    BOTO S3 services
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html
    """

    def __init__(self, s3_ip, aws_access_key_id, aws_secret_access_key,
                 port=443, region_name=None, api_version=None, use_ssl=False,
                 verify=False, aws_session_token=None, http=False):
        super(S3Obj, self).__init__()
        self.s3_ip = s3_ip
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.port = port
        self.region_name = region_name
        self.api_version = api_version
        self.use_ssl = use_ssl
        self.verify = verify
        self.aws_session_token = aws_session_token
        protocol = 'http' if http else 'https'
        self.endpoint_url = '{0}://{1}:{2}'.format(protocol, self.s3_ip, self.port)

        self.s3_client = self.get_s3_client()
        self.s3_transfer = self.get_s3_transfer()

    @retry(tries=3, delay=3)
    def get_s3_client(self):
        try:
            logger.info("Init s3 client {url}(key:{key},id:{id})".format(
                url=self.endpoint_url,
                key=self.aws_access_key_id,
                id=self.aws_secret_access_key)
            )
            config = Config(connect_timeout=60, read_timeout=300)
            s3_client = boto3.client(
                's3', self.region_name, self.api_version,
                self.use_ssl, self.verify, self.endpoint_url,
                self.aws_access_key_id, self.aws_secret_access_key,
                self.aws_session_token, config
            )
            return s3_client
        except Exception as e:
            raise Exception(e)

    @retry(tries=3, delay=3)
    def get_s3_transfer(self):
        logger.info("Init s3 transfer {url}".format(url=self.endpoint_url))
        s3_config = transfer.TransferConfig(multipart_threshold=10 * TB,
                                            max_concurrency=10,
                                            multipart_chunksize=1 * TB,
                                            num_download_attempts=5,
                                            max_io_queue=100,
                                            io_chunksize=256 * KB,
                                            use_threads=True)
        try:
            s3_transfer = transfer.S3Transfer(self.s3_client, s3_config)
            return s3_transfer
        except Exception as e:
            raise Exception(e)

    @retry(tries=25, delay=30)
    def list_buckets(self):
        """ Retrieve the list of existing buckets """
        bucket_list = []
        try:
            response = self.s3_client.list_buckets()
            for bucket in response['Buckets']:
                bucket_list.append(bucket['Name'])
        except Exception as e:
            raise e
        return bucket_list

    @retry(tries=25, delay=30)
    def list_files(self, bucket):
        """List some or all (up to 1000) of the objects in a bucket"""
        files_info = {}
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket)
            if 'Contents' not in response:
                return files_info
            for f_info in response['Contents']:
                files_info[f_info['Key']] = f_info['Size']
        except Exception as e:
            raise e
        return files_info

    @retry(tries=25, delay=30)
    def upload_file(self, file_path, file_name, bucket, bucket_folder=None):
        """
        Upload a file to an S3 bucket
        :param file_path: file path
        :param file_name: File to upload
        :param bucket: Bucket to upload to
        :param bucket_folder: bucket/bucket_folder to upload
        :return: True if file was uploaded, else False
        """
        file_full_path = os.path.join(file_path, file_name)
        file_key = os.path.join(bucket_folder, file_name) \
            if bucket_folder else file_name
        try:
            logger.info('START: Upload {0} -> {1} ...'.format(file_name, bucket))
            start_time = datetime.datetime.now()
            self.s3_transfer.upload_file(file_full_path, bucket, key=file_key,
                                         callback=ProgressPercentage(file_full_path))
            end_time = datetime.datetime.now()
            cost_time = end_time - start_time
            logger.info("PASS: Upload file {0}, Elapsed:{1}".format(file_name, cost_time))
            return True
        except ClientError as e:
            raise Exception(e)

    @retry(tries=25, delay=30)
    def download_file(self, bucket, file_name, file_path, bucket_folder=None):
        file_full_path = os.path.join(file_path, file_name)
        file_key = os.path.join(bucket_folder, file_name) if bucket_folder else file_name
        try:
            logger.info('START: Download from {0} to {1} ...'.format(bucket, file_name))
            self.s3_client.download_file(bucket, file_key, file_full_path)
            logger.info("PASS: Download file {name}".format(name=file_name))
            return True
        except Exception as e:
            raise Exception(e)

    @retry(tries=25, delay=30)
    def delete_file(self, bucket, file_name, bucket_folder=None):
        try:
            file_key = file_name if not bucket_folder \
                else os.path.join(bucket_folder, file_name)
            response = self.s3_client.delete_object(Bucket=bucket, Key=file_key)
            status_code = response['ResponseMetadata']['HTTPStatusCode']
            if status_code == 204:
                logger.info('PASS: Delete {0} from {1}'.format(file_name, bucket))
            else:
                raise Exception('FAIL: Delete {0} from {1}, rc={2}!'.format(
                    file_name, bucket, status_code))
            return True
        except Exception as e:
            raise Exception(e)

    @retry(tries=25, delay=30)
    def delete_files(self, bucket, file_name_list, bucket_folder=None):
        delete_info = {'Objects': []}
        for file_name in file_name_list:
            file_key = os.path.join(bucket_folder, file_name) \
                if bucket_folder else file_name
            file_info = {'Key': file_key}
            delete_info['Objects'].append(file_info)

        try:
            # print(delete_info)
            response = self.s3_client.delete_objects(Bucket=bucket, Delete=delete_info)
            status_code = response['ResponseMetadata']['HTTPStatusCode']
            if status_code == 200:
                logger.info('PASS: Delete files from {0}!'.format(bucket))
            else:
                raise Exception('FAIL: Delete files from {0}, rc={1}!'.format(
                    bucket, status_code))
            return True
        except Exception as e:
            raise Exception(e)
