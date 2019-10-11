# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/02 12:29
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

""" DosCmd && MacCmd
"""

import os
import re
import time
import inspect
import ctypes
import subprocess
from subprocess import check_output, CalledProcessError
from os.path import expanduser
import threading

from tlib import log
from tlib.retry import retry_call


# =============================
# --- Global
# =============================
logger = log.get_logger()
WINDOWS = os.name == "nt"


class SysWOW64Redirector(object):
    """
    if WINDOWS:
    Reference: http://code.activestate.com/recipes/578035-disable-file-system-redirector/
    This class is needed while executing a 64 bit binary -
    'C:\\Windows\\System32\\dfsutil.exe'. Calling dfsutil (with or without
    absolute path) from from a 32-bit Python is a failure as Windows OS tries
    to search it in 'C:\\Windows\\SysWOW64' where it is not present.
    Note: For such binaries, this class will become redundant when 64 bit
    Python is used.
    """
    _disable = ctypes.windll.kernel32.Wow64DisableWow64FsRedirection
    _revert = ctypes.windll.kernel32.Wow64RevertWow64FsRedirection

    def __enter__(self):
        self.old_value = ctypes.c_long()
        self.success = self._disable(ctypes.byref(self.old_value))

    def __exit__(self, type, value, traceback):
        if self.success:
            self._revert(self.old_value)


class Cmd(object):
    """
    This Class provides generic Command interface, i.e. executes a command
    """

    @staticmethod
    def popen_run(cmd_spec, output=True):
        """
        Executes command and Returns (rc, output) tuple
        :param cmd_spec: Command to be executed
        :param output: collecting STDOUT and STDERR or not?
        :return:
        """

        logger.info('Execute: {cmds}'.format(cmds=' '.join(cmd_spec)))
        try:
            p = subprocess.Popen(cmd_spec, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, shell=True)
            if output:
                (stdout, stderr) = p.communicate()
                rc = p.returncode
                std_out = stdout.decode('UTF-8')
                std_err = stderr.decode('UTF-8')
                std_output = std_out + std_err
            else:
                (rc, std_out_err) = (p.returncode, '')
            logger.info('Output:rc={0},stdout/stderr:\n{1}'.format(rc, std_output))

            return rc, std_output

        except Exception as e:
            raise Exception(e)

    @staticmethod
    def check_output_run(cmd_spec):
        """
        run cmds with subprocess.check_output()
        :param cmd_spec:
        :return:dict(return_info)
        """

        logger.debug('Subprocess.check_output: {cmd}'.format(cmd=cmd_spec))
        rc, std_out, std_err = 0, '', ''

        try:
            result = subprocess.check_output(cmd_spec, stderr=subprocess.STDOUT, shell=True)
            std_out = result.decode('UTF-8')
        except subprocess.CalledProcessError as error:
            std_err = error.output.decode('UTF-8')
            rc = error.returncode
        except Exception as e:
            logger.error('Exception occurred: {err}'.format(err=e))
            rc = -1

        return rc, std_out, std_err

    def run(self, cmd_spec, expected_rc=0, output=True, tries=1, delay=10):
        """
        A generic method for running commands which will raise exception
        if return code of exeuction is not as expected.
        :param cmd_spec:A list of words constituting a command line
        :param expected_rc:An expected value of return code after command
        execution, defaults to 0, If expected RC.upper() is 'IGNORE' then
        exception will not be raised.
        :param output:collecting STDOUT and STDERR or not?
        :param tries:
        :param delay:
        :return:
        """

        # Get name of the calling method, returns <methodName>'
        method_name = inspect.stack()[1][3]
        rc, output = retry_call(self.popen_run,
                                fkwargs={
                                    'cmd_spec': cmd_spec,
                                    'output': output
                                }, tries=tries, delay=delay)

        if isinstance(expected_rc, str) and expected_rc.upper() == 'IGNORE':
            return rc, output

        if rc != expected_rc:
            raise Exception('%s(): Failed command: %s\n'
                            'Mismatched RC: Received [%d], Expected [%d]\n'
                            'Error: %s' % (method_name, ' '. join(cmd_spec),
                                           rc, expected_rc, output))
        return rc, output


class DosCmd(Cmd):
    """
    This class represents Dos Prompt and provides interface to variety of
    DOS commands
    """

    def __init__(self):
        super(DosCmd, self).__init__()
        pass

    @property
    def _volrest(self):
        """
        Installing w2k3 resource kit will be a part of client setup
        This kit provides 'volreset.exe' to do 'Previous Version' operations
        Windows Resource Kits tools download from
        https://www.microsoft.com/en-us/download/details.aspx?id=17657
        _win2k3ResourceKit = r'c:\Program Files (x86)\Windows Resource Kits\Tools'
        :return:
        """

        cur_dir = os.getcwd()
        _win2k3ResourceKit = os.path.join(cur_dir, 'tools', 'WindowsResourceKitsTools')
        return os.path.join(_win2k3ResourceKit, 'volrest.exe')


    @property
    def _wmic(self):
        """
        Using absolute path for 'wmic' to fix "'wmic' is not recognized as an
        internal or external command" error
        :return:
        """
        return r'C:\Windows\System32\wbem\WMIC.exe'

    @property
    def syswow64redirector(self):
        if WINDOWS:
            return SysWOW64Redirector()
        else:
            raise Exception("Not Windows OS!")

    def copy_dir(self, src_path, dst_path):
        """
        Copy(robocopy) files from source path to destination path.
        Create destination directory if it does not exist.
        :param src_path:
        :param dst_path:
        :return:
        """

        cmd = ['robocopy', '/e', '/r:5', src_path, dst_path]
        rc, output = self.run(cmd, expected_rc='ignore')
        logger.info('rc={0}, output:{1}'.format(rc, output))
        '''
        Any value greater than 8 indicates that there was at least one 
        failure during the robocopy operation
        '''
        if rc > 8:
            raise Exception('DosCmd: Command failed!')
        return True

    def set_acl(self, path, user, perm, mode='grant:r'):
        """
        Set ACL on the given file/directory using "icacls" command
        :param path:File/Dir path on which ACL will be set
        :param user:user for whom ACL will be set
        :param perm:Access rights
        :param mode:grant or deny
        :return:Return dos command output if Success
        """

        cmd = ['icacls', path, '/%s' % mode, '%s:%s' % (user, perm)]
        rc, output = self.run(cmd, expected_rc=0)
        return output

    def get_acl(self, path):
        """
        Get file ACL
        :param path:File/Dir path from which to get ACL
        :return: Returns ACL Map .e.g. ['user1':['acl1', 'acl2'], 'user2':..]
        """

        cmd = ['icacls', path]
        (rc, output) = self.run(cmd, expected_rc=0)
        # logger.debug('$ %s\n%s' % (cmd, output))
        if rc != 0 or output is None or len(output) == 0:
            raise Exception('Failed! rc={0}, output:{1}'.format(rc, output))

        acl_map = {}
        for acl_desc in output.split()[1:]:
            if len(acl_desc) == 0:
                continue
            perm = acl_desc.split(':')
            if len(perm) <= 1:
                continue
            if perm[0] not in acl_map.keys():
                acl_map[perm[0]] = []
            acl_map[perm[0]].append(perm[1])

        logger.info('ACL_Map=%s' % acl_map)
        return acl_map

    def remove_acl(self, path, user_name, mode=None):
        """
        Removes ACL from the file/dir represented by path
        :param path:File/Dir path from which to remove ACL
        :param user_name:User Name e.g. domain\\user1
        :param mode:Mode in which perm is set. Value can be 'd' for DENY,
        'g' GRANT or None to remove all ACLs of user_name
        :return:
        """

        mode = '' if mode is None else ':%s' % mode
        cmd = ['icacls', path, '/remove%s' % mode, user_name]
        rc, output = self.run(cmd, expected_rc=0)
        logger.debug(output)
        return output

    def change_inheritance(self, path, op_code='e'):
        """
        Change way ACLs are inherited for a file/dir represented by path
        :param path:File/Dir path for which inheritance of ACL has to be changed
        :param op_code:Supported operation types are: e: enable, d: disable, r: remove
        :return:
        """

        cmd = ['icacls', path, '/inheritance:%s' % op_code]
        rc, output = self.run(cmd, expected_rc=0)
        logger.debug(output)
        return output

    def run_dos_attr(self, path, attr_spec, op):
        """
        Executes 'attrib' command to set/remove attributes on path
        attrSpec can store one or more of the following values, e.g. "RA"
        R - Read-only File
        A - Archive File
        H - Hidden File
        S - System File
        I - Not Content Index File
        :param path:File path to set attribute on
        :param attr_spec:contains one or more of attribute value
        :param op:"+":set, or "-":remove
        :return:
        """

        cmd = ['attrib']
        for attr in attr_spec:
            cmd.append('%s%s' % (op, attr))
        cmd.append(path)
        rc, output = self.run(cmd, expected_rc=0)
        logger.debug(output)
        return output

    def set_dos_attr(self, path, attr_spec):
        """
        Sets given attr on the path as per given input 'attrSpec'
        attrSpec can store one or more of the following values, e.g. "RA"
        R - Read-only File
        A - Archive File
        H - Hidden File
        S - System File
        I - Not Content Index File
        :param path:File path to set attribute on
        :param attr_spec:contains one or more of attribute value
        :return:
        """

        return self.run_dos_attr(path, attr_spec, '+')

    def remove_dos_attr(self, path, attr_spec):
        """
        Clears given attr from the path as per given input 'attrSpec'
        attrSpec can store one or more of the following values, e.g. "RA"
        R - Read-only File
        A - Archive File
        H - Hidden File
        S - System File
        I - Not Content Index File
        :param path:File path to clear attribute on
        :param attr_spec:contains one or more of attribute value
        :return:
        """

        return self.run_dos_attr(path, attr_spec, '-')

    def get_dos_attr(self, path):
        """
        Get attributes
        :param path: File path for which to return attribute
        :return: Returns list of attributes associated with the path
        using 'attrib' command
        """

        cmd = ['attrib', path]
        rc, output = self.run(cmd, expected_rc=0)
        logger.debug(output)

        attr_spec = ''.join(output.split()[:-1])
        return attr_spec

    def set_owner(self, path, owner):
        """
        Changes owner of a file or directory
        :param path:path of a file or directory
        :param owner:value of owner to be set
        :return:
        """

        cmd = ['icacls', path, '/setowner', owner]
        rc, output = self.run(cmd, expected_rc=0)
        logger.debug(output)
        return output

    def get_owner(self, path):
        """
        Get file owner
        :param path:Path of a file object
        :return: Returns a file owner / None
        """

        cmd = ['dir', '/q', path]
        rc, output = self.run(cmd, expected_rc=0)
        logger.debug(output)

        owner = None
        dpath, fname = os.path.split(path)
        # Matches:
        # 04/24/2015  12:26 PM            12,589 BUILTIN\Administrators a.py
        owner_pattern = re.compile(r'^\s*[/0-9]+\s+[:0-9]+\s+(?:A|P)M\s+[,0-9]+\s+(\S+)\s+%s\s*$' % re.escape(fname))

        for line in output.split('\n'):
            m = owner_pattern.match(line)
            if m:
                owner = m.group(1)

        return owner

    def get_previous_versions(self, path, recursive=True):
        """
        Use volrest get a list of previous version associated with the path

        Normally, for a file/folder without any backing snapshot,
        screen-shot of execution is as below:
            VOLREST 1.1 - Previous Version command-line tool
            (C) Copyright 2003 Microsoft Corp.
            No previous versions.
            C:\\Users\\test1>echo %errorlevel%
            0
        Observation is, in this scenario when volrest.exe fails to execute
        with success even if its run multiple times in a loop.Screen-shot
        of execution with return code as 1 is as below:
            (C) Copyright 2003 Microsoft Corp.
            Failed to query shadow copies
            More data is available.
            C:\\Users\\test1>echo %errorlevel%
            1
        And hence, an alternate approach is:
            if rc is not 0; check if output contains
            "Failed to query shadow copies" then return [] (empty list)
            which means 'No previous versions available'
        And this is essentially to fix failure of
        2101_CC-449-3_wpvDeleteAllSnapsNoPV in wpv.txt

        :param path: Target File or directory path for get Previous Versions
        :param recursive: If True, includes '/S' parameter while listing PVs
        :return previousVersions: A list of previous versions with each entry
        in a map of key-value pairs
        """

        cmd = [DosCmd._volrest, '/S', path] if recursive else [DosCmd._volrest, path]

        previous_versions = []
        rc, output = self.run(cmd)
        logger.debug(output)
        if rc != 0:
            search_str = "Failed to query shadow copies"
            for line in output.split('\n'):
                if line.find(search_str) >= 0:
                    logger.info(line)
                    return previous_versions

            raise Exception('DosCmd Failed!rc={0},output:{1}'.format(rc, output))

        # Matches: 12/15/2014  02:28 AM            11,342 P:\@GMT-2014.12.17-08.00.08\wtest1.docx
        #          12/23/2014  08:10 AM     <DIR>         p:\@GMT-2014.12.24-08.00.04\testdir2\sub-folder1
        #          05/30/2015  06:04 AM             1,024 R:\@GMT-2015.05.30-13.04.30\sub - Dir1\Non - Alpha - Num 1_FILE.txt
        pv_entry = r'^\s*([/0-9]+\s+[:0-9]+\s+(?:A|P)M)\s+([,0-9]+|<DIR>)\s+(\S[\s\S]+\S)\s*$'
        # Matches:  Searching previous versions on P:\
        pv_entries_header = r'\s*Searching previous versions on '
        # Matches:               12 File(s)  1,510,432 bytes
        pv_entries_footer = r'\s*[,0-9]+\s+File\(s\)\s+[,0-9]+\s+bytes'
        blank_line = r'^\s*$'  # self-explanatory

        pv_entry_regx = re.compile(pv_entry, re.I)
        pv_entries_header_regx = re.compile(pv_entries_header, re.I)
        pv_entries_footer_regx = re.compile(pv_entries_footer, re.I)
        blank_line_regx = re.compile(blank_line)

        pv_entries_header_flag, pv_entries_footer_flag = False, False

        for line in output.split('\n'):
            if blank_line_regx.match(line):
                continue
            if not pv_entries_header_flag:
                if pv_entries_header_regx.match(line):
                    pv_entries_header_flag = True
                continue
            if not pv_entries_footer_flag:
                if pv_entries_footer_regx.match(line):
                    pv_entries_footer_flag = True
                    break
                if pv_entries_header_flag:
                    m = pv_entry_regx.match(line)
                    if m:
                        previous_versions.append({
                            'pvTime': m.group(1),
                            'pvSize': m.group(2),
                            'pvPath': m.group(3)
                        })

        logger.info('previousVersions=%s' % previous_versions)
        return previous_versions

    def copy_previous_version(self, path, destination, version):
        """
        Uses 'volrest' to copy all Previous Versions associated with the path in destination
        Since, volrest can't restore a specific 'Previous Version' of a path, 'version' argument will not be used.
        :param path:File or directory path of which Previous Versions has to be copied
        :param destination:None (it's a default value and will be unused)
        :param version:
        :return:return code of cmd execution
        """

        if os.path.isdir(destination):
            destination = r'/R:' + destination
            # Option E will include empty directories during restoration
            print(DosCmd()._volrest)
            cmd = [DosCmd()._volrest, '/E', '/S', destination, path]
            rc, output = self.run(cmd, expected_rc=0)
            logger.debug(output)
            return rc
        else:
            raise Exception('DosCmd: Could not copy PVs of [%s] in [%s] as it\'s not a dirpath' % (path, destination))

    def restore_previous_version(self, path, version):
        """
        Uses volrest, to do in-place restore of all previous versions associated with the path
        Note: To do 'in-place restore', restore destination will be dirpath of a file
        Since, volrest can't restore a specific 'Previous Version' of a path, 'version' argument will not be used.
        :param path: File or directory path of which Previous Versions has to be restored
        :param version: None (it's a default value and will be unused.)
        :return: return code of cmd execution
        """
        destination = None
        if os.path.isdir(path):
            destination = path
        else:
            # TODO: Handling of Shortcuts
            destination = os.path.dirname(path)

        return self.copy_previous_version(path, destination, version)

    def kill_proc(self, proc_name):
        """
        Kill the process specified as input.
        :param proc_name: process to be killed
        :return:
        """

        cmd = ['taskkill', '/f', '/im', proc_name]
        rc, output = self.run(cmd, expected_rc=0)
        # logger.info('$ %s\n%s' % (cmd, output))
        return rc

    def create_archive(self, archiver, atype, source, archive):
        """
        Creates an achieve of given 'type' by compressing 'source'
        :param archiver:Application to be used for creating an archive
        :param atype:Type of archive to be created
        :param source:File/Directory to be compressed
        :param archive:Filepath of archive to be created
        :return:
        """

        archive_type = '-t' + atype.lower()
        cmd = [archiver, 'a',  archive_type, archive, source]

        rc, output = self.run(cmd, expected_rc=0)
        # logger.debug('$ %s\n%s' % (' '.join(cmd), output))
        return rc

    def edit_archive(self, archiver, archive, op_code, input):
        """
        Add/Delete/Update file in an existing archive
        :param archiver:Application to be used for creating an archive
        :param archive:Filepath of an archive to be edited in in-line mode
        :param opCode:A entry to be added/updated/deleted in an archive. (Supported values: add|delete)
        :param input:A file/directory to be used for an opCode operation
        :return:
        """

        op_code_cmd_map = {'add': 'a', 'delete': 'd'}
        cmd = [archiver, op_code_cmd_map[op_code], archive, input]

        rc, output = self.run(cmd, expected_rc=0)
        # logger.debug('$ %s\n%s' % (' '.join(cmd), output))
        return rc

    def extract_archive(self, archiver, archive, path):
        """
        Extract an archive into a directory
        :param archiver: Application to be used for creating an archive
        :param archive: Filepath of an archive to be edited in in-line mode
        :param path: Dirpath for extracting files into
        :return:
        """

        epath = '-o' + path
        cmd = [archiver, 'x', archive, epath]

        rc, output = self.run(cmd, expected_rc=0)
        # logger.debug('$ %s\n%s' % (' '.join(cmd), output))
        return rc

    def open_with_app(self, application, path):
        """
        Opens a file at path using application
        :param application:A program to be used for opening a file
        :param path:A file to be opened
        :return:
        """

        cmd = [application, path]
        rc, output = self.run(cmd, output=False)
        # As process started by 'cmd' to open a file is kept running and hence, value of rc is None.
        # So if rc is None; treat it as success by setting it to 0
        rc = 0 if rc is None else rc
        if rc != 0:
            raise Exception('DosCmd: Command failed...\n$ %s\nError %d: %s' % (' ' . join(cmd), rc, output))
        return rc

    def get_network_diagnostics(self, connection):
        """
        Get Network Diagnostics. Diagnostics include nslookup and ping connection output, netstat output
        :param connection: connection name
        :return:
        """

        cmd = ['ping', connection]
        rc, output = self.run(cmd)
        # logger.debug('$ %s\n%s' % (cmd, output))

        cmd = ['nslookup', connection]
        rc, output = self.run(cmd)
        # logger.debug('$ %s\n%s' % (cmd, output))

        cmd = ['netstat', '-rn']
        rc, output = self.run(cmd)
        # logger.debug('$ %s\n%s' % (cmd, output))
        return 0

    def list_mapped_drive(self):
        """
        List mapped drives on the windows client
        :return:
        """

        cmd = ['net', 'use']
        rc, output = self.run(cmd, expected_rc=0)
        return rc, output

    def check_mapped_drive(self, drive):
        """
        Check mapped drive is accessible by listing its contents
        :param drive: drive name
        :return:
        """

        logger.info("drive: %s" % drive)
        cmd = ['dir', drive]
        rc, output = self.run(cmd, expected_rc=0)
        return rc, output

    def get_used_drives(self):
        """
        drives used for mapping resources shared over network
        e.g. After parsing below output, will return ['A:', 'C:', 'D:', 'Q:', 'X:']
            C:\\temp>wmic logicaldisk get name
            A:
            C:
            D:
            Q:
            X:
            C:\temp>
        :return:Returns a list of drives which contains drives like - 'C:' used for system's own resource
        """

        cmd = [DosCmd._wmic, 'logicaldisk', 'get', 'name']
        rc, output = self.run(cmd)
        used_drives = []
        blank_line_regx = re.compile(r'^\s*$')  # self-explanatory
        # Matches: A:
        drive_regex = re.compile(r'^[A-Z]:$')

        for line in output.split('\n'):
            line = line.strip()
            if blank_line_regx.match(line):
                continue
            if drive_regex.match(line):
                used_drives.append(line)

        return used_drives

    def get_mapped_drives(self):
        """
        e.g. After parsing below output, will return ['Q:', 'X:']
            C:\Windows\system32>net use
            New connections will not be remembered.


            Status       Local     Remote                    Network

            -------------------------------------------------------------------------------
            OK           W:        \\10.180.119.66\smb66     Microsoft Windows Network
            Disconnected X:        \\10.1.3.103\qa\Logs\stress
                                                            Microsoft Windows Network
            OK           Y:        \\10.180.119.66\smb65     Microsoft Windows Network
            OK           Z:        \\10.180.119.65\smb65     Microsoft Windows Network
            The command completed successfully.


            C:\Windows\system32>
        """

        cmd = ['net', 'use']
        rc, output = self.run(cmd, expected_rc=0)
        mapped_drives = []

        # To match: -------------------------------------------------------------------------------
        sep_regx = re.compile(r'^-+$')
        # To match:
        #  OK           X:        \\pune1-cc1\smoke         Microsoft Windows Network
        # or to match DFS share where 1st field - 'Status' is blank
        #               Y:        \\pztest28.com\pune1-cc1\smoke
        #                                                   Microsoft Windows Network
        drive_regx = re.compile(r'^(?:\S+\s+)?([A-Z]:)\s+')
        passed_sep = False

        for line in output.split('\n'):
            line = line.strip()
            if passed_sep is False:
                if sep_regx.match(line):
                    passed_sep = True
                continue
            m = drive_regx.match(line)
            if m:
                mapped_drives.append(m.group(1))

        return mapped_drives

    def map_drive(self, cc, drive_name, resource, ad_domain, user_name, user_passwd, retry_max, interval):

        cmd = ['net',  'use', drive_name, resource, user_passwd, '/user:%s\%s' % (ad_domain, user_name)]
        rc, output = self.run(cmd, True, retry_max, interval)

        if rc != 0:
            # cc will be None when mapping a DFS namespace without any direct mapping
            # of CC share; so collection of network diagnotstics is not applicable
            if cc is not None:
                self.get_network_diagnostics(cc)
            raise Exception('MapDrive: Command failed...\n$ %s\nError %d: %s' % (' ' . join(cmd), rc, output))
        return rc

    def unmap_drive(self, drive_name):
        """
        unmap drive
        :param drive_name:eg: z:
        :return:
        """

        cmd = ['net', 'use', '/delete', drive_name, '/y']
        rc, output = self.run(cmd, expected_rc=0)
        return rc

    def get_domain(self):
        """
        Processing below output to return domain string - 'pztest24.local'
            C:\Windows\system32>wmic computersystem get domain
            Domain
            txupzqa.com
            C:\Windows\system32>
        TODO: Getting domain from AD server hosting AD foreset is not implemented.
        Note: Current implementation works only for a AD system hosting single domain.
        :return:
        """

        cmd = [DosCmd._wmic, 'computersystem', 'get', 'domain']
        rc, output = self.run(cmd, expected_rc=0)
        header_regx = re.compile('^Domain$')
        domain_regx = re.compile('^(\S+)$')
        blankLine_regx = re.compile('^$')

        passed_header, found_domain, domain = False, False, None
        shares = {}

        for line in output.split('\n'):
            line = line.strip()

            if blankLine_regx.match(line):
                continue

            if not passed_header:
                if header_regx.match(line):
                    passed_header = True
                continue

            if not found_domain:
                m = domain_regx.match(line)
                if m:
                    domain = m.group(1)
                    found_domain = True
                break

        return domain

    def AddADAcct(self, acctType, domainName, domainSuffix, acctName, *args):
        #"""
        # Adds user/group account into AD. Password for an added user will be same as its userName
        # param acctType:   user|group|computer
        # param domainName: Name of AD domain
        # param acctName:   Name of user/group to be added/updated/deleted
        # param args:       For a user account, specify name of the group of which user will be a memberof
        #"""
        acctType = acctType.lower()
        acctTypes = ('group', 'user', 'computer')  # supported AD account types
        if acctType not in acctTypes:
            raise Exception('AddADAcct: %s account type is not supporrted for adding account in AD' % (acctType))
        cnCategory = 'Computers' if acctType == 'computer' else 'Users'

        isAcctPresent = self.QueryAD(acctType, domainName, domainSuffix, acctName)
        if isAcctPresent:
            return 0

        cmd = ['dsadd', acctType, "cn=%s,cn=%s,dc=%s,dc=%s" % (acctName, cnCategory, domainName, domainSuffix)]
        if acctType == 'user':
            cmd += ['-pwd', acctName]

        rc, output = self.CmdRunner(cmd)

        if acctType == 'user':
            groupName = args[0]
            if groupName is not None:
                rc = self.EditADUserGroup('add', domainName, domainSuffix, groupName, acctName)
        return rc

    def RemoveADAcct(self, acctType, domainName, domainSuffix, acctName):
        #"""
        # Removes a user/group account from AD
        # param acctType:   user|group|computer
        # param domainName: Name of AD group
        # param acctName:   Name of AD user
        #"""
        acctType = acctType.lower()
        acctTypes = ('group', 'user', 'computer') # supported AD account types
        if acctType not in acctTypes:
            raise Exception('RemoveADAcct: %s account type is not supporrted for adding account in AD' % (acctType))

        isAcctPresent = self.QueryAD(acctType, domainName, domainSuffix, acctName)
        if not isAcctPresent:
            return 0

        cmd = ['dsquery', acctType, '-name', acctName, '|', 'dsrm', '-noprompt']
        rc, output = self.CmdRunner(cmd)
        return rc

    def ChangeStateADAcct(self, opType, acctType, domainName, domainSuffix, acctName):
        #"""
        # Change state of an AD account from 'enabled' -> 'disabled' and vice-versa
        # param opType:      enable|disable
        # param acctType:    computer
        # param domainName:  Name of AD domain
        # param acctName:    Name of account to be modified
        #"""
        opType = opType.lower()
        opTypes = ['enable', 'disable']
        if opType not in opTypes:
            raise Exception('ChangeStateADAcct: %s optype is not supporrted for editing state of account in AD' % (opType))

        acctType = acctType.lower()
        acctTypes = ('computer') # supported AD account types
        if acctType not in acctTypes:
            raise Exception('ChangeStateADAcct: %s account type is not supporrted for editing state of account in AD' % (acctType))

        isEnabledAcctPresent = self.QueryAD(acctType, domainName, domainSuffix, acctName)
        isDisabledAcctPresent = self.QueryAD(acctType, domainName, domainSuffix, acctName, None, 'disabled')

        if not (isEnabledAcctPresent or isDisabledAcctPresent):
            raise Exception('ChangeStateADAcct: %s account is not present in AD' % (acctType))

        # No-action conditions
        if opType == 'enable':
            # When acct is enabled, doing 'dsquery with '-disabled' flag will not list acct
            if isEnabledAcctPresent and not isDisabledAcctPresent:
                return 0
        if opType == 'disable':
            # When acct is disabled, doing 'dsquery with/without '-disabled' flag will list acct
            if isEnabledAcctPresent and isDisabledAcctPresent:
                return 0

        return self._changeStateADAcct(opType, acctType, domainName, domainSuffix, acctName)

    def _changeStateADAcct(self, opType, acctType, domainName, domainSuffix, acctName):
        #"""
        # Change state of an AD account from 'enabled' -> 'disabled' and vice-versa
        # param opType:      enable|disable
        # param acctType:    computer
        # param domainName:  Name of AD domain
        # param acctName:    Name of account to be modified
        #"""
        opTypeMap = {'enable' : 'no', 'disable' : 'yes'}
        cnCategory = 'Computers' if acctType == 'computer' else 'Users'
        cmd = [ 'dsmod',  acctType, 'cn=%s,cn=%s,dc=%s,dc=%s' % (acctName,  cnCategory, domainName, domainSuffix), '-disabled',  opTypeMap[opType] ]

        rc, output = self.CmdRunner(cmd)
        return rc

    def EditADUserGroup(self, opType, domainName, domainSuffix, groupName, userName):
        #"""
        # Add/remove a user to/from a group
        # param opType:     add|remove a user to a group
        # param domainName: Name of AD domain
        # param groupName:  Name of AD group
        # param userName:   Name of AD user
        #"""
        opType = opType.lower()
        opTypes = ('add', 'remove') # supported AD account types
        if opType not in opTypes:
            raise Exception('EditADUserGroup: %s operation is not supporrted for editing group of an AD user' % (opType))

        opTypeMap = {'add' : '-addmbr', 'remove' : '-rmmbr'}

        isGroupPresent = self.QueryAD('group', domainName, domainSuffix, groupName)
        if not isGroupPresent:
            if opType == 'add':
                raise Exception('EditADUserGroup: AD group %s is not present for adding user %s.' % (groupName, userName))
            return 0  # When opType is 'remove'; then no action is needed

        isMember = self._isADGroupMember(domainName, domainSuffix, groupName, userName)

        if opType == 'add' and isMember:
            return 0

        if opType == 'remove' and not isMember:
            return 0

        cmd = ['dsmod', 'group', "cn=%s,cn=users,dc=%s,dc=%s" % (groupName, domainName, domainSuffix), opTypeMap[opType], "cn=%s,cn=users,dc=%s,dc=%s" % (userName, domainName, domainSuffix)]

        rc, output = self.CmdRunner(cmd)
        return rc

    def QueryAD(self, acctType, domainName, domainSuffix, acctName, groupName=None, state='enabled'):
        #"""
        # Queries AD for a user/group and returns boolean (True for presence and False for abscence)
        # param acctType:   user|group|computer
        # param domainName: Name of AD domain
        # param acctName:   Name of user/group to be queried
        # param groupName:  Name of AD group of which user is a member of.
        # param state:      State of AD account- enabled|disabled
        #"""
        acctTypes = ('group', 'user', 'computer') # supported AD account types
        if acctType not in acctTypes:
            raise Exception('QueryAD: %s account type is not supporrted for query in AD' % (acctType))

        states = ('enabled', 'disabled')
        if state not in states:
            raise Exception('QueryAD: %s state is not supported for querying AD database' % (state))

        cmd = ['dsquery', acctType, '-name', acctName]
        if state == 'disabled':
            cmd += ['-disabled']

        isAcctPresent = self._checkADQueryResults(cmd, acctType, domainName, domainSuffix, acctName)

        if acctType == 'user' and groupName is not None:
            isAcctPresent = self._isADGroupMember(domainName, domainSuffix, groupName, acctName)

        return isAcctPresent

    def _isADGroupMember(self, domainName, domainSuffix, groupName, userName):
        #"""
        # Queries Group to find if an user is member of the group specified.
        # param domainName: AD Domain Name
        # param groupName:   Name of AD group
        # param userName:   Name of AD user
        #"""
        foundInADGroup = False
        cmd = ['dsget', 'group', 'cn=%s,cn=users,dc=%s,dc=%s' % (groupName, domainName, domainSuffix), '-members']
        foundInADGroup = self._checkADQueryResults(cmd, 'user', domainName, domainSuffix, userName)

        if foundInADGroup:
            logger.info('User %s\%s found in %s group' % (domainName, userName, groupName))
        else:
            logger.info('User %s\%s not found in %s group' % (domainName, userName, groupName))

        return foundInADGroup

    def _checkADQueryResults(self, cmd, acctType, domainName, domainSuffix, acctName):
        #"""
        # Check results of an AD query for presene of an AD acct in a domain
        # param cmd:        A command to be run whose output is to be verified
        # param acctType:   Account type
        # param domainName: Name of an AD domain
        # param acctName:   Name of AD user or group
        #"""
        cnCategory = 'Computers' if acctType == 'computer' else 'Users'
        patternString = '"CN=%s,CN=%s,DC=%s,DC=%s"' % (acctName, cnCategory, domainName, domainSuffix)

        isAcctPresent = False
        rc, output = self.CmdRunner(cmd)

        for line in output.split('\n'):
            m = re.match(patternString, line, re.I)
            if m:
                isAcctPresent = True
                break

        if isAcctPresent:
            logger.info('Account %s\%s is present in AD' % (domainName, acctName))
        else:
            logger.info('User %s\%s is not present in AD' % (domainName, acctName))

        return isAcctPresent

    def AddShare(self, shareName, dirpath):
        cmd = ['net', 'share', '%s=%s' % (shareName, dirpath), '/grant:everyone,FULL']
        return self.CmdRunner(cmd)[0]

    def RemoveShare(self, shareName):
        cmd = ['net', 'share', '/delete', shareName]
        return self.CmdRunner(cmd)[0]

    def GetShares(self):
        #"""
        #Returns a dicionary of 'Share name' mapped to 'Resource' by parsing output of 'net share'
        #On a Windows system, local folder is exported as a share.
        #
        #Excerpts from sample output:
        #
        #C:\Users\Administrator>net share
        #
        #Share name   Resource                        Remark
        #
        #-------------------------------------------------------------------------------
        #C$           C:\                             Default share
        #IPC$                                         Remote IPC
        #ADMIN$       C:\Windows                      Remote Admin
        #EBS          C:\EBS
        #NETLOGON     C:\Windows\SYSVOL\sysvol\pztest28.com\SCRIPTS
        #pune1-cc1    C:\DFSRoots\pune1-cc1
        #The command completed successfully.
        #
        #C:\Users\Administrator>
        #
        #"""
        cmd = ['net', 'share']
        output = self.CmdRunner(cmd)[1]

        headerRegx = re.compile('^\s*Share\s+name\s+Resource\s+Remark\s*')
        separatorRegx = re.compile(r'^-+$')
        recordRegx = re.compile('\s*^(\S+)\s+(\S+)\s*')
        footerRegx = re.compile('^\s*The command completed successfully.\s*$')
        blankLineRegx = re.compile('^$')

        passedHeader, passedSeparator, passedFooter = False, False, False
        shares = {}

        for line in output.split('\n'):
            line = line.strip()

            if blankLineRegx.match(line):
                continue

            if not passedHeader:
                if headerRegx.match(line):
                    passedHeader = True
                continue

            if not passedSeparator:
                if separatorRegx.match(line):
                    passedSeparator = True
                continue

            if not passedFooter:
                if footerRegx.match(line):
                    passedFooter = True
                    break

            m = recordRegx.match(line)
            if m:
                shares[m.group(1)] = m.group(2)  # Maps a 'share name' to 'resource'

        return shares

    def AddDFSRoot(self, adFQHN, shareName):
        cmd = ['dfsutil', 'root', 'AddDom', '\\\\%s\%s' % (adFQHN, shareName), 'V1' ]
        with DosCmd.syswow64redirector:
            return self.CmdRunner(cmd)[0]

    def RemoveDFSRoot(self, adDomain, shareName):
        cmd = ['dfsutil', 'root', 'remove', '\\\\%s\%s' % (adDomain, shareName) ]
        with DosCmd.syswow64redirector:
            return self.CmdRunner(cmd)[0]

    def GetDFSRoots(self, adFQDN):
        #"""
        # Returns a list of DFS roots by parsing output of 'dfsutil domain pztest28.com'
        # Process output like as below, lines between header and footer lines are DFS roots
        #
        # C:\Users\Administrator>dfsutil domain pztest28.com
        #
        # Roots on Domain pztest28.com
        #
        # pune1-cc1
        #
        # Done with Roots on Domain pztest28.com
        #
        # Done processing this command.
        #
        # C:\Users\Administrator>
        #"""

        cmd = ['dfsutil', 'domain', adFQDN]
        with DosCmd.syswow64redirector:
            output = self.CmdRunner(cmd)[1]

        header = r'Roots on Domain %s' % adFQDN
        footer = r'Done with Roots on Domain %s' % adFQDN
        headerRegx = re.compile(header, re.I)
        footerRegx = re.compile(footer, re.I)
        blankLineRegx = re.compile('^$')

        passedHeader, passedFooter = False, False
        DFSRoots = []

        for line in output.split('\n'):
            line = line.strip()

            if blankLineRegx.match(line):
                continue

            if not passedHeader:
                if headerRegx.match(line):
                    passedHeader = True
                continue

            if not passedFooter:
                if footerRegx.match(line):
                    passedFooter = True
                    break

            DFSRoots.append(line)

        return DFSRoots

    def AddDFSLink(self, adFQDN, adFQHN, DFSRootName, shareName):
        cmd = ['dfsutil', 'link', 'add', '\\\\%s\%s\%s' % (adFQDN, DFSRootName, shareName), '\\\\%s\%s\%s' % (adFQHN, DFSRootName, shareName)]
        with DosCmd.syswow64redirector:
            return self.CmdRunner(cmd)[0]

    def RemoveDFSLink(self, adFQDN, DFSRootName, shareName):
        cmd = ['dfsutil', 'link', 'remove', '\\\\%s\%s\%s' % (adFQDN, DFSRootName, shareName)]
        with DosCmd.syswow64redirector:
            return self.CmdRunner(cmd)[0]

    def GetDFSLink(self, adDomainName, adFQDN, DFSRootName, shareName):
        data = self._getDFSLinkTargets(adDomainName, adFQDN, DFSRootName, shareName)
        return data['link']

    def AddDFSTarget(self, adFQDN, DFSRootName, CC, shareName):
        cmd = ['dfsutil', 'target', 'add', '\\\\%s\%s\%s' % (adFQDN, DFSRootName, shareName), '\\\\%s\%s' % (CC, shareName)]
        with DosCmd.syswow64redirector:
            return self.CmdRunner(cmd)[0]

    def RemoveDFSTarget(self, adFQDN, DFSRootName, CC, shareName):
        cmd = ['dfsutil', 'target', 'remove', '\\\\%s\%s\%s' % (adFQDN, DFSRootName, shareName), '\\\\%s\%s' % (CC, shareName)]
        with DosCmd.syswow64redirector:
            return self.CmdRunner(cmd)[0]

    def ManageInsite(self, adFQDN, DFSRootName, shareName, opCode):

        _insiteEnabled = self._isInsiteEnabled(adFQDN, DFSRootName, shareName)

        if _insiteEnabled is None:
            raise Exception ("Could not determine value of 'Insite' property")

        if opCode == 'add':
            if _insiteEnabled:
                return 0
            cmd = ['dfsutil', 'Property', 'Insite', 'Enable', '\\\\%s\%s\%s' % (adFQDN, DFSRootName, shareName)]
        elif opCode == 'remove':
            if not _insiteEnabled:
                return 0
            cmd = ['dfsutil', 'Property', 'Insite', 'Disable', '\\\\%s\%s\%s' % (adFQDN, DFSRootName, shareName)]

        with DosCmd.syswow64redirector:
            return self.CmdRunner(cmd)[0]

    def _isInsiteEnabled(self, adFQDN, DFSRootName, shareName):
        """
        # Returns True, if 'ENABLED' string is found in output
        # Sample outputs indicating ENABLED and DISABLED state
        #     Namespace \\domain.com\cc1-1379\smoke: InSite Referrals ENABLED
        #     Namespace \\domain.com\cc1-1379\smoke: InSite Referrals DISABLED
        """
        cmd = ['dfsutil', 'Property', 'Insite', '\\\\%s\%s\%s' % (adFQDN, DFSRootName, shareName)]
        rc, output = self.CmdRunner(cmd)
        logger.info('output: %s' % (output))
        ret = None

        blankLineRegx = re.compile('^$')
        expectedEntry = 'Namespace \\\\' + '\\'.join([adFQDN, DFSRootName, shareName])
        expectedEntry2 = expectedEntry.replace('\\', '\\\\')  # Escape backslashes for use in regular expression
        # To match: Namespace \\domain.com\cc1-1379\smoke: InSite Referrals ENABLED
        # and capture last word - ENABLED or DISABLED
        insiteRegx = re.compile (r'^%s:\s+Insite\s+Referrals\s+(.+)$' % expectedEntry2, re.I)

        for line in output.split('\n'):
            line = line.strip()

            if blankLineRegx.match(line):
                continue

            m = insiteRegx.match(line)
            if m:
                insiteStatus = m.group(1).upper()
                if  insiteStatus == 'ENABLED':
                    ret = True
                elif insiteStatus == 'DISABLED':
                    ret = False
                break

        return ret

    def GetDFSTargets(self, adDomainName, adFQDN, DFSRootName, shareName):
        data = self._getDFSLinkTargets(adDomainName, adFQDN, DFSRootName, shareName)
        return data['targets']

    def _getDFSLinkTargets(self, adDomainName, adFQDN, DFSRootName, shareName):
        """
        # Returns a data-structure of DFS link and targets by processing as below.
        # C:\\Users\\Administrator>dfsutil /root:\\pztest28.com\\pune1-cc1 /view
        # Domain Root with 1 Links [Blob Size: 720 bytes]
        #
        # Root Name="\\PZTEST28\\pune1-cc1" State="OK" Timeout="300"
        # Target="\\demoad\\pune1-cc1" State="ONLINE"  [Site: Default-First-Site-Name]
        #
        # Link Name="smoke" State="OK" Timeout="300"
        #        Target="\\demoAD.pztest28.com\\pune1-cc1\\smoke" State="ONLINE"  [Site: Default-First-Site-Name]
        #        Target="\\pune1-cc1\\smoke" State="ONLINE"  [Site: Default-First-Site-Name]
        #
        # Root with 1 Links [Blob Size: 720 bytes]
        #
        # NOTE: All site information shown was generated by this utility.
        # Actual DFS behavior depends on site information currently in use by
        # DFS service, and may not reflect configuration changes made recently.
        #
        # Done processing this command.
        #
        """
        cmd = ['dfsutil', '/root:\\\\%s\\%s' % (adFQDN, DFSRootName), '/view']
        with DosCmd.syswow64redirector:
            rc, output = self.CmdRunner(cmd, 'Ignore')

        data = {'link': None, 'targets': []}

        # When 'RemoveTarget' or 'RemoveLink' is called on an system with no DFS namespace
        # then return empty data as 'cmd' would fail
        if rc != 0:
            return data

        blankLineRegx = re.compile('^$')
        # To match: Root Name="\\PZTEST28\pune1-cc1" State="OK" Timeout="300"
        header = r'Root Name="\\\\%s\\%s".*' % (adDomainName, DFSRootName)
        headerRegx = re.compile(header, re.I)
        # To match: Root with 1 Links [Blob Size: 720 bytes]
        footer = r'Root with \d+ Links \[Blob Size: \d+ bytes\]'
        footerRegx = re.compile(footer, re.I)
        # To match: Link Name="smoke" State="OK" Timeout="300"
        # and extract 'smoke'
        link = r'^Link Name="([^"]+)"\s+State=.*$'
        linkRegx = re.compile(link, re.I)
        # To match: Target="\\pune1-cc1\smoke" State="ONLINE"  [Site: (null)]
        # and extract '\\pune1-cc1\smoke'
        target = re.compile(r'Target="([^"]+)"\s+State="[^"]*"\s+\[Site:\s*\(?(.*)\)?.*\]')
        targetRx = re.compile(target)
        passedHeader, passedFooter = False, False

        for line in output.split('\n'):
            line = line.strip()

            if blankLineRegx.match(line):
                continue

            if not passedHeader:
                if headerRegx.match(line):
                    passedHeader = True
                continue

            if not passedFooter:
                if footerRegx.match(line):
                    passedFooter = True
                    break

            m = linkRegx.match(line)
            if m:
                data['link'] = m.group(1)
                continue

            m = targetRx.match(line)
            if m:
                target = m.group(1)
                # site = m.group(2)  # Unused for now. But keeping it for future if need arises to use it.
                # First target: Target="\\demoAD.pztest28.com\pune1-cc1\smoke" State="ONLINE"  [Site: Default-First-Site-Name]
                # pointing to local share is created while adding link; so ignore it while collecting targets
                # Select only #2 part targets like: Target="\\pune1-cc1\smoke" State="ONLINE"  [Site: Default-First-Site-Name]
                targetParts = [ p for p in target.split('\\') if len(p) > 0 ]  # Splitting '\\' on '\' makes empty fields, so ignore them
                if len(targetParts) == 2:
                    data['targets'].append(target)

        return data

    def GetDFSPktInfo(self):
        cmd = ['dfsutil', '/pktinfo']
        with DosCmd.syswow64redirector:
            return self.CmdRunner(cmd)[1]

    def FlushDFSCache(self):
        #
        # Reference: https://technet.microsoft.com/en-us/library/cc736784(v=ws.10).aspx#BKMK_35
        #
        # /pktflush:
        #        Flushes the client's locally cached target referral list provided by the DFS server. When the client tries to access the
        # corresponding link, this forces the client to refresh the referral list of targets from the DFS server.
        # Some of the entries in the PKT may not get flushed, especially if DFS is in the process of using the referrals.
        #
        # /spcflush:
        #           The client flushes out its cached knowledge about the trusted domains and the domain controllers of these domains.
        #
        # /PurgeMupCache:
        #           Resets the client's knowledge about the various sites' information.
        #           This is a troubleshooting option which should only be run on the client.
        #
        overall_rc = 0
        _flushOps = ['/pktflush', '/spcflush', '/PurgeMupCache']
        for _flushOp in _flushOps:
            cmd = ['dfsutil', _flushOp]
            with DosCmd.syswow64redirector:
                rc, output = self.CmdRunner(cmd, 'IGNORE')
            if rc not in [0, 1326]:
                overall_rc = rc
                logger.error('%s' % (output))
            logger.info('dfsutil doing %s returned %d' % (_flushOp, rc))

        # Also, flush other caches
        # Error code 1326 has been added in the list of success codes as its source
        # can be AD configuration with other/trusted domains and observed only while
        # executing 'dfsutil /spcflush' and 'dfsutil /spcflush' when run against domain.com
        # e.g.
        # C:\temp>dfsutil /spcflush
        # Could not execute the command successfully
        # SYSTEM ERROR - Logon failure: unknown user name or bad password.
        # C:\temp>echo %errorlevel%
        # 1326
        #
        # More notes:
        # http://www.error.info/windows/permission-1326.html indicates that configuration of
        # local security policies as a source of this error which as saide has occured while
        # working with domain.com and revise it when run on a new setup.
        #

        _cacheTypes = ['Provider', 'Referral', 'Domain']
        for _cacheType in _cacheTypes:
            cmd = ['dfsutil', 'Cache',  _cacheType, 'flush']
            with DosCmd.syswow64redirector:
                rc, output = self.CmdRunner(cmd, 'IGNORE')
            if rc not in [0, 1326]:
                overall_rc = rc
                logger.error('%s' % (output))
            logger.info('dfsutil flushing %s cache returned %d' % (_cacheType, rc))

        return overall_rc


class MacCmd(Cmd):
    SCRIPTSDIR = "%s/pandas/RPC/Scripts" % expanduser('~')
    output = None
    rc = 0
    def Run(self, cmdSpec):
        try:
            # logger.info('$ %s' % ' '.join(cmdSpec))
            output = check_output(cmdSpec)
            print('$ %s\n%s' % (cmdSpec, output))
            self.output = output
            return 0, output
        except CalledProcessError as e:
            # logger.error("cmd %s, return code %s, message %s" % (cmdSpec, e.returncode, e.output))
            print("cmd %s, return code %s, message %s" % (cmdSpec, e.returncode, e.output))
            raise Exception(e)

    def CreateWordDoc(self, filePath):
        scriptPath = os.path.join(self.SCRIPTSDIR, "mswordcreate.scpt")
        rc, output = self.Run(["osascript", scriptPath, filePath])
        return rc, output

    def WriteWordDoc(self, filePath, inData):
        scriptPath = os.path.join(self.SCRIPTSDIR, "mswordwrite.scpt")
        rc, output = self.Run(["osascript", scriptPath, filePath, inData])
        return rc, output

    def ReadWordDoc(self, filePath):
        scriptPath = os.path.join(self.SCRIPTSDIR, "mswordread.scpt")
        rc, output = self.Run(["osascript", scriptPath, filePath])
        return rc, output

    def SaveWordDoc(self, filePath, newFilePath):
        scriptPath = os.path.join(self.SCRIPTSDIR, "mswordsaveas.scpt")
        rc, output = self.Run(["osascript", scriptPath, filePath, newFilePath])
        return rc, output

    def CopyDir(self, srcPath, dstPath):
        """
        Copy files from source path to destination path.
        :param srcPath: source directory path
        :param dstPath: destination directory path
        """
        cmd = ['cp', '-R', srcPath, dstPath]
        rc, output = self.Run(cmd)
        if rc != 0:
            logger.info('output %s' % output)
        return rc

    def CreateExcelWorkbook(self, filePath):
        t1 = threading.Thread(target=self.CreateExcelDoc, args=(filePath,))
        t2 = threading.Thread(target=self.GrantAccessHandler, args=("Microsoft Excel",))

        # starting thread 1
        t1.start()
        time.sleep(5)
        # starting thread 2
        t2.start()
        # wait until thread 2 is completely executed
        t2.join()

        # wait until thread 1 is completely executed
        t1.join()
        return 0, self.output

    def CreateExcelDoc(self, filePath):
        scriptPath = os.path.join(self.SCRIPTSDIR, "msexcelcreate.scpt")
        cmdSpec = ["osascript", scriptPath, filePath]
        try:
            self.rc, self.output = self.Run(cmdSpec)
            logger.info('$ %s\n%s' % (cmdSpec, self.output))
        except CalledProcessError as e:
            print("cmd %s, return code %s, message %s" % (cmdSpec, e.returncode, e.output))
            logger.info("cmd %s, return code %s, message %s" % (cmdSpec, e.returncode, e.output))
            self.rc, self.output = e.returncode, e.output

    def GrantAccessHandler(self, app):
        #SCRIPTSDIR = "%s/pandas/RPC/Scripts" % expanduser('~')
        scriptPath = os.path.join(self.SCRIPTSDIR, "savehandler.scpt")
        cmdSpec = ["osascript", scriptPath, app]
        try:
            #output = check_output(cmdSpec)
            rc, output = self.Run(cmdSpec)
            print('$ %s\n%s' % (cmdSpec, output))
        except CalledProcessError as e:
            print("cmd %s, return code %s, message %s" % (cmdSpec, e.returncode, e.output))

    def WriteExcelWorkbook(self, filePath, inData):
        scriptPath = os.path.join(self.SCRIPTSDIR, "msexcelwrite.scpt")
        rc, output = self.Run(["osascript", scriptPath, filePath, inData])
        return rc, output

    def ReadExcelWorkbook(self, filePath):
        scriptPath = os.path.join(self.SCRIPTSDIR, "msexcelread.scpt")
        rc, output = self.Run(["osascript", scriptPath, filePath])
        return rc, output

    def SaveExcelWorkbook(self, filePath, newFilePath):
        scriptPath = os.path.join(self.SCRIPTSDIR, "msexcelsaveas.scpt")
        rc, output = self.Run(["osascript", scriptPath, filePath, newFilePath])
        return rc, output

    def WriteRefExcelWorkbook(self, filePath, inData):
        scriptPath = os.path.join(self.SCRIPTSDIR, "msexcelwriteref.scpt")
        rc, output = self.Run(["osascript", scriptPath, filePath, inData])
        return rc, output

    def ValidateExcelWorkbook(self, filePath, inData):
        scriptPath = os.path.join(self.SCRIPTSDIR, "msexcelvalidate.scpt")
        rc, output = self.Run(["osascript", scriptPath, filePath, inData])
        return rc, output

    def CreatePpt(self, filePath):
        t1 = threading.Thread(target=self.CreatePPTFile, args=(filePath,))
        t2 = threading.Thread(target=self.GrantAccessHandler, args=("Microsoft PowerPoint",))

        # starting thread 1
        t1.start()
        time.sleep(5)
        # starting thread 2
        t2.start()
        # wait until thread 2 is completely executed
        t2.join()

        # wait until thread 1 is completely executed
        t1.join()
        return 0, self.output

    def CreatePPTFile(self, filePath):
        scriptPath = os.path.join(self.SCRIPTSDIR, "mspptcreate.scpt")
        cmdSpec = ["osascript", scriptPath, filePath]
        try:
            self.rc, self.output = self.Run(cmdSpec)
            logger.info('$ %s\n%s' % (cmdSpec, self.output))
        except CalledProcessError as e:
            print("cmd %s, return code %s, message %s" % (cmdSpec, e.returncode, e.output))
            logger.info("cmd %s, return code %s, message %s" % (cmdSpec, e.returncode, e.output))

    def WritePpt(self, filePath, inData):
        scriptPath = os.path.join(self.SCRIPTSDIR, "mspptwrite.scpt")
        rc, output = self.Run(["osascript", scriptPath, filePath, inData])
        return rc, output

    def ReadPpt(self, filePath):
        t1 = threading.Thread(target=self.ReadPptPres, args=(filePath,))
        t2 = threading.Thread(target=self.GrantAccessHandler, args=("Microsoft PowerPoint",))

        # starting thread 1
        t1.start()
        time.sleep(5)
        # starting thread 2
        t2.start()
        # wait until thread 2 is completely executed
        t2.join()
        # wait until thread 1 is completely executed
        t1.join()
        return 0, self.output

    def ReadPptPres(self, filePath):
        scriptPath = os.path.join(self.SCRIPTSDIR, "mspptread.scpt")
        cmdSpec = ["osascript", scriptPath, filePath]
        try:
            self.rc, self.output = self.Run(cmdSpec)
        except CalledProcessError as e:
            print("cmd %s, return code %s, message %s" % (cmdSpec, e.returncode, e.output))
            logger.info("cmd %s, return code %s, message %s" % (cmdSpec, e.returncode, e.output))
            self.rc, self.output = e.returncode, e.output

    def SavePpt(self, filePath, newFilePath):
        scriptPath = os.path.join(self.SCRIPTSDIR, "mspptsaveas.scpt")
        rc, output = self.Run(["osascript", scriptPath, filePath, newFilePath])
        return rc, output

    def WriteRefPpt(self, filePath, inData):
        scriptPath = os.path.join(self.SCRIPTSDIR, "mspptwriteref.scpt")
        rc, output = self.Run(["osascript", scriptPath, filePath, inData])
        return rc, output

    def ValidatePpt(self, filePath, inData):
        t1 = threading.Thread(target=self.ValidatePPTPres, args=(filePath, inData))
        t2 = threading.Thread(target=self.GrantAccessHandler, args=("Microsoft PowerPoint",))

        # starting thread 1
        t1.start()
        time.sleep(5)
        # starting thread 2
        t2.start()
        # wait until thread 2 is completely executed
        t2.join()

        # wait until thread 1 is completely executed
        t1.join()
        return 0, self.output

    def ValidatePptPres(self, filePath, inData):
        scriptPath = os.path.join(self.SCRIPTSDIR, "mspptvalidate.scpt")
        cmdSpec = ["osascript", scriptPath, filePath, inData]
        try:
            self.rc, self.output = self.Run(cmdSpec)
            logger.info('$ %s\n%s' % (cmdSpec, self.output))
        except CalledProcessError as e:
            print("cmd %s, return code %s, message %s" % (cmdSpec, e.returncode, e.output))
            logger.info("cmd %s, return code %s, message %s" % (cmdSpec, e.returncode, e.output))
            self.rc, self.output = e.returncode, e.output


if __name__ == "__main__":
    obj_doscmd = DosCmd()
    obj_doscmd.get_acl('D:\\test')
