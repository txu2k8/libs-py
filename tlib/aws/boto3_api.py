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
import time
import urllib3
import datetime
import threading
import boto3
from boto3.s3 import transfer
from botocore.exceptions import ClientError
from botocore.client import Config

from tlib import log
from tlib.retry import retry

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
        # self.s3_resource = self.get_s3_resource()

    @retry(tries=3, delay=3)
    def get_s3_client(self):
        try:
            logger.info("Init s3 client {url}(key:{key},id:{id})".format(
                url=self.endpoint_url,
                key=self.aws_access_key_id,
                id=self.aws_secret_access_key)
            )
            config = Config(connect_timeout=60, read_timeout=300)
            # , s3={'addressing_style':'path'}
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

    @retry(tries=3, delay=3)
    def get_s3_resource(self):
        try:
            logger.info("Init s3 resource {url}(key:{key},id:{id})".format(
                url=self.endpoint_url,
                key=self.aws_access_key_id,
                id=self.aws_secret_access_key)
            )
            config = Config(connect_timeout=60, read_timeout=300)
            s3_resource = boto3.resource(
                's3', self.region_name, self.api_version,
                self.use_ssl, self.verify, self.endpoint_url,
                self.aws_access_key_id, self.aws_secret_access_key,
                self.aws_session_token, config
            )
            return s3_resource
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
    def list_files(self, bucket, prefix=''):
        """List some or all (up to 1000) of the objects in a bucket"""
        files_info = {}
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
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

    @retry(tries=25, delay=30)
    def delete_path(self, bucket, path=''):
        logger.info("S3 Delete path {0}/{1}".format(bucket, path))

        # s3_resource = self.get_s3_resource()
        # bucket_obj = s3_resource.Bucket(bucket)
        # print(list(bucket_obj.objects.filter(Prefix=path)))
        # bucket_obj.objects.filter(Prefix=path).delete()

        delete_info = {'Objects': []}
        for f_key in self.list_files(bucket, path).keys():
            delete_info['Objects'].append({'Key': f_key})
        if not delete_info['Objects']:
            logger.warning("No file in path {0}/{1}".format(bucket, path))
            return True

        try:
            response = self.s3_client.delete_objects(Bucket=bucket,
                                                     Delete=delete_info)
            status_code = response['ResponseMetadata']['HTTPStatusCode']
            if status_code == 200:
                logger.info('PASS: Delete files from {0}/{1}!'.format(bucket, path))
            else:
                raise Exception('FAIL: Delete files from {0}/{1}, '
                                'rc={2}!'.format(bucket, path, status_code))
            return True
        except Exception as e:
            raise Exception(e)


class IAMObj(object):
    _iam_client = None

    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 region_name='us-west-2'):
        super(IAMObj, self).__init__()
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name

    @property
    def iam_client(self):
        if self._iam_client is None:
            self._iam_client = boto3.client('iam',
                                            region_name=self.region_name,
                                            aws_access_key_id=self.aws_access_key_id,
                                            aws_secret_access_key=self.aws_secret_access_key)
        return self._iam_client

    def get_instance_profile_info_by_name(self, name):
        response = self.iam_client.get_instance_profile(
            InstanceProfileName=name)
        return response['InstanceProfile']


class EC2Obj(object):
    _ec2_client = None
    _ec2_resource = None

    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 region_name='us-west-2'):
        super(EC2Obj, self).__init__()
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name

    @property
    def ec2_client(self):
        if self._ec2_client is None:
            logger.info('Init ec2 client!')
            self._ec2_client = boto3.client('ec2',
                                            region_name=self.region_name,
                                            aws_access_key_id=self.aws_access_key_id,
                                            aws_secret_access_key=self.aws_secret_access_key)
        return self._ec2_client

    @property
    def ec2_resource(self):
        if self._ec2_resource is None:
            logger.info('Init ec2 resource!')
            self._ec2_resource = boto3.resource('ec2',
                                                region_name=self.region_name,
                                                aws_access_key_id=self.aws_access_key_id,
                                                aws_secret_access_key=self.aws_secret_access_key)
        return self._ec2_resource

    @retry(tries=10, delay=10)
    def is_instance_exists(self, instance_id):
        try:
            self.ec2_client.describe_instances(InstanceIds=[instance_id])
        except ClientError:
            raise

    @retry(tries=30, delay=10)
    def is_instance_state_ok(self, instance_id, instance_state):
        logger.info('Wait for EC2 Instance state: %s -> %s' % (
        instance_id, instance_state))
        try:
            instance = self.ec2_resource.Instance(id=instance_id)
            if instance.state['Name'] == instance_state:
                logger.info('Instance state OK')
            else:
                raise TypeError('Instance still {cur_state} !'.format(
                    cur_state=instance.state['Name']))
        except ClientError:
            raise

    def get_instance_state_info_by_id(self, instance_id):
        instance = self.ec2_resource.Instance(id=instance_id)

        return instance.state

    def get_subnets_id_by_cidr(self, cidr):
        filters = [{'Name': 'cidrBlock', 'Values': [cidr]}]
        response = self.ec2_client.describe_subnets(Filters=filters)
        subnets_info = response['Subnets']
        for subnet_info in subnets_info:
            if subnet_info['State'] != 'available':
                continue

            if subnet_info['CidrBlock'] == cidr:
                return subnet_info['SubnetId']

        raise Exception('{cidr} subnet is not exist!'.format(cidr=cidr))

    def get_image_id_by_name(self, image_name):
        filters = [{'Name': 'name', 'Values': [image_name]}]
        response = self.ec2_client.describe_images(Filters=filters)
        images_info = response['Images']
        for image_info in images_info:
            if image_info['State'] != 'available':
                continue

            if image_info['Name'] == image_name:
                return image_info['ImageId']

        raise Exception('{image} image is not exist!'.format(image=image_name))

    def get_security_group_id_by_name(self, group_name):
        filters = [{'Name': 'group-name', 'Values': [group_name]}]
        response = self.ec2_client.describe_security_groups(Filters=filters)
        if len(response['SecurityGroups']) == 0:
            raise Exception('{name} is not exist!'.format(name=group_name))

        return response['SecurityGroups'][0]['GroupId']

    def request_spot_instances(self,
                               spot_count,
                               key_pair_name,
                               security_group_id,
                               iam_instance_profile_name,
                               image_id,
                               subnet_id,
                               instance_type='m5.4xlarge',
                               root_volume_size=100,
                               root_volume_type='gp2',
                               log_volume_size=100,
                               log_volume_type='gp2',
                               ebs_delete_on_termination=True,
                               ebs_optimized=True,
                               monitor=False,
                               associate_public_ip=True,
                               network_delete_on_termination=True,
                               instance_interruption_behavior='terminate',
                               availability_zone='us-west-2a',
                               tenancy='default',
                               request_type='one-time'
                               ):
        logger.info('request_spot_instances')
        spec = {
            'BlockDeviceMappings': [
                {
                    'DeviceName': '/dev/sda1',
                    'Ebs': {
                        'DeleteOnTermination': ebs_delete_on_termination,
                        'VolumeSize': root_volume_size,
                        'VolumeType': root_volume_type
                    }
                },
                {
                    'DeviceName': '/dev/sdb',
                    'Ebs': {
                        'DeleteOnTermination': ebs_delete_on_termination,
                        'VolumeSize': log_volume_size,
                        'VolumeType': log_volume_type
                    }
                }
            ],
            'EbsOptimized': ebs_optimized,
            'IamInstanceProfile': {
                'Name': iam_instance_profile_name
            },
            'ImageId': image_id,
            'InstanceType': instance_type,
            'KeyName': key_pair_name,
            'Monitoring': {
                'Enabled': monitor
            },
            'NetworkInterfaces': [
                {
                    'AssociatePublicIpAddress': associate_public_ip,
                    'DeleteOnTermination': network_delete_on_termination,
                    'Description': '',
                    'DeviceIndex': 0,
                    'Groups': [security_group_id],
                    'SubnetId': subnet_id
                },
            ],
            'Placement': {
                'AvailabilityZone': availability_zone,
                'Tenancy': tenancy
            }
        }

        try:
            response = self.ec2_client.request_spot_instances(
                InstanceCount=spot_count,
                LaunchSpecification=spec,
                Type=request_type,
                InstanceInterruptionBehavior=instance_interruption_behavior
            )

            status_code = response['ResponseMetadata']['HTTPStatusCode']
            spot_request_ids = []
            if status_code == 200:
                for i in range(spot_count):
                    spot_request_id = response['SpotInstanceRequests'][i][
                        'SpotInstanceRequestId']
                    spot_request_status = response['SpotInstanceRequests'][i][
                        'Status']
                    spot_request_state = response['SpotInstanceRequests'][i][
                        'State']
                    if spot_request_status['Code'] == 'pending-evaluation':
                        logger.info('{id}: State is {state}, {message}'.format(
                            id=spot_request_id, state=spot_request_state,
                            message=spot_request_status['Message']))
                        spot_request_ids.append(spot_request_id)
                    else:
                        raise Exception(spot_request_status)

                instance_ids = self.wait_request_to_active(spot_request_ids)
                time.sleep(5)
                self.wait_instances_to_ok(instance_ids)
                instances_id_primary_ip = self.get_instances_id_primary_ip_by_ids(
                    instance_ids)
                logger.info('Request spots success!')
                return instances_id_primary_ip

            else:
                logger.warning(response['ResponseMetadata'])
                raise Exception(
                    'Requst spot fail, status code is {code}'.format(
                        code=status_code))

        except Exception as e:
            logger.warning('Exception occured, request spot fail!')
            raise e

    def describe_spot_instance_requests(self, spot_request_ids):
        try:
            response = self.ec2_client.describe_spot_instance_requests(
                SpotInstanceRequestIds=spot_request_ids)
            status_code = response['ResponseMetadata']['HTTPStatusCode']
            if status_code == 200:
                return response['SpotInstanceRequests']
            else:
                logger.warning(response['ResponseMetadata'])
                raise Exception(
                    'Describe spot instance requests fail, status code is {code}'.format(
                        code=status_code))

        except Exception as e:
            logger.warning(
                'Exception occured, describe spot instance requests fail!')
            raise e

    @retry(tries=10, delay=10)
    def wait_request_to_active(self, spot_request_ids):
        spot_instance_requests = self.describe_spot_instance_requests(
            spot_request_ids)
        instance_ids = []
        for spot_instance_request in spot_instance_requests:
            spot_request_id = spot_instance_request['SpotInstanceRequestId']
            spot_request_status = spot_instance_request['Status']
            spot_request_state = spot_instance_request['State']
            if spot_request_status[
                'Code'] == 'fulfilled' and spot_request_state == 'active':
                logger.info('{id}: State is {state}, {message}'.format(
                    id=spot_request_id, state=spot_request_state,
                    message=spot_request_status['Message']))
                instance_ids.append(spot_instance_request['InstanceId'])
            else:
                raise Exception(
                    'Wait request {id} to active!'.format(id=spot_request_id))

        return instance_ids

    def describe_instances_status(self, instance_ids):
        try:
            response = self.ec2_client.describe_instance_status(
                InstanceIds=instance_ids)
            status_code = response['ResponseMetadata']['HTTPStatusCode']
            if status_code == 200:
                return response['InstanceStatuses']
            else:
                logger.warning(response['ResponseMetadata'])
                raise Exception(
                    'Describe instances status fail, status code is {code}'.format(
                        code=status_code))

        except Exception as e:
            logger.warning(
                'Exception occured, describe instances status fail!')
            raise e

    @retry(tries=20, delay=30)
    def wait_instances_to_ok(self, instance_ids):
        instances_status = self.describe_instances_status(instance_ids)
        for instance_status in instances_status:
            summary_instance_status = instance_status['InstanceStatus'][
                'Status']
            detail_instance_status = \
            instance_status['InstanceStatus']['Details'][0]['Status']
            detail_instance_status_name = \
            instance_status['InstanceStatus']['Details'][0]['Name']

            summary_system_status = instance_status['SystemStatus']['Status']
            detail_system_status = \
            instance_status['SystemStatus']['Details'][0]['Status']
            detail_system_status_name = \
            instance_status['SystemStatus']['Details'][0]['Name']

            instance_id = instance_status['InstanceId']
            if summary_instance_status == "ok" and detail_instance_status == "passed":
                logger.info(
                    '{id} instance {status_name} status checks {detail_status}!'.format(
                        id=instance_id,
                        status_name=detail_instance_status_name,
                        detail_status=detail_instance_status))
            else:
                raise Exception(
                    'Wait {id} instance {status_name} status check, status is {status}, detail status is {detail_status}'.format(
                        id=instance_id,
                        status_name=detail_instance_status_name,
                        status=summary_instance_status,
                        detail_status=detail_instance_status))

            if summary_system_status == "ok" and detail_system_status == "passed":
                logger.info(
                    '{id} system {status_name} status checks {detail_status}!'.format(
                        id=instance_id, status_name=detail_system_status_name,
                        detail_status=detail_system_status))
            else:
                raise Exception(
                    'Wait {id} system {status_name} status check, status is {status}, detail status is {detail_status}'.format(
                        id=instance_id, status_name=detail_system_status_name,
                        status=summary_system_status,
                        detail_status=detail_system_status))

    def describe_instances(self, filters=None):
        logger.info('Describing EC2 Instances...')
        try:
            if filters is None:
                response = self.ec2_client.describe_instances()
            else:
                response = self.ec2_client.describe_instances(Filters=filters)

            return response
        except Exception as e:
            raise e

    def describe_instances_by_id(self, instance_ids):
        filters = [{'Name': 'instance-id', 'Values': instance_ids}]
        try:
            response = self.describe_instances(filters)
            status_code = response['ResponseMetadata']['HTTPStatusCode']
            if status_code == 200:
                if len(response['Reservations']) == 0:
                    raise Exception(
                        '{ids} is not exist!'.format(ids=instance_ids))

                return response['Reservations'][0]['Instances']
            else:
                logger.warning(response['ResponseMetadata'])
                raise Exception(
                    'Describe instances fail, status code is {code}'.format(
                        code=status_code))

        except Exception as e:
            logger.warning('Exception occured, describe instances fail!')
            raise e

    def describe_instances_by_private_ip(self, primary_ips):
        filters = [{'Name': 'network-interface.addresses.private-ip-address',
                    'Values': primary_ips}]
        try:
            response = self.describe_instances(filters)
            status_code = response['ResponseMetadata']['HTTPStatusCode']
            if status_code == 200:
                if len(response['Reservations']) == 0:
                    raise Exception(
                        '{ips} is not exist!'.format(ips=primary_ips))

                return response['Reservations'][0]['Instances']
            else:
                logger.warning(response['ResponseMetadata'])
                raise Exception(
                    'Describe instances fail, status code is {code}'.format(
                        code=status_code))

        except Exception as e:
            logger.warning('Exception occured, describe instances fail!')
            raise e

    def get_instance_networkinterface_id_by_ip(self, primary_ip):
        instances_info = self.describe_instances_by_private_ip([primary_ip])
        for instance_info in instances_info:
            network_interfaces = instance_info['NetworkInterfaces']
            for network_interface in network_interfaces:
                return network_interface['NetworkInterfaceId']

    def get_instances_id_primary_ip_by_ids(self, instance_ids):
        instances_info = self.describe_instances_by_id(instance_ids)
        instances_id_primary_ip = {}
        for instance_info in instances_info:
            instnace_id = instance_info['InstanceId']
            network_interfaces = instance_info['NetworkInterfaces']
            for network_interface in network_interfaces:
                for private_ip_info in network_interface['PrivateIpAddresses']:
                    if private_ip_info['Primary']:
                        instances_id_primary_ip[instnace_id] = private_ip_info[
                            'PrivateIpAddress']

        return instances_id_primary_ip

    def get_instances_id_primary_ip_by_ips(self, primary_ips):
        instances_id_primary_ip = {}
        try:
            instances_info = self.describe_instances_by_private_ip(primary_ips)
        except Exception as e:
            logger.warning(
                'Get none of instances with ips: {0}, err={1}'.format(
                    primary_ips, e))
            return instances_id_primary_ip

        real_primary_ips = []
        for instance_info in instances_info:
            instance_id = instance_info['InstanceId']
            network_interfaces = instance_info['NetworkInterfaces']
            for network_interface in network_interfaces:
                for private_ip_info in network_interface['PrivateIpAddresses']:
                    if private_ip_info['Primary']:
                        instances_id_primary_ip[instance_id] = private_ip_info[
                            'PrivateIpAddress']
                        real_primary_ips.append(
                            private_ip_info['PrivateIpAddress'])

        not_exist_ips = list(
            set(primary_ips).difference(set(real_primary_ips)))
        if len(not_exist_ips) > 0:
            logger.warning('{ip} is not exist!'.format(ip=not_exist_ips))

        return instances_id_primary_ip

    def assign_private_ip_addresses(self, primary_ip, secondary_private_ips):
        instance_netwrokinterface_id = self.get_instance_networkinterface_id_by_ip(
            primary_ip)
        response = self.ec2_client.assign_private_ip_addresses(
            AllowReassignment=False,
            NetworkInterfaceId=instance_netwrokinterface_id,
            PrivateIpAddresses=secondary_private_ips)

        return response

    def unassign_private_ip_addresses(self, primary_ip, secondary_private_ips):
        instance_netwrokinterface_id = self.get_instance_networkinterface_id_by_ip(
            primary_ip)
        response = self.ec2_client.unassign_private_ip_addresses(
            NetworkInterfaceId=instance_netwrokinterface_id,
            PrivateIpAddresses=secondary_private_ips)
        return response

    def create_tags(self, instance_id, key, value):
        try:
            tags = [{'Key': key, 'Value': value}]
            response = self.ec2_client.create_tags(Resources=[instance_id],
                                                   Tags=tags)
            status_code = response['ResponseMetadata']['HTTPStatusCode']
            if status_code == 200:
                logger.info('Create tags {name} successful for {id}!'.format(
                    name=value, id=instance_id))
            else:
                logger.warning(response['ResponseMetadata'])
                raise Exception(
                    'Create tags fail, status code is {code}'.format(
                        code=status_code))

        except Exception as e:
            logger.warning('Exception occured, create tags fail!')
            raise e

    def modify_instance(self, instance_id):
        logger.info('Modifying EC2 Instance ' + instance_id)
        return self.ec2_client.modify_instance_attribute(
            InstanceId=instance_id, DisableApiTermination={'Value': True})

    def stop_instances(self, instance_ip_list):
        instance_id_ip = self.get_instances_id_primary_ip_by_ips(
            instance_ip_list)
        logger.info('Stopping EC2 Instance %s' % instance_id_ip)
        return self.ec2_client.stop_instances(
            InstanceIds=list(instance_id_ip.keys()))

    def start_instances(self, instance_ip_list):
        instance_id_ip = self.get_instances_id_primary_ip_by_ips(
            instance_ip_list)
        logger.info('Starting EC2 Instance %s' % instance_id_ip)
        return self.ec2_client.start_instances(
            InstanceIds=list(instance_id_ip.keys()))

    def reboot_instances(self, instance_ip_list):
        instance_id_ip = self.get_instances_id_primary_ip_by_ips(
            instance_ip_list)
        logger.info('Reboot EC2 Instance %s' % instance_id_ip)
        return self.ec2_client.reboot_instances(
            InstanceIds=list(instance_id_ip.keys()))

    def terminate_instance(self, instance_ip_list):
        instance_id_ip = self.get_instances_id_primary_ip_by_ips(
            instance_ip_list)
        if not instance_id_ip:
            return True

        logger.info('Terminating EC2 Instance %s' % instance_id_ip)
        self.ec2_client.terminate_instances(
            InstanceIds=list(instance_id_ip.keys()))

        while True:
            for instance_id, instance_ip in instance_id_ip.items():
                instance_stat_info = self.get_instance_state_info_by_id(
                    instance_id)
                instance_stat = instance_stat_info['Name']
                if instance_stat != 'terminated':
                    logger.warning(
                        'Instance {ip} is terminating, state is {stat}!'.format(
                            ip=instance_ip, stat=instance_stat))
                    time.sleep(10)
                    break
                else:
                    logger.info(
                        'Instance {ip} is terminated, state is {stat}!'.format(
                            ip=instance_ip, stat=instance_stat))
            else:
                break
        return True


if __name__ == "__main__":
    bucket_name = 'bucket-west-2'
    path_prefix = 'd1'
    s3_obj = S3Obj('s3.amazonaws.com', 'IAIR6GZOQZYEN', 'qFngeZyXjymLKd')
    # s3_obj.delete_path(bucket, path)
    s3_resource = s3_obj.get_s3_resource()
    bucket_obj = s3_resource.Bucket(bucket_name)
    print(list(bucket_obj.objects.filter(Prefix=path_prefix)))
    # bucket_obj.objects.filter(Prefix=path).delete()
