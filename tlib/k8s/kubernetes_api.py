# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/16 15:23
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""Kubernetes Python Client
Usage of Official Python client library for kubernetes
FYI: https://github.com/kubernetes-client/python
"""

import json
import urllib3
from kubernetes import config, client
from kubernetes.stream import stream
from kubernetes.client.rest import ApiException

from tlib import log
from tlib.utils import util
from tlib.retry import retry

# =============================
# --- Global Value
# =============================
logger = log.get_logger()
urllib3.disable_warnings()


class KubernetesApi(object):
    is_connected = None
    _corev1api = None
    _appsv1api = None
    _appsv1betaapi = None
    _extensionsv1betaapi = None

    def __init__(self, host=None, secret=None, config_file=None,
                 namespace="default"):
        self.host = host  # api server
        self.secret = secret  # api key
        self.config_file = config_file  # config_file full path
        self.namespace = namespace

    @property
    def client_config(self):
        configuration = client.Configuration()
        configuration.host = self.host
        configuration.verify_ssl = False
        configuration.debug = False
        configuration.api_key = {"authorization": "Bearer " + self.secret}
        return configuration

    def connect(self):
        client.configuration.assert_hostname = False
        try:
            config.load_kube_config(self.config_file)
        except IOError:
            client.Configuration.set_default(self.client_config)
        self.is_connected = True

    @property
    def corev1api(self):
        if self._corev1api is None:
            if self.is_connected is None:
                self.connect()
            self._corev1api = client.CoreV1Api()
        return self._corev1api

    @property
    def appsv1api(self):
        if self._appsv1api is None:
            if self.is_connected is None:
                self.connect()
            self._appsv1api = client.AppsV1Api()
        return self._appsv1api

    @property
    def appsv1betaapi(self):
        if self._appsv1betaapi is None:
            if self.is_connected is None:
                self.connect()
            self._appsv1betaapi = client.AppsV1Api()  # AppsV1beta1Api
        return self._appsv1betaapi

    @property
    def extensionsv1betaapi(self):
        if self._extensionsv1betaapi is None:
            if self.is_connected is None:
                self.connect()
            self._extensionsv1betaapi = client.AppsV1Api()  # ExtensionsV1beta1Api
        return self._extensionsv1betaapi

    def run_cmd(self, pod_name, cmd, container=None, timeout=360, run_async=False, stdout=True):
        rtn_dict = {'stdout': None, 'stderr': None}
        r_code = 1
        json_stdout = ''

        try:
            if container:
                'Execute: ssh root@10.25.119.76# ls /etc/kubernetes/pki/etcd/'
                logger.info('Execute on pod [{0}:{1}]# {2}'.format(pod_name, container, cmd))
                resp = stream(self.corev1api.connect_get_namespaced_pod_exec, name=pod_name, namespace=self.namespace,
                              command=['/bin/bash'], container=container, stderr=True, stdin=True, stdout=True,
                              tty=False, _preload_content=False)
            else:
                logger.info('Execute on pod [{0}]# {1}'.format(pod_name, cmd))
                resp = stream(self.corev1api.connect_get_namespaced_pod_exec, name=pod_name, namespace=self.namespace,
                              command=['/bin/bash'], stderr=True, stdin=True, stdout=True,
                              tty=False, _preload_content=False)
            break_f = False
            resp.update(timeout=timeout)
            while resp.is_open():
                if not run_async:
                    # resp.update(timeout=timeout)
                    if resp.peek_stdout():
                        json_stdout += resp.read_stdout(timeout=timeout)
                    if break_f:
                        break
                    resp.write_stdin("/opt/node/util/pod_console.sh \"{}\"\n".format(cmd))
                    break_f = True
                elif stdout:
                    # resp.update(timeout=timeout)
                    resp.write_stdin("{}\n ".format(cmd))
                    if resp.peek_stdout() or resp.peek_stderr():
                        rtn_dict['stdout'] = resp.read_stdout(timeout=timeout).strip()
                        rtn_dict['stderr'] = resp.read_stderr(timeout=timeout).strip()
                        break
                else:
                    resp.write_stdin("{}\n ".format(cmd))
                    break
            resp.close()
            if not run_async:
                r_code = 0
            elif not run_async and (not json_stdout):
                # time out
                r_code = 1
                rtn_dict['stderr'] = "timeout"
            elif not run_async and json_stdout:
                json_info = json.loads(json_stdout.strip(), strict=False)
                r_code = int(json_info['r_code'])
                if int(r_code) == 0:
                    rtn_dict['stdout'] = json_info['message']
                else:
                    rtn_dict['stderr'] = json_info['message']
            elif run_async:
                r_code = 0
            else:
                pass

        except ApiException as e:
            raise e

        return r_code, rtn_dict

    def pod_exec_cmd(self, pod_name, cmd, container=None, timeout=360):
        rtn_dict = {'stdout': None, 'stderr': None}
        try:
            if container:
                logger.info('Run {0} on {1}:{2}'.format(cmd, pod_name, container))
                resp = stream(self.corev1api.connect_get_namespaced_pod_exec,
                              name=pod_name, namespace=self.namespace, command=['/bin/bash'], container=container,
                              stderr=True, stdout=True, stdin=True, tty=False, _preload_content=False)
            else:
                logger.info('Run {cmd} on {pod_name}'.format(cmd=cmd, pod_name=pod_name))
                resp = stream(self.corev1api.connect_get_namespaced_pod_exec,
                              name=pod_name, namespace=self.namespace, command=['/bin/bash'],
                              stderr=True, stdout=True, stdin=True, tty=False, _preload_content=False)

            while resp.is_open():
                resp.update(timeout=timeout)
                resp.write_stdin("{}\n ".format(cmd))
                if resp.peek_stdout() or resp.peek_stderr():
                    rtn_dict['stdout'] = resp.read_stdout(timeout=timeout).strip()
                    rtn_dict['stderr'] = resp.read_stderr(timeout=timeout).strip()
                    break
            resp.close()
        except ApiException as e:
            raise e

        r_code = -1 if rtn_dict['stderr'] else 0

        return r_code, rtn_dict

    # ============ Node ============
    @property
    def nodes_info(self):
        all_info = self.corev1api.list_node()

        nodes_info = []
        for node_info in all_info.items:
            tmp_info = {}
            tmp_info['name'] = node_info.metadata.name
            tmp_info['labels'] = node_info.metadata.labels
            tmp_info['ip'] = node_info.metadata.annotations[
                'projectcalico.org/IPv4Address'].split('/')[0]
            for condition in node_info.status.conditions:
                if condition.type == 'Ready':
                    tmp_info['status'] = condition.status
                    break

            tmp_info['images'] = []
            for image_info in node_info.status.images:
                for image_name in image_info.names:
                    if '@sha256' not in image_name:
                        tmp_info['images'].append(image_name)

            nodes_info.append(tmp_info)

        return nodes_info

    @property
    def nodes_name_list(self):
        node_list = self.corev1api.list_node()
        return [node.metadata.name for node in node_list.items] if \
            node_list.items else []

    def get_node_list_by_label(self, label_selector):
        nodes_info = self.corev1api.list_node(
            label_selector=label_selector
        )
        return nodes_info.items

    def get_node_name_list_by_label(self, label_selector):
        node_list = self.get_node_list_by_label(label_selector)
        return [node.metadata.name for node in node_list] if node_list else []

    def get_node_name_list_by_pod_label(self, label_selector):
        """
        get_nodes_name_list by pod label_selector
        :param label_selector: "key=value"
        :return:
        """
        pod_list = self.get_pod_list_by_label(label_selector)
        return [pod['spec']['node_name'] for pod in pod_list if
                pod['spec']['node_name']]

    def get_node_ip_list_by_label(self, label_selector):
        node_ip_list = []
        nodes_info = self.get_node_list_by_label(label_selector)
        for node_info in nodes_info:
            node_ip = node_info.metadata.annotations[
                'projectcalico.org/IPv4Address'].split('/')[0]
            node_ip_list.append(node_ip)

        return node_ip_list

    def get_node_ip_by_name(self, node_name, ip_type='ExternalIP'):
        node_data = self.corev1api.read_node(node_name)
        for ip_info in node_data.status.addresses:
            if ip_info.type == ip_type:
                return ip_info.address
        else:
            return None

    def get_node_ipv4_by_name(self, node_name):
        node_data = self.corev1api.read_node(node_name)
        node_annotations = node_data.metadata.annotations
        return node_annotations['projectcalico.org/IPv4Address'].split('/')[0]

    def update_node_label(self, node_name, labels):
        p_node_data = self.corev1api.read_node(name=node_name)
        p_labels = p_node_data.metadata.labels

        if set(labels.keys()).issubset(set(p_labels.keys())):
            logger.info(
                'Update node label {0} -> {1} ...'.format(node_name, labels))
            self.corev1api.patch_node(
                node_name,
                {
                    'metadata': {
                        'labels': labels
                    }
                }
            )
        else:
            logger.warning('Try to add new label name, ignore!')

    def disable_node_label(self, node_name, label_name):
        self.update_node_label(node_name, labels={label_name: 'false'})

    def enable_node_label(self, node_name, label_name):
        self.update_node_label(node_name, labels={label_name: 'true'})

    # ============ deployment ============
    @property
    def deployment_name_list(self):
        deployment_info = self.appsv1betaapi.list_namespaced_deployment(
            namespace=self.namespace
        )

        deployment_list = []
        for deployment in deployment_info.items:
            deployment_list.append(deployment.metadata.name)

        return deployment_list

    def get_deployment_name_list_by_label(self, label_selector):
        """
        get_deployment_name_list by label_selector
        :param label_selector: "key=value"
        :return:
        """
        deployment_info = self.appsv1betaapi.list_namespaced_deployment(
            namespace=self.namespace,
            label_selector=label_selector
        )

        deployment_name_list = []
        for deployment in deployment_info.items:
            deployment_name_list.append(deployment.metadata.name)

        return deployment_name_list

    def get_deployment_data(self, deployment_name):
        deployment_data = self.appsv1betaapi.read_namespaced_deployment(
            name=deployment_name, namespace=self.namespace)
        return deployment_data

    def get_deployment_last_applied_config(self, deployment_name):
        deployment_data = self.get_deployment_data(deployment_name).to_dict()
        last_config = deployment_data['metadata']['annotations'][
            'kubectl.kubernetes.io/last-applied-configuration']
        return json.loads(last_config)

    def set_deployment_env(self, deployment_name, container_name, env_name,
                           env_value):
        logger.info(
            'Set {0} env: "name:{1}, value:{2}" ...'.format(deployment_name,
                                                            env_name,
                                                            env_value))
        p_deployment_data = self.appsv1betaapi.read_namespaced_deployment(
            deployment_name, self.namespace)
        p_containers = p_deployment_data.spec.template.spec.containers
        p_env_list = []
        for p_container in p_containers:
            if p_container.name == container_name:
                p_env_list = p_container.env

        # {'name': 'CAPT_SCORE', 'value': '0', 'value_from': None}
        for p_env in p_env_list:
            if p_env.name == env_name:
                p_index = p_env_list.index(p_env)
                p_env_list[p_index].value = env_value
                break
        else:
            p_env_list.insert(0, {'name': env_name, 'value': str(env_value),
                                  'value_from': None})

        deployment_spec_template_spec_containers = [
            client.V1Container(
                name=container_name,
                env=p_env_list
            )
        ]

        deployment_spec_template_spec = client.V1PodSpec(
            containers=deployment_spec_template_spec_containers
        )

        deployment_spec_template = client.V1PodTemplateSpec(
            spec=deployment_spec_template_spec
        )

        deployment_spec = client.AppsV1beta1DeploymentSpec(
            template=deployment_spec_template
        )

        deployment = client.ExtensionsV1beta1Deployment(
            spec=deployment_spec
        )

        self.appsv1betaapi.patch_namespaced_deployment(
            name=deployment_name,
            namespace=self.namespace,
            body=deployment
        )

    def set_replicas_for_deployment(self, deployment_name, replicas=0):
        logger.info(
            'Set {0} replicas={1} ...'.format(deployment_name, replicas))
        self.appsv1betaapi.patch_namespaced_deployment(
            name=deployment_name,
            namespace=self.namespace,
            body={
                "spec": {
                    "replicas": replicas
                }
            }
        )

    def set_image_for_deployment(self, deployment_name, container_name, image):
        deployment_spec_template_spec_containers = [
            client.V1Container(
                name=container_name,
                image=image
            )
        ]

        deployment_spec_template_spec = client.V1PodSpec(
            containers=deployment_spec_template_spec_containers
        )

        deployment_spec_template = client.V1PodTemplateSpec(
            spec=deployment_spec_template_spec
        )

        deployment_spec = client.AppsV1beta1DeploymentSpec(
            template=deployment_spec_template
        )

        deployment = client.ExtensionsV1beta1Deployment(
            spec=deployment_spec
        )

        self.appsv1betaapi.patch_namespaced_deployment(
            name=deployment_name,
            namespace=self.namespace,
            body=deployment
        )

    # ============ statefulset(sts) ============
    def get_statefulset_name_list_by_label(self, label_selector):
        """
        get_statefulset_name_list by label_selector
        :param label_selector: "key=value"
        :return:
        """
        stateful_set_info = self.appsv1betaapi.list_namespaced_stateful_set(
            namespace=self.namespace,
            label_selector=label_selector
        )

        sts_name_list = []
        for stateful_set in stateful_set_info.items:
            sts_name_list.append(stateful_set.metadata.name)

        return sts_name_list

    def get_statefulset_data(self, sts_name):
        statefulset_data = self.appsv1betaapi.read_namespaced_stateful_set(
            name=sts_name, namespace=self.namespace)
        return statefulset_data

    def get_statefulset_last_applied_config(self, sts_name):
        statefulset_data = self.get_statefulset_data(sts_name).to_dict()
        last_config = statefulset_data['metadata']['annotations'][
            'kubectl.kubernetes.io/last-applied-configuration']
        return json.loads(last_config)

    def set_replicas_for_stateful_set(self, sts_name, replicas=0):
        logger.info('Set {0} replicas={1} ...'.format(sts_name, replicas))
        self.appsv1betaapi.patch_namespaced_stateful_set(
            name=sts_name,
            namespace=self.namespace,
            body={
                "spec": {
                    "replicas": replicas
                }
            }
        )

    def set_image_for_stateful_set(self, sts_name, container_name,
                                   service_name, image):
        stateful_set_spec_template_spec_containers = [
            client.V1Container(
                name=container_name,
                image=image
            )
        ]

        stateful_set_spec_template_spec = client.V1PodSpec(
            containers=stateful_set_spec_template_spec_containers
        )

        stateful_set_spec_template = client.V1PodTemplateSpec(
            spec=stateful_set_spec_template_spec
        )

        stateful_set_spec = client.V1beta1StatefulSetSpec(
            template=stateful_set_spec_template,
            service_name=service_name
        )

        stateful_set = client.V1beta1StatefulSet(
            spec=stateful_set_spec
        )

        self.appsv1betaapi.patch_namespaced_stateful_set(
            name=sts_name,
            namespace=self.namespace,
            body=stateful_set
        )

    def get_image_from_statefulsets(self, sts_name):
        image = ''
        statefulset_data = self.appsv1betaapi.read_namespaced_stateful_set(
            name=sts_name, namespace=self.namespace)
        containers = statefulset_data.spec.template.spec.containers
        for container in containers:
            if container.name == sts_name.split('-')[0]:
                image = container.image
                break
        return image

    # ============ daemonset(ds) ============
    @property
    def daemon_set_name_list(self):
        daemon_set_info = self.extensionsv1betaapi.list_namespaced_daemon_set(
            namespace=self.namespace
        )

        daemon_set_list = []
        for daemon_set in daemon_set_info.items:
            daemon_set_list.append(daemon_set.metadata.name)

        return daemon_set_list

    def get_daemonset_name_list_by_label(self, label_selector):
        """
        get_daemonset_name_list by label_selector
        :param label_selector: "key=value"
        :return:
        """
        daemon_set_info = self.extensionsv1betaapi.list_namespaced_daemon_set(
            namespace=self.namespace,
            label_selector=label_selector
        )

        ds_name_list = []
        for daemon_set in daemon_set_info.items:
            ds_name_list.append(daemon_set.metadata.name)

        return ds_name_list

    def set_image_for_daemon_set(self, ds_name, container_name, image):
        daemon_set_spec_template_spec_containers = [
            client.V1Container(
                name=container_name,
                image=image
            )
        ]

        daemon_set_spec_template_spec = client.V1PodSpec(
            containers=daemon_set_spec_template_spec_containers
        )

        daemon_set_spec_template = client.V1PodTemplateSpec(
            spec=daemon_set_spec_template_spec
        )

        daemon_set_spec = client.V1beta1DaemonSetSpec(
            template=daemon_set_spec_template
        )

        daemon_set = client.V1beta1DaemonSet(
            spec=daemon_set_spec
        )

        self.extensionsv1betaapi.patch_namespaced_daemon_set(
            name=ds_name,
            namespace=self.namespace,
            body=daemon_set
        )

    # ============ pod ============
    @property
    def pod_name_list(self):
        all_pod_name_list = []
        all_info = self.corev1api.list_namespaced_pod(namespace=self.namespace)
        for pod_info in all_info.items:
            pod_name = pod_info.metadata.name
            all_pod_name_list.append(pod_name)

        return all_pod_name_list

    def get_pod_info_by_name(self, pod_name):
        return self.corev1api.read_namespaced_pod(
            name=pod_name,
            namespace=self.namespace
        )

    def get_pod_status_by_name(self, pod_name):
        return self.corev1api.read_namespaced_pod_status(
            name=pod_name,
            namespace=self.namespace
        )

    def get_pod_list_by_label(self, label_selector):
        """
        get pod list by label_selector
        :param label_selector: "key=value"
        :return:
        """
        pod_list = self.corev1api.list_namespaced_pod(
            namespace=self.namespace,
            label_selector=label_selector
        )
        if len(pod_list.items) >= 1:
            return pod_list.to_dict()['items']
        return []
        # raise Exception('Failed to get pod')

    def get_pods_info_by_label(self, label_selector=None):
        if label_selector:
            all_pods_info = self.corev1api.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=label_selector
            )
        else:
            all_pods_info = self.corev1api.list_namespaced_pod(
                namespace=self.namespace
            )

        pods_info_list = []
        for pod_info in all_pods_info.items:
            pod_name = pod_info.metadata.name
            tmp_pod_info = {}
            tmp_pod_info['name'] = pod_name
            tmp_pod_info['host_ip'] = pod_info.status.host_ip
            tmp_pod_info['pod_ip'] = pod_info.status.pod_ip
            tmp_pod_info['status'] = pod_info.status.phase
            tmp_pod_info['node_name'] = pod_info.spec.node_name
            tmp_pod_info['containers'] = []
            tmp_pod_info['restart_count'] = 0
            if pod_info.status.container_statuses is not None:
                for container_status in pod_info.status.container_statuses:
                    tmp_container_stat = {}
                    if container_status.container_id is not None:
                        tmp_container_stat['container_id'] = container_status.container_id.split('//')[-1]
                    else:
                        tmp_container_stat['container_id'] = container_status.container_id

                    tmp_container_stat['image'] = container_status.image
                    tmp_container_stat['ready'] = container_status.ready
                    tmp_container_stat['restarts'] = container_status.restart_count

                    tmp_pod_info['restart_count'] += container_status.restart_count
                    tmp_pod_info['containers'].append(tmp_container_stat)
            pods_info_list.append(tmp_pod_info)

        return pods_info_list

    def get_pod_list_by_node(self, node_name, label_selector):
        """
        get_pod_list on nodes by label_selector
        :param node_name:
        :param label_selector: "key=value"
        :return:
        """
        pod_list = []
        all_pods = self.get_pod_list_by_label(label_selector)
        for pod in all_pods:
            if pod['spec']['node_name'] == node_name:
                pod_list.append(pod)
        return pod_list

    def delete_pod(self, pod_name, grace_period_seconds=60):
        try:
            self.corev1api.delete_namespaced_pod(
                namespace=self.namespace,
                name=pod_name,
                grace_period_seconds=grace_period_seconds,
                body={}
            )
        except Exception as e:
            if 'Not Found' in str(e):
                logger.warning(e)
            else:
                raise Exception(e)

    def delete_all_pods_for_deployment(self, deployment_name):
        try:
            self.set_replicas_for_deployment(deployment_name, replicas=0)
        except ApiException as e:
            if e.status == 404:
                logger.warning("Not found, ignore")
            else:
                raise e
        else:
            for pod in self.get_pod_list_by_label(deployment_name):
                pod_name = pod['metadata']['name']
                logger.info('pod name {}'.format(pod_name))
                logger.info('pod status {} '.format(
                    self.get_pod_status_by_name(pod_name)))
                self.delete_pod(pod_name)

    def is_pod_running_by_pod_name(self, pod_name):
        try:
            the_pod = self.get_pod_status_by_name(pod_name)
            return True if the_pod.status.phase in ['Running'] else False
        except Exception as e:
            logger.warning(e)
            return False

    @retry(tries=60, delay=20)
    def is_pod_ready_by_pod_name(self, pod_name):
        try:
            the_pod = self.get_pod_info_by_name(pod_name)
        except ApiException as e:
            if e.status == '404':
                raise Exception(e)
            else:
                logger.warning('get pod failed!')
                logger.warning('{}'.format(e.body))
                raise e
        if the_pod and the_pod.status.container_statuses:
            for container_status in the_pod.status.container_statuses:
                container_name = container_status.name
                if container_status.ready:
                    logger.info(
                        'Pod {0} containers [{1}] ready!'.format(pod_name,
                                                                 container_name))
                else:
                    raise Exception(
                        'Pod {0} containers [{1}] not ready!'.format(pod_name,
                                                                     container_name))

        return True

    @retry(tries=60, delay=20)
    def is_pod_not_ready_by_pod_name(self, pod_name):
        try:
            the_pod = self.get_pod_info_by_name(pod_name)
        except ApiException as e:
            if e.status == '404':
                raise Exception(e)
            else:
                logger.warning('get pod failed!')
                logger.warning('{}'.format(e.body))
                raise e
        if the_pod and the_pod.status.container_statuses:
            for container_status in the_pod.status.container_statuses:
                container_name = container_status.name
                if not container_status.ready:
                    logger.info(
                        'Pod {0} containers [{1}] not ready!'.format(pod_name,
                                                                     container_name))
                else:
                    raise Exception(
                        'Pod {0} containers [{1}] still is ready!'.format(
                            pod_name, container_name))

        return True

    @retry(tries=60, delay=20)
    def is_all_pod_ready(self, pod_label, node_name=None, skip_empty=False):
        """
        is_all_pod_ready
        :param pod_label:
        :param node_name:
        :param skip_empty:
        :return:
        """
        pod_list = self.get_pod_list_by_label(pod_label)
        if not pod_list and not skip_empty:
            raise Exception('Got None pods!')

        for the_pod in pod_list:
            the_node_name = the_pod['spec']['node_name']
            if node_name and the_node_name != node_name:
                continue
            the_pod_name = the_pod['metadata']['name']
            logger.info('> Check pod ready: {0} ({1})'.format(the_pod_name,
                                                              the_node_name))
            if the_pod and the_pod['status']['container_statuses']:
                for container_status in the_pod['status'][
                    'container_statuses']:
                    container_name = container_status['name']
                    if container_status['ready']:
                        logger.info('Pod {0} containers [{1}] ready!'.format(
                            the_pod_name, container_name))
                    else:
                        raise Exception(
                            'Pod {0} containers [{1}] not ready!'.format(
                                the_pod_name, container_name))
            else:
                raise Exception(
                    'Pod {0} containers not ready!'.format(the_pod_name))
        return True

    @retry(tries=60, delay=20)
    def is_all_pod_down(self, pod_label, node_name=None):
        pod_list = self.get_pod_list_by_label(pod_label)
        for the_pod in pod_list:
            if node_name and the_pod['spec']['node_name'] != node_name:
                continue
            pod_name = the_pod['metadata']['name']
            raise Exception('Pod {0} not down!'.format(pod_name))

        return True

    @retry(tries=120, delay=15)
    def wait_pod_ready(self, pod_name=None, pod_name_startswith=None,
                       origin_pod_name_list=None):
        """
        wait for pod ready: Running
        :param pod_name:
        :param pod_name_startswith:
        :param origin_pod_name_list:
        :return:
        """
        if origin_pod_name_list is None:
            origin_pod_name_list = []
        assert pod_name or pod_name_startswith

        all_info = self.corev1api.list_namespaced_pod(namespace=self.namespace)
        for p_info in all_info.items:
            p_name = p_info.metadata.name
            if pod_name:
                if p_name != pod_name:
                    continue
            elif pod_name_startswith:
                if not p_name.startswith(pod_name_startswith):
                    continue
            else:
                pass
            if origin_pod_name_list and p_name in origin_pod_name_list:
                continue

            host_ip = p_info['host_ip']
            if p_info['status'] != 'Running' or \
                    not p_info['containers'][0]['ready']:
                logger.warning('Wait pod {0} on {1} start.'.format(p_name, host_ip))
                raise Exception('Pod {0} is not ready'.format(p_name))
            else:
                logger.info('Pod {0} on {1} is ready.'.format(p_name, host_ip))
                return True
        else:
            if pod_name:
                logger.error('Not found the pod name {}!'.format(pod_name))
            else:
                logger.error('Not found the pod name start with {}!'.format(pod_name_startswith))
            return False

    def wait_pod_ready_by_startswith(self, pod_startswith):
        return self.wait_pod_ready(None, pod_startswith, None)

    def wait_new_pod_ready_by_startswith(self, pod_startswith, origin_pod_name_list):
        return self.wait_pod_ready(None, pod_startswith, origin_pod_name_list)

    @retry(tries=30, delay=20)
    def wait_pod_terminated(self, pod_name=None, pod_name_startswith=None):
        """
        wait for pod terminated
        :param pod_name:
        :param pod_name_startswith:
        :return:
        """

        assert pod_name or pod_name_startswith
        all_info = self.corev1api.list_namespaced_pod(namespace=self.namespace)
        for p_info in all_info.items:
            p_name = p_info.metadata.name
            if pod_name:
                if p_name == pod_name:
                    logger.warning('Wait pod {0} terminating!'.format(p_name))
                    raise Exception('Pod {0} is not terminated'.format(p_name))
            elif pod_name_startswith:
                if p_name.startswith(pod_name_startswith):
                    logger.warning('Wait pod {0}* terminating!'.format(pod_name_startswith))
                    raise Exception('Pod {0} is not terminated'.format(p_name))
            else:
                raise Exception('Please specify what pods to wait terminated!')
        else:
            if pod_name:
                logger.info('Pod {0} terminate done!'.format(pod_name))
            else:
                logger.info('Pod {0}* terminate done!'.format(pod_name_startswith))
        return True

    def wait_pod_terminated_by_startswith(self, pod_startswith):
        return self.wait_pod_terminated(None, pod_startswith)

    # ============ service(svc) ============
    @property
    def services_info(self):
        all_info = self.corev1api.list_service_for_all_namespaces()
        services_info = {}
        for service_info in all_info.items:
            service_name = service_info.metadata.name
            services_info[service_name] = {}
            services_info[service_name]['name'] = service_name
            services_info[service_name]['type'] = service_info.spec.type
            services_info[service_name]['cluster_ip'] = service_info.spec.cluster_ip
            if service_info.spec.type == 'ClusterIP':
                services_info[service_name]['external_ips'] = service_info.spec._external_i_ps
            elif service_info.spec._type == 'LoadBalancer':
                services_info[service_name]['external_ips'] = []
                for ingress in service_info.status._load_balancer.ingress:
                    services_info[service_name]['external_ips'].append(ingress.ip)
            else:
                services_info[service_name]['external_ips'] = []

        return services_info

    def get_service_info_by_name(self, svc_name):
        service_info = self.corev1api.read_namespaced_service(svc_name, self.namespace)
        return service_info

    def get_service_external_ips(self, svc_name):
        svc_external_ips = []
        try:
            service_info = self.get_service_info_by_name(svc_name)
        except Exception as e:
            logger.warning("FAIL: Get svc {0}!\n{1}".format(svc_name, e))
        else:
            if service_info.spec.type == 'ClusterIP':
                if service_info.spec._external_i_ps:
                    svc_external_ips = service_info.spec._external_i_ps
                else:
                    svc_external_ips = [service_info.spec._cluster_ip]
            elif service_info.spec._type == 'LoadBalancer':
                for ingress in service_info.status._load_balancer.ingress:
                    svc_external_ips.append(ingress.ip)
            else:
                svc_external_ips = []

        return svc_external_ips

    def set_service_external_ips(self, service_name, external_ips):
        """
        edit a service external_ips, location as follow

        spec:
          clusterIP: 10.233.2.3
          externalIPs:
          - 10.25.119.69

        :param service_name:
        :param external_ips: a list of ips
        :return:
        """

        try:
            assert isinstance(external_ips, list)
            self.corev1api.patch_namespaced_service(
                name=service_name,
                namespace=self.namespace,
                body={
                    "spec": {
                        "externalIPs": external_ips
                    }
                }
            )
        except Exception as e:
            raise e

    def create_service(self, service_type, selector, service_name,
                       port_list=None, external_ips=None, cluster_ip=None,
                       node_port=None):
        service_spec_clusterip = None
        service_spec_ports = None
        service_spec_externalips = None
        service_spec_external_traffic_policy = None
        service_spec_type = None
        service_spec_session_affinity = 'ClientIP'
        service_spec_selector = selector

        # Cluster ip
        if service_type == 'cluster_ip':
            service_spec_clusterip = cluster_ip
            if port_list is not None:
                service_spec_ports = [
                    client.V1ServicePort(
                        name='p{}'.format(port),
                        protocol='TCP',
                        port=port,
                        target_port=port
                    ) for port in port_list
                ]

        # External ip
        elif service_type == 'external_ip':
            service_spec_externalips = external_ips
            if port_list is not None:
                service_spec_ports = [
                    client.V1ServicePort(
                        name='p{}'.format(port),
                        protocol='TCP',
                        port=port,
                        target_port=port
                    ) for port in port_list
                ]

        # network 3 and 4 do NOT need service

        # Node port
        elif service_type == 'node_port':
            service_spec_clusterip = cluster_ip
            service_spec_external_traffic_policy = 'Cluster'
            if port_list is not None:
                service_spec_ports = [
                    client.V1ServicePort(
                        name='p{}'.format(port),
                        protocol='TCP',
                        port=port,
                        target_port=port,
                        node_port=node_port
                    ) for port in port_list
                ]
                service_spec_type = 'NodePort'

        service_spec = client.V1ServiceSpec(
            selector=service_spec_selector,
            ports=service_spec_ports,
            cluster_ip=service_spec_clusterip,
            external_i_ps=service_spec_externalips,
            external_traffic_policy=service_spec_external_traffic_policy,
            type=service_spec_type,
            session_affinity=service_spec_session_affinity
        )

        service_metadata = client.V1ObjectMeta(
            name=service_name
        )

        service = client.V1Service(
            metadata=service_metadata,
            spec=service_spec
        )

        try:
            self.corev1api.create_namespaced_service(
                namespace=self.namespace,
                body=service,
                pretty=True
            )
        except Exception as e:
            raise e

    # ============ secret ============
    def get_secret_info_by_name(self, secret_name):
        secret_info = self.corev1api.read_namespaced_secret(secret_name, self.namespace)
        return secret_info

    # ============ configmap(cm) ============
    def get_configmap_data_by_name(self, name):
        configmap = self.corev1api.read_namespaced_config_map(
            namespace=self.namespace,
            name=name
        )

        return configmap.data

    def update_configmap_data(self, name, data):
        logger.info('update configmap {0} data ...'.format(name))
        previous_configmap = self.corev1api.read_namespaced_config_map(
            namespace=self.namespace,
            name=name
        )

        previous_data = previous_configmap.data if previous_configmap.data else {}
        previous_data.update(data)

        self.corev1api.patch_namespaced_config_map(
            namespace=self.namespace,
            name=name,
            body={
                'data': previous_data
            }
        )


if __name__ == '__main__':
    pass
