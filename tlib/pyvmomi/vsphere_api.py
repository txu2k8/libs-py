# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/14 10:22
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""
Usage for the pyVmomi library
pyVmomi is the Python SDK for the VMware vSphere API that allows you to manage
ESX, ESXi, and vCenter.

FYI:
pyVmomi library: https://github.com/vmware/pyvmomi/
Pydoc https://www.pydoc.io/pypi/pyvmomi-6.7.0/index.html
Community Samples: http://vmware.github.io/pyvmomi-community-samples/
"""

import os
import re
import time
from threading import Thread
import unittest
import ssl
import atexit
from concurrent.futures import ThreadPoolExecutor, as_completed

from pyVim import connect  # pip install pyVmomi
from pyVim.task import WaitForTask
from pyVmomi import vim
from pyVmomi import vmodl

from tlib import log
from tlib.retry import retry
from tlib.utils import util

# =============================
# --- Global
# =============================
logger = log.get_logger()


class VsphereApi(object):
    """Use the pyVmomi to manage ESX, ESXi, and vCenter"""
    _si = None
    _content = None

    def __init__(self, host, user, password, port=443):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.ssl_context = None

    @retry(tries=3, delay=10)
    def connect_instance(self):
        if hasattr(ssl, '_create_unverified_context'):
            self.ssl_context = ssl._create_unverified_context()

        try:
            # form a connection...
            si = connect.SmartConnect(host=self.host,
                                      user=self.user,
                                      pwd=self.password,
                                      port=self.port,
                                      sslContext=self.ssl_context
                                      )
            # doing this means you don't need to remember to disconnect your
            # script/objects
            atexit.register(connect.Disconnect, si)
        except Exception as e:
            raise e

        if not si:
            raise SystemExit("Unable to connect to host with supplied info.")
        logger.info('Connected to vcenter: {0}'.format(self.host))
        return si

    def disconnect_instance(self):
        if self._si is not None:
            connect.Disconnect(self._si)

    @property
    def si(self):
        """return the service instance object"""
        if self._si is None:
            self._si = self.connect_instance()
        return self._si

    @property
    def content(self):
        if self._content is None:
            self._content = self.si.RetrieveContent()
        return self._content

    def wait_for_tasks(self, tasks):
        """
        returns after all the tasks are complete
        :param tasks: task objects list
        :return:
        """
        property_collector = self.si.content.propertyCollector
        task_list = [str(task) for task in tasks]
        # Create filter
        obj_specs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task)
                     for task in tasks]
        property_spec = vmodl.query.PropertyCollector.PropertySpec(
            type=vim.Task,
            pathSet=[],
            all=True)
        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.objectSet = obj_specs
        filter_spec.propSet = [property_spec]
        pcfilter = property_collector.CreateFilter(filter_spec, True)
        try:
            version, state = None, None
            # Loop looking for updates till the state moves to completed state.
            while len(task_list):
                update = property_collector.WaitForUpdates(version)
                for filter_set in update.filterSet:
                    for obj_set in filter_set.objectSet:
                        task = obj_set.obj
                        for change in obj_set.changeSet:
                            if change.name == 'info':
                                state = change.val.state
                            elif change.name == 'info.state':
                                state = change.val
                            else:
                                continue

                            if not str(task) in task_list:
                                continue

                            if state == vim.TaskInfo.State.success:
                                # Remove task from taskList
                                task_list.remove(str(task))
                            elif state == vim.TaskInfo.State.error:
                                raise task.info.error
                # Move to next version
                version = update.version
        finally:
            if pcfilter:
                pcfilter.Destroy()

    def get_obj(self, vimtype, name, show=False):
        """
        Return an object by name, if name is None the
        first found object is returned
        :param vimtype: such as [vim.Datacenter]
        :param name:
        :param show: print the obj
        :return:
        """
        obj = None
        container = self.content.viewManager.CreateContainerView(
            self.content.rootFolder, vimtype, True)
        for c in container.view:
            if name:
                if c.name == name:
                    obj = c
                    break
            else:
                obj = c
                break

        if show and obj:
            print("obj.name:" + str(obj.name))

        return obj

    @staticmethod
    def get_obj_in_list(obj_name, obj_list):
        """
        Return an object out of a list (obj_list) who's name matches obj_name.
        """
        for obj in obj_list:
            if obj.name == obj_name:
                return obj
        raise Exception("Unable to find object by the name of %s in list:\n%s"
                        % (obj_name, map(lambda obj: obj.name, obj_list)))

    def rename_obj(self, obj, new_name):
        print("renaming from %s to %s ..." % (obj.name, new_name))
        task = obj.Rename(new_name)
        self.wait_for_tasks([task])

    # ================== Get VM ==================
    @staticmethod
    def print_vm(vm):
        details = {'name': vm.summary.config.name,
                   'instance UUID': vm.summary.config.instanceUuid,
                   'bios UUID': vm.summary.config.uuid,
                   'path to VM': vm.summary.config.vmPathName,
                   'guest OS id': vm.summary.config.guestId,
                   'guest OS name': vm.summary.config.guestFullName,
                   'host name': vm.runtime.host.name,
                   'last booted timestamp': vm.runtime.bootTime,
                   }

        for name, value in details.items():
            print("{0:{width}{base}}: {1}".format(name, value, width=25,
                                                  base='s'))

    @staticmethod
    def print_vm_plus(vm):
        """
        Print information for a particular virtual machine or recurse into a
        folder with depth protection
        """
        summary = vm.summary
        print("Name       : ", summary.config.name)
        print("Template   : ", summary.config.template)
        print("Path       : ", summary.config.vmPathName)
        print("Guest      : ", summary.config.guestFullName)
        print("Instance UUID : ", summary.config.instanceUuid)
        print("Bios UUID     : ", summary.config.uuid)
        annotation = summary.config.annotation
        if annotation:
            print("Annotation : ", annotation)
        print("State      : ", summary.runtime.powerState)
        if summary.guest is not None:
            ip_address = summary.guest.ipAddress
            tools_version = summary.guest.toolsStatus
            if tools_version is not None:
                print("VMware-tools: ", tools_version)
            else:
                print("Vmware-tools: None")
            if ip_address:
                print("IP         : ", ip_address)
            else:
                print("IP         : None")
        if summary.runtime.question is not None:
            print("Question  : ", summary.runtime.question.text)
        print("")

    def get_vm_by_uuid(self, uuid):
        """
        Get VM info see:
        http://pubs.vmware.com/vsphere-55/topic/com.vmware.wssdk.apiref.doc/vim.ServiceInstanceContent.html
        http://pubs.vmware.com/vsphere-55/topic/com.vmware.wssdk.apiref.doc/vim.SearchIndex.html
        :param uuid:
        :return:
        """
        search_index = self.si.content.searchIndex
        vm = search_index.FindByUuid(None, uuid, True, True)

        if vm is None:
            raise Exception("Could not find virtual machine '{0}'".format(uuid))

        return vm

    def get_vm_by_ip(self, ip):
        search_index = self.content.searchIndex
        vm = search_index.FindByIp(None, ip, True)

        if vm is None:
            raise Exception("Could not find virtual machine '{0}'".format(ip))

        return vm

    def get_vm_by_dnsname(self, dnsname):
        search_index = self.si.content.searchIndex
        vm = search_index.FindByDnsName(None, dnsname, True)

        if vm is None:
            raise Exception("Could not find virtual machine '{0}'".format(dnsname))

        return vm

    def get_vm_by_name(self, name):
        """
        get vm object by name
        :param name:
        :return:
        """
        for child in self.content.rootFolder.childEntity:
            vm = self.content.searchIndex.FindChild(child.vmFolder, name)
            if vm is not None:
                return vm
        else:
            raise Exception("Could not find virtual machine '{0}'".format(name))

    def get_vm_by_name_filter(self, name_filter):
        """
        get vm object by name_filter, re support
        Note: take a long time
        :param name_filter: regular expression for name
        :return:
        """
        vm_list = []
        container = self.content.rootFolder  # starting point to look into
        view_type = [vim.VirtualMachine]  # object types to look for
        recursive = True  # whether we should look into it recursively
        container_view = self.content.viewManager.CreateContainerView(
            container, view_type, recursive)

        children = container_view.view
        pattern = re.compile(name_filter, re.IGNORECASE) \
            if name_filter is not None else None
        for child in children:
            if name_filter is None:
                # self.print_vm_plus(child)
                vm_list.append(child)
            else:
                if pattern.search(child.summary.config.name) is not None:
                    # self.print_vm_plus(child)
                    vm_list.append(child)
        if not vm_list:
            raise Exception("Could not find virtual machine by "
                            "filter '{0}'".format(name_filter))
        return vm_list

    def is_vm_exist(self, name):
        for child in self.content.rootFolder.childEntity:
            try:
                vm_folder = child.vmFolder
            except Exception as e:
                logger.warning(e)
                vm_folder = child
            # vm_folder = child.vmFolder
            vm = self.content.searchIndex.FindChild(vm_folder, name)
            if vm is not None:
                return True
        return False

    def get_vm_location_dc(self, vm):
        for dc in self.dc_objects:
            if self.content.searchIndex.FindChild(dc.vmFolder, vm.name):
                return dc.name
        logger.warning("Could not find vm <%s> in all datacenters!" % vm.name)
        return None

    def get_vm_location_cluster(self, vm):
        for cluster in self.cluster_objects:
            for host in cluster.host:
                if vm in host.vm:
                    return cluster.name
        logger.warning("Could not find vm <%s> in all cluster!" % vm.name)
        return None

    @staticmethod
    def get_vm_name(vm):
        return vm.name

    @staticmethod
    def get_vm_host_name(vm):
        return vm.guest.hostName

    @staticmethod
    def get_vm_ip(vm):
        return vm.guest.ipAddress

    @staticmethod
    def get_vm_memory(vm):
        return vm.config.hardware.memoryMB

    @staticmethod
    def get_vm_cpu(vm):
        return vm.config.hardware.numCPU

    @staticmethod
    def get_vm_disks(vm):
        """
        Internal method to collect template disks
        :param vm: VM object
        :return: list of vm disks
        """
        vm_disks = []
        for device in vm.config.hardware.device:
            if type(device).__name__ == "vim.vm.device.VirtualDisk":
                datastore = device.backing.datastore
                print("device.deviceInfo.summary:" + device.deviceInfo.summary)
                print("datastore.summary.type:" + datastore.summary.type)
                if hasattr(device.backing, 'fileName'):
                    disk_desc = str(device.backing.fileName)
                    print("Disc Discription -- {}".format(disk_desc))
                    drive = disk_desc.split("]")[0].replace("[", "")
                    print("drive:" + drive)
                    print("device.backing.fileName:" + device.backing.fileName)
                    vm_disks.append(device)
        return vm_disks

    # ================== Power OPS VM ==================
    @staticmethod
    def check_vm_power_state(vm, expected_state='poweredOn'):
        power_state = vm.runtime.powerState
        if vm.runtime.powerState != expected_state:
            raise Exception('powerState(runtime/expected):{0}/{1}'.format(
                power_state, expected_state))
        logger.info('powerState(runtime/expected):{0}/{1}'.format(
            power_state, expected_state))
        return True

    @retry(tries=120, delay=10)
    def wait_vm_poweroff(self, vm):
        self.check_vm_power_state(vm, expected_state='poweredOff')

    def suspend_vm(self, vm):
        if vm.runtime.powerState == 'poweredOff':
            raise Exception('{0} state can not be suspend.'.format(
                vm.runtime.powerState))

        if vm.runtime.powerState == 'suspended':
            logger.info('Suspend {0} success'.format(vm.name))
            return True

        task = vm.SuspendVM_Task()

        try:
            task_state = WaitForTask(task)
        except Exception as e:
            raise Exception('Suspend {0} failed\n{1}'.format(vm.name, e))
        else:
            if task_state != vim.TaskInfo.State.success:
                raise Exception('Suspend {0} failed'.format(vm.name))
            self.check_vm_power_state(vm, 'suspended')
            return True

    def poweroff_vm(self, vm):
        if vm.runtime.powerState == 'poweredOff':
            logger.info('Power off {0} success'.format(vm.name))
            return True

        task = vm.PowerOffVM_Task()

        try:
            task_state = WaitForTask(task)
        except Exception as e:
            raise Exception('Power off {0} failed\n{1}'.format(vm.name, e))
        else:
            if task_state != vim.TaskInfo.State.success:
                raise Exception('Power off {0} failed'.format(vm.name))
            self.check_vm_power_state(vm, 'poweredOff')
            return True

    def shutdown_vm(self, vm):
        if vm.runtime.powerState == 'poweredOff':
            logger.info('Shutdown {0} success'.format(vm.name))
            return True

        vm.ShutdownGuest()

        try:
            self.wait_vm_poweroff(vm)
        except Exception as e:
            raise e
        else:
            logger.info('Shutdown {0} success'.format(vm.name))

    def poweron_vm(self, vm):
        if vm.runtime.powerState == 'poweredOn':
            logger.info('Power on {0} success'.format(vm.name))
            return True

        task = vm.PowerOnVM_Task()

        try:
            task_state = WaitForTask(task)
        except Exception as e:
            raise Exception('Power on {0} failed\n{1}'.format(vm.name, e))
        else:
            if task_state != vim.TaskInfo.State.success:
                raise Exception('Power off {0} failed'.format(vm.name))
            self.check_vm_power_state(vm, 'poweredOn')
            return True

    def reset_vm(self, vm):
        if vm.runtime.powerState in['poweredOff', 'suspended']:
            raise Exception('State {0} can not be reset.'.format(
                vm.runtime.powerState))

        task = vm.ResetVM_Task()

        try:
            task_state = WaitForTask(task)
        except Exception as e:
            raise Exception('Reset {0} failed\n{1}'.format(vm.name, e))
        else:
            if task_state != vim.TaskInfo.State.success:
                raise Exception('Reset {0} failed'.format(vm.name))
            util.sleep_progressbar(5)
            self.check_vm_power_state(vm, 'poweredOn')
            return True

    def reboot_vm(self, vm):
        if vm.runtime.powerState in ['poweredOff', 'suspended']:
            raise Exception('State {0} can not be reboot.'.format(
                    vm.runtime.powerState))

        vm.RebootGuest()
        util.sleep_progressbar(15)
        self.check_vm_power_state(vm, 'poweredOn')

    def destroy_vm(self, vm):
        vm_name = vm.name
        if vm.runtime.powerState in ['poweredOn', 'suspended']:
            logger.info('power off vm before destroy ...')
            self.poweroff_vm(vm)

        task = vm.Destroy_Task()

        try:
            task_state = WaitForTask(task)
        except Exception as e:
            raise Exception('Destroy vm {0} fail!\n{1}'.format(vm_name, e))
        else:
            if task_state != vim.TaskInfo.State.success:
                raise Exception('Destroy vm {0} failed'.format(vm_name))
            logger.info('Destroy vm {0} failed'.format(vm_name))
            return True

    def power_ops(self, vm, ops):
        support_power_opt = [
            'poweroff',
            'shutdown',
            'poweron',
            'suspend',
            'reset',
            'reboot',
            'standby'
        ]
        power_opt = {
            "poweroff": self.poweroff_vm,
            "shutdown": self.shutdown_vm,
            "poweron": self.poweron_vm,
            "reboot": self.reboot_vm,
            "reset": self.reset_vm,
            "suspend": self.suspend_vm
        }

        try:
            return power_opt[ops](vm)
        except Exception as e:
            raise Exception('Support power operate:{0}\n{1}'.format(
                support_power_opt, e))

    def multi_power_ops(self, vm_ops_dict):
        """
        multi power operate VMs, support power operate, choice in
            [
                'poweroff',
                'shutdown',
                'poweron',
                'suspend',
                'reset',
                'reboot',
                'standby'
            ]
        :param vm_ops_dict: {vm1:ops1, vms2:ops2} type:(vm: obj, ops:str)
        :return:
        """
        pool = ThreadPoolExecutor(max_workers=8)
        futures = []
        for vm, ops in vm_ops_dict.items():
            futures.append(pool.submit(self.power_ops, vm, ops))
        pool.shutdown()
        future_results = [future.result() for future in as_completed(futures)]

        return all(future_results)

    def multi_power_ip_ops_dict(self, ip_ops_dict):
        """
        multi power operate VMs, support power operate, choice in
            [
                'poweroff',
                'shutdown',
                'poweron',
                'suspend',
                'reset',
                'reboot',
                'standby'
            ]
        :param ip_ops_dict: {ip1:ops1, ip2:ops2}
        :return:
        """
        pool = ThreadPoolExecutor(max_workers=8)
        futures = []
        for ip, ops in ip_ops_dict.items():
            vm = self.get_vm_by_ip(ip)
            futures.append(pool.submit(self.power_ops, vm, ops))
        pool.shutdown()
        future_results = [future.result() for future in as_completed(futures)]

        return all(future_results)

    def multi_power_name_ops_dict(self, name_ops_dict):
        """
        multi power operate VMs, support power operate, choice in
            [
                'poweroff',
                'shutdown',
                'poweron',
                'suspend',
                'reset',
                'reboot',
                'standby'
            ]
        :param name_ops_dict: {name1:ops1, name2:ops2}
        :return:
        """
        pool = ThreadPoolExecutor(max_workers=8)
        futures = []
        for name, ops in name_ops_dict.items():
            vm = self.get_vm_by_name(name)
            futures.append(pool.submit(self.power_ops, vm, ops))
        pool.shutdown()
        future_results = [future.result() for future in as_completed(futures)]

        return all(future_results)

    def multi_power_ips_ops(self, ip_list, ops='poweron'):
        """
        multi power operate VMs, support power operate, choice in
            [
                'poweroff',
                'shutdown',
                'poweron',
                'suspend',
                'reset',
                'reboot',
                'standby'
            ]
        :param ip_list: vms ip list
        :param ops: string of operate
        :return:
        """
        pool = ThreadPoolExecutor(max_workers=8)
        futures = []
        for ip in ip_list:
            vm = self.get_vm_by_ip(ip)
            futures.append(pool.submit(self.power_ops, vm, ops))
        pool.shutdown()
        future_results = [future.result() for future in as_completed(futures)]

        return all(future_results)

    def multi_power_names_ops(self, name_list, ops='poweron'):
        """
        multi power operate VMs, support power operate, choice in
            [
                'poweroff',
                'shutdown',
                'poweron',
                'suspend',
                'reset',
                'reboot',
                'standby'
            ]
        :param name_list: vms name list
        :param ops: string of operate
        :return:
        """
        pool = ThreadPoolExecutor(max_workers=8)
        futures = []
        for name in name_list:
            vm = self.get_vm_by_name(name)
            futures.append(pool.submit(self.power_ops, vm, ops))
        pool.shutdown()
        future_results = [future.result() for future in as_completed(futures)]

        return all(future_results)

    def multi_destroy_vms(self, vm_list):
        """
        multi destroy VMs
        :param vm_list: vm object list
        :return:
        """
        pool = ThreadPoolExecutor(max_workers=8)
        futures = []
        for vm in vm_list:
            futures.append(pool.submit(self.destroy_vm, vm))
        pool.shutdown()
        future_results = [future.result() for future in as_completed(futures)]

        return all(future_results)

    def get_vm_snapshots_by_name(self, vm, snap_name, show=False):
        snap_list = []
        for snapshot in vm.snapshot.rootSnapshotList:
            if snapshot.name == snap_name:
                snap_text = "Name: %s; Description: %s; CreateTime: %s; " \
                            "State: %s" % (snapshot.name, snapshot.description,
                                           snapshot.createTime, snapshot.state)
                if show:
                    logger.info(snap_text)
                snap_list.append(snapshot)
            else:
                snap_list = snap_list + self.get_vm_snapshots_by_name(
                    snapshot.childSnapshotList, snap_name)
        return snap_list

    def list_vm_snapshots(self, vm):
        snapshot_data = []
        for snapshot in vm.snapshot.rootSnapshotList:
            snap_text = "Name: %s; Description: %s; CreateTime: %s; State: %s" % (
                snapshot.name, snapshot.description,
                snapshot.createTime, snapshot.state)
            snapshot_data.append(snap_text)
            snapshot_data = snapshot_data + self.list_vm_snapshots(
                snapshot.childSnapshotList)
        return snapshot_data

    def create_vm_snapshot(self, vm, snap_name, snap_desc, memory=False):
        task = vm.CreateSnapshot_Task(name=snap_name,
                                      description=snap_desc,
                                      memory=memory,
                                      quiesce=False)
        self.wait_for_tasks([task])
        logger.info("Snapshot Completed.")
        vm_ip = self.get_vm_ip(vm)
        vm = self.get_vm_by_ip(vm_ip)
        snap_info = vm.snapshot
        tree = snap_info.rootSnapshotList
        while tree[0].childSnapshotList is not None:
            logger.info("Snap: {0} => {1}".format(
                tree[0].name, tree[0].description))
            if len(tree[0].childSnapshotList) < 1:
                break
            tree = tree[0].childSnapshotList
        return True

    def remove_vm_snapshot(self, vm, snap_name):
        snap_list = self.get_vm_snapshots_by_name(vm, snap_name, show=True)
        for snap in snap_list:
            print("Removing snapshot %s" % snap_name)
            WaitForTask(snap.RemoveSnapshot_Task(True))

        return True

    def remove_vm_all_snapshots(self, vm):
        snapshot_paths = self.list_vm_snapshots(vm)
        for snapshot in snapshot_paths:
            print(snapshot)
        print("Removing all snapshots for virtual machine %s" % vm.name)
        WaitForTask(vm.RemoveAllSnapshots())

        return True

    def revert_vm_snapshot(self, vm, snap_name):
        snap_list = self.get_vm_snapshots_by_name(vm, snap_name, show=True)
        for snap in snap_list:
            print("Reverting to snapshot %s" % snap_name)
            WaitForTask(snap.RevertToSnapshot_Task())

        return True

    # ================== Set VM ==================
    def add_nic(self, vm, network_name):
        """
        add nic to vm
        :param vm: Virtual Machine Object
        :param network_name: Name of the Virtual Network
        """
        spec = vim.vm.ConfigSpec()
        nic_changes = []

        nic_spec = vim.vm.device.VirtualDeviceSpec()
        nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add

        nic_spec.device = vim.vm.device.VirtualE1000()

        nic_spec.device.deviceInfo = vim.Description()
        nic_spec.device.deviceInfo.summary = 'vCenter API test'

        network = self.get_obj([vim.Network], network_name)
        if isinstance(network, vim.OpaqueNetwork):
            nic_spec.device.backing = \
                vim.vm.device.VirtualEthernetCard.OpaqueNetworkBackingInfo()
            nic_spec.device.backing.opaqueNetworkType = \
                network.summary.opaqueNetworkType
            nic_spec.device.backing.opaqueNetworkId = \
                network.summary.opaqueNetworkId
        else:
            nic_spec.device.backing = \
                vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
            nic_spec.device.backing.useAutoDetect = False
            nic_spec.device.backing.deviceName = network

        nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nic_spec.device.connectable.startConnected = True
        nic_spec.device.connectable.allowGuestControl = True
        nic_spec.device.connectable.connected = False
        nic_spec.device.connectable.status = 'untried'
        nic_spec.device.wakeOnLanEnabled = True
        nic_spec.device.addressType = 'assigned'

        nic_changes.append(nic_spec)
        spec.deviceChange = nic_changes
        task_state = vm.ReconfigVM_Task(spec=spec)
        logger.info("NIC CARD ADDED, rc={0}".format(task_state))

    def del_nic(self, vm, nic_number):
        """
        Deletes virtual NIC based on nic number
        :param vm: Virtual Machine Object
        :param nic_number: Unit Number
        :return: True if success
        """
        nic_prefix_label = 'Network adapter '
        nic_label = nic_prefix_label + str(nic_number)
        virtual_nic_device = None
        for dev in vm.config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualEthernetCard) \
                    and dev.deviceInfo.label == nic_label:
                virtual_nic_device = dev

        if not virtual_nic_device:
            raise RuntimeError('Virtual {} could not be found.'.format(nic_label))

        virtual_nic_spec = vim.vm.device.VirtualDeviceSpec()
        virtual_nic_spec.operation = \
            vim.vm.device.VirtualDeviceSpec.Operation.remove
        virtual_nic_spec.device = virtual_nic_device

        spec = vim.vm.ConfigSpec()
        spec.deviceChange = [virtual_nic_spec]
        task = vm.ReconfigVM_Task(spec=spec)
        self.wait_for_tasks([task])
        return True

    @staticmethod
    def set_vm_network(vm, ip, subnet, gateway, dns_server, hostname):
        nic_num = 0
        for device in vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualEthernetCard):
                nic_num += 1

        adapter_map_list = []

        adapter_map = vim.vm.customization.AdapterMapping()
        adapter_map.adapter = vim.vm.customization.IPSettings()
        adapter_map.adapter.ip = vim.vm.customization.FixedIp()
        adapter_map.adapter.ip.ipAddress = ip
        adapter_map.adapter.subnetMask = subnet
        adapter_map.adapter.gateway = gateway

        adapter_map_list.append(adapter_map)

        if nic_num == 2:
            ip_num = ip.split('.')
            vm_ip1 = '192.168.{0}.{1}'.format(ip_num[2], ip_num[3])
            adapter_map1 = vim.vm.customization.AdapterMapping()
            adapter_map1.adapter = vim.vm.customization.IPSettings()
            adapter_map1.adapter.ip = vim.vm.customization.FixedIp()
            adapter_map1.adapter.ip.ipAddress = vm_ip1
            adapter_map1.adapter.subnetMask = subnet

            adapter_map_list.append(adapter_map1)

        global_ip = vim.vm.customization.GlobalIPSettings()
        global_ip.dnsServerList = dns_server

        ident = vim.vm.customization.LinuxPrep(
            hostName=vim.vm.customization.FixedName(name=hostname))

        customspec = vim.vm.customization.Specification()
        customspec.nicSettingMap = adapter_map_list
        customspec.globalIPSettings = global_ip
        customspec.identity = ident

        task = vm.Customize(spec=customspec)
        try:
            task_stat = WaitForTask(task)
        except Exception as e:
            raise Exception('Set vm {0} network fail!\n{1}'.format(vm.name, e))
        else:
            if task_stat != vim.TaskInfo.State.success:
                raise Exception('Set vm {0} network fail!'.format(vm.name))
            return True

    @staticmethod
    def update_vm_nic_state(vm, nic_number=1, new_nic_state='connect'):
        """
        update teh virtual nic state. connect|disconnect|delete
        :param vm: Virtual Machine Object
        :param nic_number: Network Interface Controller Number
        :param new_nic_state: Either Connect, Disconnect or Delete.
                              connect|disconnect|delete
        :return: True if success
        """
        nic_prefix_label = 'Network adapter '
        nic_label = nic_prefix_label + str(nic_number)
        virtual_nic_device = None
        for dev in vm.config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualEthernetCard) \
                    and dev.deviceInfo.label == nic_label:
                virtual_nic_device = dev
        if not virtual_nic_device:
            raise RuntimeError('Could not found virtual {}'.format(nic_label))

        virtual_nic_spec = vim.vm.device.VirtualDeviceSpec()
        virtual_nic_spec.operation = \
            vim.vm.device.VirtualDeviceSpec.Operation.remove \
                if new_nic_state == 'delete' \
                else vim.vm.device.VirtualDeviceSpec.Operation.edit
        virtual_nic_spec.device = virtual_nic_device
        virtual_nic_spec.device.key = virtual_nic_device.key
        virtual_nic_spec.device.macAddress = virtual_nic_device.macAddress
        virtual_nic_spec.device.backing = virtual_nic_device.backing
        virtual_nic_spec.device.wakeOnLanEnabled = \
            virtual_nic_device.wakeOnLanEnabled
        connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        if new_nic_state == 'connect':
            connectable.connected = True
            connectable.startConnected = True
        elif new_nic_state == 'disconnect':
            connectable.connected = False
            connectable.startConnected = False
        else:
            connectable = virtual_nic_device.connectable
        virtual_nic_spec.device.connectable = connectable

        device_changes = [virtual_nic_spec]
        spec = vim.vm.ConfigSpec()
        spec.deviceChange = device_changes
        task = vm.ReconfigVM_Task(spec=spec)
        # self.wait_for_tasks([task])

        try:
            task_state = WaitForTask(task)
        except Exception as e:
            raise Exception('FAIL: Set VM {0} network -- {1}\n{2}'.format(vm.name, new_nic_state, e))
        else:
            if task_state != vim.TaskInfo.State.success:
                raise Exception('FAIL: Set VM {0} network -- {1}'.format(vm.name, new_nic_state))
            logger.info('PASS: Set VM {0} network -- {1}'.format(vm.name, new_nic_state))
            return True

    @staticmethod
    def set_vm_cpu(vm, cpu_num, core_num=None):
        if core_num is None:
            core_num = cpu_num

        vm_spec = vim.vm.ConfigSpec()
        vm_spec.numCPUs = cpu_num
        vm_spec.numCoresPerSocket = core_num

        task = vm.ReconfigVM_Task(spec=vm_spec)
        try:
            task_state = WaitForTask(task)
        except Exception as e:
            raise Exception('Set vm {0} cpu fail! {1}'.format(vm.name, e))
        else:
            if task_state != vim.TaskInfo.State.success:
                raise Exception('Set vm {0} cpu fail!'.format(vm.name))
            logger.info('Set vm {0} cpu success'.format(vm.name))
            return True

    @staticmethod
    def set_vm_memory(vm, memory_size):
        vm_spec = vim.vm.ConfigSpec()
        vm_spec.memoryMB = memory_size

        task = vm.ReconfigVM_Task(spec=vm_spec)
        try:
            task_state = WaitForTask(task)
        except Exception as e:
            raise Exception('Set vm {0} memory fail: {1}'.format(vm.name, e))
        else:
            if task_state != vim.TaskInfo.State.success:
                raise Exception('Set vm {0} memory fail!'.format(vm.name))
            logger.info('Set vm {0} memory success'.format(vm.name))
            return True

    def reserve_vm_memory(self, vm, reserve_memory=None):
        vm_spec = vim.vm.ConfigSpec()
        if reserve_memory is None:
            reserve_memory = self.get_vm_memory(vm)
        vm_spec.memoryAllocation = vim.ResourceAllocationInfo(reservation=reserve_memory)

        task = vm.ReconfigVM_Task(spec=vm_spec)
        try:
            task_state = WaitForTask(task)
        except Exception as e:
            raise Exception('Reserve vm {0} memory fail: {1}'.format(vm.name, e))
        else:
            if task_state != vim.TaskInfo.State.success:
                raise Exception('Reserve vm {0} memory fail'.format(vm.name))
            logger.info(('Reserve vm {0} memory success'.format(vm.name)))
            return True

    @staticmethod
    def reserve_vm_cpu(vm, reserve_cpu):
        vm_spec = vim.vm.ConfigSpec()
        vm_spec.cpuAllocation = vim.ResourceAllocationInfo(reservation=reserve_cpu)

        task = vm.ReconfigVM_Task(spec=vm_spec)
        try:
            task_state = WaitForTask(task)
        except Exception as e:
            raise Exception('Reserve vm {0} cpu fail: {1}'.format(vm.name, e))
        else:
            if task_state != vim.TaskInfo.State.success:
                raise Exception('Reserve vm {0} cpu fail'.format(vm.name))
            logger.info(('Reserve vm {0} cpu success'.format(vm.name)))
            return True

    # ================== Clone VM ==================
    def clone_vm(self, template, new_vm_name,
                 linked_clone=False, snapshot_name=None,
                 nic_network=None, datacenter_name=None, vm_folder=None,
                 datastore_name=None, cluster_name=None, resource_pool=None,
                 power_on=False, datastorecluster_name=None):
        """
        Clone a VM from a template/VM
        :param template: Name of the template/VM you are cloning from
        :param new_vm_name: Name of the VM you wish to make
        :param linked_clone: if True, linked clone
        :param snapshot_name: Name of snapshot for linked clone
        :param nic_network: Name of the network to add to the VM
        :param datacenter_name:Name of the Datacenter you wish to use.
        If omitted, the first datacenter will be used
        :param vm_folder: Name of the VMFolder you wish the VM to be dumped in
        :param datastore_name: Datastore you wish the VM to end up on
        :param cluster_name: Name of the cluster you wish the VM to end up on
        :param resource_pool: Resource Pool to use.
        :param power_on: power on the VM after creation
        :param datastorecluster_name: Datastorecluster (DRS Storagepod) you
        wish the VM to end up on

        :return:
        """

        vm_template = self.get_obj([vim.VirtualMachine], template)
        if vm_template is None:
            raise Exception("VM template not found with name:%s" % template)

        # if none git the first one
        datacenter = self.get_obj([vim.Datacenter], datacenter_name)

        if vm_folder:
            destfolder = self.get_obj([vim.Folder], vm_folder)
        else:
            destfolder = datacenter.vmFolder

        if datastore_name:
            datastore = self.get_obj([vim.Datastore], datastore_name)
        else:
            datastore = self.get_obj([vim.Datastore],
                                     vm_template.datastore[0].info.name)

        # if None, get the first one
        cluster = self.get_obj([vim.ClusterComputeResource], cluster_name)

        if resource_pool:
            resource_pool = self.get_obj([vim.ResourcePool], resource_pool)
        else:
            resource_pool = cluster.resourcePool

        vmconf = vim.vm.ConfigSpec()

        if datastorecluster_name:
            podsel = vim.storageDrs.PodSelectionSpec()
            pod = self.get_obj([vim.StoragePod], datastorecluster_name)
            podsel.storagePod = pod

            storagespec = vim.storageDrs.StoragePlacementSpec()
            storagespec.podSelectionSpec = podsel
            storagespec.type = 'create'
            storagespec.folder = destfolder
            storagespec.resourcePool = resource_pool
            storagespec.configSpec = vmconf

            try:
                rec = self.content.storageResourceManager.RecommendDatastores(
                    storageSpec=storagespec)
                rec_action = rec.recommendations[0].action[0]
                real_datastore_name = rec_action.destination.name
            except Exception as e:
                print(e)
                real_datastore_name = vm_template.datastore[0].info.name

            datastore = self.get_obj([vim.Datastore], real_datastore_name)

        # set relospec
        relospec = vim.vm.RelocateSpec()
        relospec.datastore = datastore
        relospec.pool = resource_pool
        if linked_clone:
            relospec.diskMoveType = 'createNewChildDiskBacking'

        clonespec = vim.vm.CloneSpec()
        clonespec.location = relospec
        clonespec.powerOn = power_on
        if linked_clone:
            snap_list = vm_template.snapshot.rootSnapshotList
            if not snap_list:
                raise Exception('None snapshot on VM %s' % vm_template.name)
            if snapshot_name:
                while snap_list[0].childSnapshotList is not None:
                    if snap_list[0].name == snapshot_name:
                        logger.info("Snap: {0} => {1}".format(
                            snap_list[0].name, snap_list[0].description))
                        snap = snap_list[0]
                        break
                    snap_list = snap_list[0].childSnapshotList
                else:
                    raise Exception("Not find snapshot: %s" % snapshot_name)
            else:
                snap = snap_list[0]

            clonespec.template = False
            clonespec.snapshot = snap.snapshot

        logger.info("Cloning VM ...")
        task = vm_template.Clone(folder=destfolder, name=new_vm_name,
                                 spec=clonespec)
        self.wait_for_tasks([task])

        vm = self.get_obj([vim.VirtualMachine], new_vm_name)
        self.add_nic(vm, nic_network)

    def linked_clone_vm(self, template, new_vm_name, snapshot_name=None,
                        nic_network=None, datacenter_name=None, vm_folder=None,
                        datastore_name=None, cluster_name=None,
                        resource_pool=None, power_on=False,
                        datastorecluster_name=None):
        """
        linked clone vm from snapshot
        :param template:
        :param new_vm_name:
        :param snapshot_name:
        :param nic_network:
        :param datacenter_name:
        :param vm_folder:
        :param datastore_name:
        :param cluster_name:
        :param resource_pool:
        :param power_on:
        :param datastorecluster_name:
        :return:
        """

        self.clone_vm(template, new_vm_name, True, snapshot_name,
                      nic_network, datacenter_name, vm_folder,
                      datastore_name, cluster_name, resource_pool,
                      power_on, datastorecluster_name)

    def relocate_vm(self, vm_name, host_dest, datastore_dest=None, **kwargs):
        """
        This method relocates vm to the host_dest across
        datacenters, clusters, datastores managed by a vCenter
        :param vm_name:
        :param host_dest:
        :param datastore_dest:
        :param kwargs:
        :return:
        """

        def construct_locator(src_disks, dest_ds_id):
            """
            Internal method to construct locator for the disks
            :param src_disks:list of source template_disks
            :param dest_ds_id:ID of destination datastore
            :return:list of locator
            """

            ds_disk = []
            for index, wdisk in enumerate(src_disks):
                print("relocate index:" + str(index))
                print("disk:" + str(wdisk))
                disk_desc = str(wdisk.backing.fileName)
                drive = disk_desc.split("]")[0].replace("[", "")
                print("drive:" + drive)
                print("wdisk.backing.fileName:" + wdisk.backing.fileName)
                locator = vim.vm.RelocateSpec.DiskLocator()
                locator.diskBackingInfo = wdisk.backing
                locator.diskId = int(wdisk.key)
                locator.datastore = dest_ds_id
                ds_disk.append(locator)
            return ds_disk

        relocation_status = False
        message = "relocate_vm passed"
        try:
            vm = self.get_obj([vim.VirtualMachine], vm_name)
            current_host = vm.runtime.host.name
            logger.info("vmotion_vm current_host:" + current_host)

            # Create Relocate Spec
            spec = vim.VirtualMachineRelocateSpec()

            # Check whether compute vmotion required and construct spec accordingly
            if host_dest is not None:
                if current_host == host_dest:
                    raise Exception("WARNING:: destination_host can not equal "
                                    "current_host")

                # Find destination host
                destination_host = self.get_obj([vim.HostSystem], host_dest)
                print("vmotion_vm destination_host:" + str(destination_host))
                spec.host = destination_host

                # Find destination Resource pool
                resource_pool = destination_host.parent.resourcePool
                print("vmotion_vm resource_pool:" + str(resource_pool))
                spec.pool = resource_pool

            # Check whether storage vmotion required and construct spec accordingly
            if datastore_dest is not None:
                # collect disks belong to the VM
                template_disks = self.get_vm_disks(vm)
                datastore_dest_id = self.get_obj([vim.Datastore], datastore_dest)
                spec.datastore = datastore_dest_id
                spec.disk = construct_locator(template_disks, datastore_dest_id)

            logger.info("relocate_vm spec:" + str(spec))
            task = vm.RelocateVM_Task(spec)
            while task.info.state == vim.TaskInfo.State.running:
                continue
            relocation_status = True
        except Exception as e:
            message = "relocate_vm failed for vm:" + vm_name \
                      + " with error:" + str(e)
        print(message)
        return relocation_status, message

    # ================== Get/Set ESXi ==================
    def get_esxi(self, esxi_host):
        esxi_view = self.content.viewManager.CreateContainerView(
            self.content.rootFolder, [vim.HostSystem], True)
        for esxi in esxi_view.view:
            if esxi.name == esxi_host:
                return esxi
        else:
            raise Exception('Cannot find esxi host: %s' % esxi_host)

    def get_esxi_location(self, esxi_host):
        """
        get the specified esxi host location: datacenter_name, cluster_name
        :param esxi_host:
        :return:
        """
        datacenter_name, cluster_name = '', ''
        datacenters = self.content.rootFolder.childEntity
        for dc in datacenters:
            datacenter_name = dc.name
            clusters = dc.hostFolder.childEntity
            for cluster in clusters:
                cluster_name = cluster.name
                hosts = cluster.host
                host_ips = [host.name for host in hosts]
                if esxi_host in host_ips:
                    return datacenter_name, cluster_name
        return datacenter_name, cluster_name

    # ===== Resource: dc/cluster/resource pool/datastore =====
    def create_datacenter(self, dc_name=None, folder=None):
        """
        Creates a new datacenter with the given name.
        Any % (percent) character used in this name parameter must be escaped,
        unless it is used to start an escape sequence. Clients may also escape
        any other characters in this name parameter.

        An entity name must be a non-empty string of
        less than 80 characters. The slash (/), backslash (\) and percent (%)
        will be escaped using the URL syntax. For example, %2F

        This can raise the following exceptions:
        vim.fault.DuplicateName
        vim.fault.InvalidName
        vmodl.fault.NotSupported
        vmodl.fault.RuntimeFault
        ValueError raised if the name len is > 79
        https://github.com/vmware/pyvmomi/blob/master/docs/vim/Folder.rst

        Required Privileges
        Datacenter.Create

        :param folder: Folder object to create DC in. If None it will default to
                       rootFolder
        :param dc_name: Name for the new datacenter.
        :return:
        """
        if len(dc_name) > 79:
            raise ValueError("The name of the datacenter must be under "
                             "80 characters.")
        if folder is None:
            folder = self.si.content.rootFolder

        if folder is not None and isinstance(folder, vim.Folder):
            dc_moref = folder.CreateDatacenter(name=dc_name)
            return dc_moref

    @staticmethod
    def create_cluster(datacenter, cluster_name, cluster_spec=None):
        """
        Method to create a Cluster in vCenter

        :param datacenter:
        :param cluster_name:
        :param cluster_spec:
        :return: Cluster MORef
        """

        if cluster_name is None:
            raise ValueError("Missing value for name.")
        if datacenter is None:
            raise ValueError("Missing value for datacenter.")
        if cluster_spec is None:
            cluster_spec = vim.cluster.ConfigSpecEx()

        host_folder = datacenter.hostFolder
        cluster = host_folder.CreateClusterEx(name=cluster_name,
                                              spec=cluster_spec)
        return cluster

    @property
    def dc_objects(self):
        dc_view = self.content.viewManager.CreateContainerView(
            self.content.rootFolder, [vim.Datacenter], True)
        return dc_view.view

    @property
    def cluster_objects(self):
        cluster_view = self.content.viewManager.CreateContainerView(
            self.content.rootFolder, [vim.ClusterComputeResource], True)
        return cluster_view.view

    def get_dc(self, dc_name):
        """
        Get a datacenter by its name.
        :param dc_name: datacenter name
        :return:
        """
        for dc in self.si.content.rootFolder.childEntity:
            if dc.name == dc_name:
                return dc
        raise Exception('Failed to find datacenter named %s' % dc_name)

    def get_rp(self, rp_name, dc):
        """
        Get a resource pool in the datacenter by its names.
        :param rp_name: resource pool name
        :param dc: datacenter object
        :return:
        """
        view_manager = self.si.content.viewManager
        container_view = view_manager.CreateContainerView(dc, [vim.ResourcePool], True)
        try:
            for rp in container_view.view:
                if rp.name == rp_name:
                    return rp
        finally:
            container_view.Destroy()
        raise Exception("Failed to find resource pool %s in dc/cluster %s" %
                        (rp_name, dc.name))

    def get_rp_in_cluster(self, rp_name, cluster):
        """
        Get a resource pool in the cluster by its names.
        :param rp_name:resource pool name
        :param cluster: cluster object
        :return:
        """
        self.get_rp(cluster, rp_name)

    def get_rp_largest_free(self, dc):
        """
        Get the resource pool with the largest unreserved memory for VMs.
        :param dc: datacenter object
        :return: resource pool object
        """
        view_manager = self.si.content.viewManager
        container_view = view_manager.CreateContainerView(dc, [vim.ResourcePool], True)
        largest_rp = None
        unreserved_for_vm = 0
        try:
            for rp in container_view.view:
                if rp.runtime.memory.unreservedForVm > unreserved_for_vm:
                    largest_rp = rp
                    unreserved_for_vm = rp.runtime.memory.unreservedForVm
        finally:
            container_view.Destroy()
        if largest_rp is None:
            raise Exception("Failed to find a resource pool in dc %s" % dc.name)
        return largest_rp

    @staticmethod
    def get_ds(ds_name, dc):
        """
        Pick a datastore by its name.
        :param ds_name: datastore name
        :param dc: dc object
        :return:
        """
        for ds in dc.datastore:
            try:
                if ds.name == ds_name:
                    return ds
            except Exception as e:  # Ignore datastores that have issues
                logger.warning('Ignore datastores that have issues\n%s' % e)
                pass
        raise Exception("Failed to find %s on dc %s" % (ds_name, dc.name))

    @staticmethod
    def get_ds_largest_free(dc):
        """
        Pick the datastore that is accessible with the largest free space.
        :param dc: dc object
        :return:
        """
        largest = None
        largest_free = 0
        for ds in dc.datastore:
            try:
                free_space = ds.summary.freeSpace
                if free_space > largest_free and ds.summary.accessible:
                    largest_free = free_space
                    largest = ds
            except Exception as e:  # Ignore datastores that have issues
                logger.warning('Ignore datastores that have issues\n%s' % e)
                pass
        if largest is None:
            raise Exception('Failed to find any free datastores on %s' % dc.name)
        return largest

    def get_ds_filter(self, esxi_host, ds_type, min_size=100*1024*1024*1024):
        ds_list = []
        view_obj = self.content.viewManager.CreateContainerView(
            self.content.rootFolder, [vim.Datastore], True)
        all_ds_list = view_obj.view
        for ds in all_ds_list:
            for host in ds.host:
                if host.key == self.get_esxi(esxi_host):
                    ds_list.append(ds)

        match_ds_list = []
        for ds in ds_list:
            if not ds.summary.accessible:
                logger.debug('{ds} is not accessible, ignore.'.format(ds=ds.name))
                continue
            if ds.summary.type != 'VMFS':
                logger.debug('{ds} is not VMFS type, ignore.'.format(ds=ds.name))
                continue

            try:
                ssd_enable = ds.info.vmfs.ssd
            except Exception as e:
                print(e)
                ssd_enable = False

            if ssd_enable:
                if ds_type != 'SSD':
                    logger.warning('{ds} is SSD, ignore.'.format(ds=ds.name))
                    continue
            else:
                if ds_type == 'SSD':
                    logger.warning('{ds} is not SSD, ignore.'.format(ds=ds.name))
                    continue
            try:
                free_space = ds.summary.freeSpace
                if free_space >= min_size:
                    match_ds_list.append(ds)
            except Exception as e:
                logger.warning('Failed get free ds: {0}. Ignore'.format(e))
        return match_ds_list

    # ================== Deploy ==================
    def get_deployment_objects(self, datacenter_name, datastore_name,
                               cluster_name=None, resource_pool=None):
        """
        Return a dict containing the necessary objects for deployment.
        """
        # Get datacenter object.
        datacenter_list = self.content.rootFolder.childEntity
        if datacenter_name:
            datacenter_obj = self.get_obj_in_list(datacenter_name, datacenter_list)
        else:
            datacenter_obj = datacenter_list[0]

        # Get datastore object.
        datastore_list = datacenter_obj.datastoreFolder.childEntity
        if datastore_name:
            datastore_obj = self.get_obj_in_list(datastore_name, datastore_list)
        elif len(datastore_list) > 0:
            datastore_obj = datastore_list[0]
        else:
            raise Exception("No datastores found in DC (%s)." % datacenter_obj.name)

        # Get cluster object.
        cluster_list = datacenter_obj.hostFolder.childEntity
        if cluster_name:
            cluster_obj = self.get_obj_in_list(cluster_name, cluster_list)
        elif len(cluster_list) > 0:
            cluster_obj = cluster_list[0]
        else:
            raise Exception("No clusters found in DC: %s" % datacenter_obj.name)

        # Generate resource pool.
        # resource_pool_obj = cluster_obj.resourcePool
        view_manager = self.si.content.viewManager
        container_view = view_manager.CreateContainerView(cluster_obj,
                                                          [vim.ResourcePool],
                                                          True)
        try:
            for rp in container_view.view:
                if rp.name == resource_pool:
                    resource_pool_obj = rp
                    break
            else:
                raise Exception("Failed to find resource pool %s in cluster %s"
                                % (resource_pool, cluster_obj.name))
        finally:
            container_view.Destroy()

        deployment_objects = {
            "datacenter": datacenter_obj,
            "datastore": datastore_obj,
            "resource pool": resource_pool_obj
        }

        return deployment_objects

    def deploy_ovf(self, ovf_path, vmdk_path, datacenter_name, datastore_name,
                   cluster_name):

        def get_ovf_descriptor(ovf_path):
            """
            Read in the OVF descriptor from *.ovf
            """
            if os.path.exists(ovf_path):
                with open(ovf_path, 'r') as f:
                    try:
                        ovfd = f.read()
                        f.close()
                        return ovfd
                    except:
                        raise Exception("Could not read file: %s" % ovf_path)
            else:
                raise Exception("ovf file not exists: %s" % ovf_path)

        def keep_lease_alive(lease):
            """
            Keeps the lease alive while POSTing the VMDK.
            """
            while True:
                time.sleep(5)
                try:
                    # Choosing arbitrary percentage to keep the lease alive.
                    lease.HttpNfcLeaseProgress(50)
                    if lease.state == vim.HttpNfcLease.State.done:
                        return
                    # If the lease is released, we get an exception.
                    # Returning to kill the thread.
                except:
                    return

        ovfd = get_ovf_descriptor(ovf_path)
        objs = self.get_deployment_objects(datacenter_name, datastore_name, cluster_name)
        manager = self.si.content.ovfManager
        spec_params = vim.OvfManager.CreateImportSpecParams()
        import_spec = manager.CreateImportSpec(ovfd,
                                               objs["resource pool"],
                                               objs["datastore"],
                                               spec_params)
        lease = objs["resource pool"].ImportVApp(import_spec.importSpec,
                                                 objs["datacenter"].vmFolder)
        while True:
            if lease.state == vim.HttpNfcLease.State.ready:
                # Assuming single VMDK.
                url = lease.info.deviceUrl[0].url.replace('*', self.host)
                # Spawn a dawmon thread to keep the lease active while POSTing VMDK.
                keepalive_thread = Thread(target=keep_lease_alive,
                                          args=(lease,))
                keepalive_thread.start()
                # POST the VMDK to the host via curl.
                # Requests library would work too.
                curl_cmd = (
                        "curl -Ss -X POST --insecure -T %s -H 'Content-Type: \
                        application/x-vnd.vmware-streamVmdk' %s" %
                        (vmdk_path, url))
                os.system(curl_cmd)
                lease.HttpNfcLeaseComplete()
                keepalive_thread.join()
                return True
            elif lease.state == vim.HttpNfcLease.State.error:
                raise Exception("Lease error: " + lease.state.error)
            else:
                logger.warning(lease.state)


class VsphereApiTestCase(unittest.TestCase):
    """Test cases for VsphereApi"""

    def setUp(self) -> None:
        self.vsp_api = VsphereApi('10.25.1.8', 'txu@panzura.com', 'pass@0612')

    def tearDown(self) -> None:
        pass

    def test_1(self):
        print(self.vsp_api.get_deployment_objects('VIZION', '10.25.0.56-SSD-1', 'Vizion_Stress', 'txu'))

    def test_get_vm_by_uuid(self):
        vm = self.vsp_api.get_vm_by_uuid('503ab6f6-d125-69bf-6a97-507948fa230a')
        self.vsp_api.print_vm(vm)

    def test_get_vm_by_ip(self):
        vm = self.vsp_api.get_vm_by_ip('10.25.119.71')
        self.vsp_api.print_vm(vm)

    def test_get_vm_by_dnsname(self):
        vm = self.vsp_api.get_vm_by_dnsname('node1')
        self.vsp_api.print_vm(vm)

    def test_get_vm_by_name(self):
        # Ran test in 9.09s
        vm = self.vsp_api.get_vm_by_name('txu-node71')
        self.vsp_api.print_vm(vm)

    def test_get_vm_by_name_filter(self):
        # Ran test in 113.183s
        vm_list = self.vsp_api.get_vm_by_name_filter('txu-node71')
        for vm in vm_list:
            self.vsp_api.print_vm(vm)


if __name__ == "__main__":
    # test
    # unittest.main()
    suite = unittest.TestSuite(
        map(VsphereApiTestCase, ['test_1'])
    )
    # suite = unittest.TestLoader().loadTestsFromTestCase(VsphereApiTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
