# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/16 16:07
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

""" boto2 obj
http://boto.cloudhackers.com/en/latest/ref/ec2.html#
"""

import json, re
import datetime
import threading
import boto
import boto.ec2
import boto.iam

from libs import log
from libs.retry import retry

# =============================
# --- Global
# =============================
logger = log.get_logger()


class EC2Obj(object):
    _ec2_client = None

    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 region='us-west-2'):
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region = region
        self.instance_ip = {}
        self.start_time = datetime.datetime.now()
        self.spot_set_list = []  # lifecycle=spot
        self.spot_instance_request_list = []  # lifecycle=spot
        self.reservation_list = []  # lifecycle=normal

    @property
    def ec2_client(self):
        """
        Connect EC2 Client
        :return:
        """
        if self._ec2_client is None:
            # check region
            region_list = ("us-west-1", "us-west-2")
            assert self.region in region_list, \
                "Not support region {0}".format(self.region)
            self._ec2_client = boto.ec2.connect_to_region(
                self.region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key
            )
        return self._ec2_client

    def check_image(self, image_id):
        """
        Check weather the image_id is exist or not
        :param image_id:
        :return:
        """

        try:
            img = self.ec2_client.get_image(image_id)
            logger.debug("Image info,\nid: %s\nname: %s\ncreationDate: %s"
                            % (image_id, img.name, img.creationDate))
        except boto.exception.EC2ResponseError as e:
            logger.error("Failed to get image, message: %s" % e.message)
            raise Exception()

        return True

    def check_key_pair(self, key_name):
        """
        Check weather the key_name is exist or not
        :param key_name:
        :return:
        """

        try:
            key = self.ec2_client.get_key_pair(key_name)
            if key is None:
                logger.error("Key pair name '%s' not exist" % key_name)
                raise Exception()
            else:
                logger.debug("Key pair info,\nname: %s\nfingerprint: %s"
                                % (key.name, key.fingerprint))
        except Exception as e:
            raise Exception(e)

        return True

    @staticmethod
    def check_instance_type(instance_type, launch_type='spot'):
        """
        Check weather the instance_type is exist or not
        :param instance_type:
        :param launch_type:
        :return:
        """

        # instance type
        instance_type_list = [
            "t2.nano", "t2.micro", "t2.small", "t2.medium", "t2.large",
            "t2.xlarge", "t2.2xlarge", "t3.nano", "t3.micro", "t3.small",
            "t3.medium", "t3.large", "t3.xlarge", "t3.2xlarge", "m5d.large",
            "m5d.xlarge", "m5d.2xlarge", "m5d.4xlarge", "m5d.12xlarge",
            "m5d.24xlarge", "m5.large", "m5.xlarge", "m5.2xlarge",
            "m5.4xlarge", "m5.12xlarge", "m5.24xlarge", "m4.large",
            "m4.xlarge", "m4.2xlarge", "m4.4xlarge", "m4.10xlarge",
            "m4.16xlarge", "c5d.large", "c5d.xlarge", "c5d.2xlarge",
            "c5d.4xlarge", "c5d.9xlarge", "c5d.18xlarge", "c5.large",
            "c5.xlarge", "c5.2xlarge", "c5.4xlarge", "c5.9xlarge",
            "c5.18xlarge", "c4.large", "c4.xlarge", "c4.2xlarge", "c4.4xlarge",
            "c4.8xlarge", "f1.2xlarge", "f1.4xlarge", "f1.16xlarge",
            "g3s.xlarge", "g3.4xlarge", "g3.8xlarge", "g3.16xlarge",
            "g2.2xlarge", "g2.8xlarge", "p2.xlarge", "p2.8xlarge",
            "p2.16xlarge", "p3.2xlarge", "p3.8xlarge", "p3.16xlarge",
            "r5d.large", "r5d.xlarge", "r5d.2xlarge", "r5d.4xlarge",
            "r5d.12xlarge", "r5d.24xlarge", "r5.large", "r5.xlarge",
            "r5.2xlarge", "r5.4xlarge", "r5.12xlarge", "r5.24xlarge",
            "r4.large", "r4.xlarge", "r4.2xlarge", "r4.4xlarge",
            "r4.8xlarge", "r4.16xlarge", "x1.16xlarge", "x1e.xlarge",
            "x1e.2xlarge", "x1e.4xlarge", "x1e.8xlarge", "x1e.16xlarge",
            "x1e.32xlarge", "x1.32xlarge", "z1d.large", "z1d.xlarge",
            "z1d.2xlarge", "z1d.3xlarge", "z1d.6xlarge", "z1d.12xlarge",
            "d2.xlarge", "d2.2xlarge", "d2.4xlarge", "d2.8xlarge",
            "i2.xlarge", "i2.2xlarge", "i2.4xlarge", "i2.8xlarge",
            "h1.2xlarge", "h1.4xlarge", "h1.8xlarge", "h1.16xlarge",
            "i3.large", "i3.xlarge", "i3.2xlarge", "i3.4xlarge", "i3.8xlarge",
            "i3.16xlarge", "i3.metal", "m5a.4xlarge"
        ]

        spot_instance_type_list = [
            "c3.2xlarge", "c3.4xlarge", "c3.8xlarge", "c3.large", "c3.xlarge",
            "c4.2xlarge", "c4.4xlarge", "c4.8xlarge", "c4.large", "c4.xlarge",
            "c5.18xlarge", "c5.2xlarge", "c5.4xlarge", "c5.9xlarge",
            "c5.large", "c5.xlarge", "c5d.18xlarge", "c5d.2xlarge",
            "c5d.4xlarge", "c5d.9xlarge", "c5d.large", "c5d.xlarge",
            "cc2.8xlarge", "cr1.8xlarge", "d2.2xlarge", "d2.4xlarge",
            "d2.8xlarge", "d2.xlarge", "f1.16xlarge", "f1.4xlarge",
            "f1.2xlarge", "g2.2xlarge", "g2.8xlarge", "g3.16xlarge",
            "g3.4xlarge", "g3.8xlarge", "g3s.xlarge", "h1.16xlarge",
            "h1.2xlarge", "h1.4xlarge", "h1.8xlarge", "i2.2xlarge",
            "i2.4xlarge", "i2.8xlarge", "i2.xlarge", "i3.16xlarge",
            "i3.2xlarge", "i3.4xlarge", "i3.8xlarge", "i3.large", "i3.metal",
            "i3.xlarge", "m3.2xlarge", "m3.large", "m3.medium", "m3.xlarge",
            "m4.10xlarge", "m4.16xlarge", "m4.2xlarge", "m4.4xlarge",
            "m4.large", "m4.xlarge", "m5.12xlarge", "m5.24xlarge",
            "m5.2xlarge", "m5.4xlarge", "m5.large", "m5.xlarge",
            "m5d.12xlarge", "m5d.24xlarge", "m5d.2xlarge", "m5d.4xlarge",
            "m5d.large", "m5d.xlarge", "p2.16xlarge", "p2.8xlarge",
            "p2.xlarge", "p3.16xlarge", "p3.2xlarge", "p3.8xlarge",
            "r3.2xlarge", "r3.4xlarge", "r3.8xlarge", "r3.large", "r3.xlarge",
            "r4.16xlarge", "r4.2xlarge", "r4.4xlarge", "r4.8xlarge",
            "r4.large", "r4.xlarge", "r5.12xlarge", "r5.24xlarge",
            "r5.2xlarge", "r5.4xlarge", "r5.large", "r5.xlarge",
            "r5d.12xlarge", "r5d.24xlarge", "r5d.2xlarge", "r5d.4xlarge",
            "r5d.large", "r5d.xlarge", "t2.2xlarge", "t2.large", "t2.medium",
            "t2.micro", "t2.small", "t2.xlarge", "t3.2xlarge", "t3.large",
            "t3.medium", "t3.micro", "t3.nano", "t3.small", "t3.xlarge",
            "x1.16xlarge", "x1.32xlarge", "x1e.16xlarge", "x1e.2xlarge",
            "x1e.32xlarge", "x1e.4xlarge", "x1e.8xlarge", "x1e.xlarge",
            "z1d.12xlarge", "z1d.2xlarge", "z1d.3xlarge", "z1d.6xlarge",
            "z1d.large", "z1d.xlarge", "m5a.4xlarge"
        ]

        type_list = spot_instance_type_list if launch_type == 'spot' \
            else instance_type_list
        if instance_type not in type_list:
            logger.error("Invalid instance type '{0}".format(instance_type))
            raise Exception()

        return True

    def check_group(self, group_id):
        """
        Check weather the group_id is exist or not
        :param group_id:
        :return:
        """

        try:
            ret = self.ec2_client.get_all_security_groups(group_ids=[group_id])
            logger.debug("Security group info,\n"
                            "id: %s\n"
                            "name: %s\n"
                            "description: %s\n"
                            "vpc_id: %s" % (group_id, ret[0].name,
                                            ret[0].description, ret[0].vpc_id))
        except Exception as e:
            logger.error("Failed to get security group, message: %s" % e)
            raise Exception()

        return True

    def get_price(self, instance_type):
        """
        Get the instance_type price from price history
        :param instance_type:
        :return:
        """

        # get history from 3 days ago
        start_time = datetime.datetime.now() - datetime.timedelta(days=-3)

        price_obj_list = self.ec2_client.get_spot_price_history(
            # product_description="Linux/UNIX",
            # availability_zone="us-west-2a"
            start_time=start_time.isoformat(),
            instance_type=instance_type
        )

        price_list = []
        for p in price_obj_list:
            price_list.append(p.price)

        if len(price_list) > 0:
            temp_list = list(set(price_list))
            temp_list.sort()
            # use the middle price
            middle_price = temp_list[len(temp_list) // 2]
            logger.debug("%s price is %s" % (instance_type, middle_price))
            # return max(price_list)
            return middle_price
        else:
            raise Exception("Can not get price in history")

    def launch_instance(self, count=1, lifecycle='spot', instance_type=None,
                        image_id=None, key_name=None, security_group_id=None,
                        subnet_id=None, instance_profile_name=None,
                        assign_public_ip=False):
        """
        Request instances
        :param count:
        :param lifecycle:
        :param instance_type:
        :param image_id:
        :param key_name:
        :param security_group_id:
        :param subnet_id:
        :param instance_profile_name:
        :param assign_public_ip:
        :return:
        """
        # check parameters
        if count < 1:
            return True
        try:
            self.check_image(image_id)
            self.check_key_pair(key_name)
            self.check_instance_type(instance_type, launch_type=lifecycle)
            self.check_group(security_group_id)
            iam = IAMObj(self.aws_access_key_id, self.aws_secret_access_key)
            iam.check_instance_profile(instance_profile_name)
        except Exception as e:
            raise Exception("Check parameters failed\n{0}".format(e))

        # start launch instances
        self.start_time = datetime.datetime.now()
        try:
            logger.info("Launch instance(count={0},instance_type={1}),"
                           "lifecycle={2}".format(count, instance_type,
                                                  lifecycle))
            if lifecycle == 'spot':
                price = self.get_price(instance_type)
                if assign_public_ip:
                    network_interface = boto.ec2.networkinterface.NetworkInterfaceSpecification(
                        device_index=0,
                        subnet_id=subnet_id,
                        delete_on_termination=True,
                        groups=[security_group_id],
                        associate_public_ip_address=True
                    )
                    spot_set = self.ec2_client.request_spot_instances(
                        count=count,
                        price=price,
                        instance_type=instance_type,
                        image_id=image_id,
                        key_name=key_name,
                        network_interfaces=boto.ec2.networkinterface.NetworkInterfaceCollection(network_interface),
                        instance_profile_name=instance_profile_name
                    )
                else:
                    spot_set = self.ec2_client.request_spot_instances(
                        count=count,
                        price=price,
                        instance_type=instance_type,
                        image_id=image_id,
                        key_name=key_name,
                        security_group_ids=[security_group_id],
                        subnet_id=subnet_id,
                        instance_profile_name=instance_profile_name
                    )
                self.spot_instance_request_list.extend(spot_set)

            elif lifecycle == 'normal':
                # EC2 instance
                if assign_public_ip:
                    network_interface = boto.ec2.networkinterface.NetworkInterfaceSpecification(
                        device_index=0,
                        subnet_id=subnet_id,
                        delete_on_termination=True,
                        groups=[security_group_id],
                        associate_public_ip_address=True
                    )
                    reservation = self.ec2_client.run_instances(
                        min_count=count,
                        max_count=count,
                        instance_type=instance_type,
                        image_id=image_id,
                        key_name=key_name,
                        network_interfaces=boto.ec2.networkinterface.NetworkInterfaceCollection(network_interface),
                        instance_profile_name=instance_profile_name
                    )
                else:
                    reservation = self.ec2_client.run_instances(
                        min_count=count,
                        max_count=count,
                        instance_type=instance_type,
                        image_id=image_id,
                        key_name=key_name,
                        security_group_ids=[security_group_id],
                        subnet_id=subnet_id,
                        instance_profile_name=instance_profile_name
                    )
                self.reservation_list.append(reservation)

            else:
                raise Exception("Not supported LifeCycle: {0}".format(lifecycle))

        except Exception as e:
            raise Exception("Failed to launch instance({0})\n{0}".format(lifecycle, e))

        return True

    @retry(tries=60, delay=30)
    def wait_instance_running(self, instance_id, lifecycle='null'):
        """
        Waiting for instance running
        :except: System reachability check passed
        :except: Instance reachability check passed
        :param instance_id:
        :param lifecycle:
        :return:
        """

        try:
            logger.info("Waiting for instance {0} running ...".format(instance_id))
            instance_info = self.get_instance_info(instance_id)
            instance_status_checks = self.get_instance_status_checks(instance_id)
            logger.debug("Instance id: %s, state: %s" % (instance_id, instance_info._state))
            if (datetime.datetime.now() - self.start_time).seconds > 60 * 15:
                logger.error("After 15 minutes, initialization is not complete yet, script terminates")
                return False
            if re.search(r'terminated', str(instance_info._state)):
                logger.error("Instance id: %s, initialization termination" % instance_id)
                return False
            if re.search(r'shutting-down', str(instance_info._state)):
                raise Exception('Waitting for Instance {0} request complete (shutting-down)...'.format(instance_id))
            if re.search(r'Status:ok', str(instance_status_checks.system_status)) \
                    and re.search(r'Status:ok', str(instance_status_checks.instance_status)):
                use_time = (datetime.datetime.now() - self.start_time).seconds
                self.instance_ip.setdefault(instance_id, {})
                self.instance_ip[instance_id]['instance_type'] = instance_info.instance_type
                self.instance_ip[instance_id]['instance_id'] = instance_id
                self.instance_ip[instance_id]['ip'] = instance_info.ip_address
                self.instance_ip[instance_id]['private_ip'] = instance_info.private_ip_address
                self.instance_ip[instance_id]['lifecycle'] = lifecycle
                logger.info("Instance id: %s, initialization complete\nuse time: %s seconds\ninstance_id: %s\n"
                               "ip: %s\nprivete_ip: %s\nlifecycle: %s" % (instance_id, use_time,
                                                                          self.instance_ip[instance_id]['instance_id'],
                                                                          self.instance_ip[instance_id]['ip'],
                                                                          self.instance_ip[instance_id]['private_ip'],
                                                                          self.instance_ip[instance_id]['lifecycle']))
                return True
            else:
                raise Exception('System/Instance reachability check: Initializing[{0}]...'.format(instance_id))

        except Exception as e:
            raise Exception(e)

    @retry(tries=30, delay=10)
    def wait_spot_request_complete(self, request):
        """
        Waiting for reservation instance initialization complete
        :param request: spot request
        :return:
        """

        spot_info = self.get_spot_instance_info(request.id)
        if spot_info.instance_id:
            instance_id = spot_info.instance_id
            return instance_id
        elif re.search(r'terminated', spot_info.status.code):
            return False
        else:
            logger.debug(
                "Spot id: %s, status:\ncode: %s\nmessage: %s" % (request.id, request.status.code, request.status.message))
            raise Exception('Waitting for spot {0} request complete ...'.format(request.id))

    def multi_wait_instance_init(self):
        """
        multi wait for all reservation and spot init complete
        :return:
        """
        t_list = []

        for reservation in self.reservation_list:
            instances = reservation.instances
            for instance in instances:
                t = threading.Thread(target=self.wait_instance_running, args=(instance.id, 'normal'))
                t.start()
                t_list.append(t)

        for spot_request in self.spot_instance_request_list:
            instance_id = self.wait_spot_request_complete(spot_request)
            t = threading.Thread(target=self.wait_instance_running, args=(instance_id, 'spot'))
            t.start()
            t_list.append(t)

        # wait all sub thread finish
        for t in t_list:
            t.join()

    def cancel_spot_instance_requests(self, request_id):
        """
        Cancel spot instance requests
        :param request_id:
        :return:
        """

        try:
            # get instance id
            ret = self.get_spot_instance_info(request_id)
            instance_id = ret[0].instance_id

            # terminate instance
            self.terminate_instance(instance_id)

            # cancel spot instance
            ret = self.ec2_client.cancel_spot_instance_requests(request_id)
            logger.info("%s was canceled" % ret[0].id)
        except Exception as e:
            if e.message:
                logger.error(e.message)
            return False

        return True

    def get_spot_instance_info(self, request_id, show=False):
        """
        Get spot instance infomation
        :param request_id:
        :param show:show: Show detail or not
        :return:
        """

        try:
            instance_ret = self.ec2_client.get_all_spot_instance_requests(request_ids=[request_id])
            if show:
                prt_list = []
                for k, v in instance_ret[0].__dict__.iteritems():
                    prt_list.append("%30s: %-s" % (k, v))
                jsondumps_prt_list = json.dumps(prt_list, sort_keys=True, indent=4, separators=(',', ': '))
                logger.info("Request Id: %s\n" % request_id + jsondumps_prt_list)
        except Exception as e:
            raise Exception("Failed to get infomation of spot instance %s, %s" % (request_id, e))

        return instance_ret[0]

    def get_instance_info(self, instance_id, show=False):
        """
        Get instance infomation
        :param instance_id:
        :param show:show: Show detail or not
        :return:
        """

        try:
            instance_ret = self.ec2_client.get_only_instances(instance_ids=[instance_id])
            if show:
                prt_list = []
                for k, v in instance_ret[0].__dict__.iteritems():
                    prt_list.append("%30s: %-s" % (k, v))
                jsondumps_prt_list = json.dumps(prt_list, sort_keys=True, indent=4, separators=(',', ': '))
                logger.info("Request Id: %s\n" % instance_id + jsondumps_prt_list)
        except Exception as e:
            raise Exception("Failed to get instance [%s] infomation, %s" % (instance_id, e))

        return instance_ret[0]

    def get_instance_status_checks(self, instance_id, show=False):
        """
        Status Checks:
            System Status Checks  -- System reachability check passed
            Instance Status Checks  -- Instance reachability check passed
        :param instance_id:
        :param show:show: Show detail or not
        :return:
        """

        try:
            instance_ret = self.ec2_client.get_all_instance_status(instance_ids=instance_id)
            if show:
                prt_list = []
                for k, v in instance_ret[0].__dict__.iteritems():
                    prt_list.append("%30s: %-s" % (k, v))
                jsondumps_prt_list = json.dumps(prt_list, sort_keys=True, indent=4, separators=(',', ': '))
                logger.info("Request Id: %s\n" % instance_id + jsondumps_prt_list)
        except Exception as e:
            raise Exception("Failed to get instance [%s] infomation, %s" % (instance_id, e))

        return instance_ret[0]

    def start_instance(self, instance_id):
        """
        start instance
        :param instance_id:
        :return:
        """
        try:
            ret = self.ec2_client.start_instances(instance_ids=[instance_id])
            logger.info("%s was started")
        except Exception as e:
            logger.error("Failed to start %s, %s" % (instance_id, e.message))
            raise Exception()
        return True

    def stop_instance(self, instance_id):
        """
        stop instance
        :param instance_id:
        :return:
        """
        try:
            ret = self.ec2_client.start_instances(instance_ids=[instance_id])
            logger.info("%s was stopped")
        except Exception as e:
            logger.error("Failed to stop %s, %s" % (instance_id, e.message))
            raise Exception()
        return True

    def terminate_instance(self, instance_id):
        """
        terminate instance
        :param instance_id:
        :return:
        """
        try:
            ret = self.ec2_client.terminate_instances(instance_ids=[instance_id])
            logger.info("%s was terminated" % instance_id)
        except Exception as e:
            logger.error("Failed to terminate %s, %s" % (instance_id, e.message))
            raise Exception()
        return True

    def assign_private_ip(self, instance_id, ip_list=None, ip_count=None):
        """
        assign private ip
        :param instance_id:
        :param ip_list:
        :param ip_count:
        :return:
        """
        if not isinstance(ip_list, list) and not isinstance(ip_count, int):
            logger.warning("Error args, need a ip list or ip count!" % ip_list)
            raise Exception()

        try:
            info = self.get_instance_info(instance_id)
            if info:
                network_interface_id = info.interfaces[0].id
            else:
                return False

            rtn = self.ec2_client.assign_private_ip_addresses(network_interface_id, ip_list, ip_count)
            if not rtn:
                return False

            new_ip_list = ip_list if ip_list else self.get_instance_ips(instance_id)['secondary'][-ip_count:]
            return new_ip_list
        except Exception as e:
            raise Exception("Failed to assign private ip, {err}".format(err=e))

    def add_tags(self, instance_ids, tags):
        """
        Create new metadata tags for the specified instance ids.
        :param instance_ids: List of strings
        :param tags:A dictionary containing the name/value pairs. If you want to create only a tag name, the
                     value for that tag should be the empty string (e.g. '')
        :return:
        """
        try:
            ret = self.ec2_client.create_tags(instance_ids, tags, dry_run=False)
            if ret:
                logger.info("Create tags {} success".format(tags))
        except Exception as e:
            raise Exception(e)
        return True

    def get_instance_ips(self, instance_id):
        """
        Get instance all ips
        :param instance_id:
        :return:
        """
        ip_dict = {}
        try:
            info = self.get_instance_info(instance_id)
            for i in info.interfaces[0].private_ip_addresses:
                if i.primary:
                    ip_dict['primary'] = i.private_ip_address
                else:
                    ip_dict.setdefault('secondary', [])
                    ip_dict['secondary'].append(i.private_ip_address)
            return ip_dict
        except Exception as e:
            logger.error(e)


class IAMObj(object):
    _iam_client = None

    def __init__(self, aws_access_key_id, aws_secret_access_key):
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key

    @property
    def iam_client(self):
        """
        Connect IMA Client
        :return:
        """
        if self._iam_client is None:
            self._iam_client = boto.iam.connection.IAMConnection(
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key)
        return self._iam_client

    def check_instance_profile(self, profile_name):
        try:
            profile = self.iam_client.get_instance_profile(profile_name)
            name = profile['get_instance_profile_response']['get_instance_profile_result']['instance_profile']['instance_profile_name']
            arn = profile['get_instance_profile_response']['get_instance_profile_result']['instance_profile']['arn']
            # print profile
            logger.debug("Instance profile info,\nname: %s\narn: %s" % (name, arn))
        except Exception as e:
            logger.error("Failed to get Instance profile, message: %s" % (e.message))
            raise Exception()

        return True


if __name__ == "__main__":
    pass
