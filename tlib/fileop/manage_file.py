# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/10 13:47
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

""" manage file/dictory utility functions """

import os
import sys
import re
import random
import time
import string
import threading
import platform
from uuid import uuid4
import shutil
import filecmp
import stat
import hashlib
from glob import iglob
from pprint import pformat
import traceback
import errno
from collections import Iterable

from tlib import log
from tlib.platform.cmd import DosCmd, MacCmd

# =============================
# --- Global
# =============================
logger = log.get_logger()
useDFS = False
useCloudPath = False


# ========================
#   base
# ========================

class Base:
    """ Base class of all the classes in the HostLib
    """
    _cache = None
    _debug = False
    _curThreadId = threading.local()

    def __init__(self, cache):
        self._cache = cache

    def SetContextKey(self, tsId, tcId):
        # TODO - Check if already set
        logger.debug('Set thread=%s, tsId=%s tcId=%s' % (threading.current_thread().name, tsId, tcId))
        self._curThreadId.tsId, self._curThreadId.tcId = tsId, tcId

    def GetContextKey(self):
        # TODO - Check if not set
        logger.debug('Get thread=%s, tsId=%s tcId=%s' % (
        threading.current_thread().name, self._curThreadId.tsId, self._curThreadId.tcId))
        return self._curThreadId.tsId, self._curThreadId.tcId


class TcCache(Base):
    """
    Class to store the Test Suite and Test Case context during execution
    """
    _data = {}

    def __init__(self):
        pass

    def Get(self, key):
        tsId, tcId = self.GetContextKey()
        if tsId not in self._data.keys():
            raise Exception('error: tsId %s not found in the cache' % tsId)

        if tcId not in self._data[tsId].keys():
            raise Exception('error: tcId %s not found in the cache' % tcId)

        if key not in self._data[tsId][tcId].keys():
            raise Exception('error: key %s not found in the cache' % key)
        return self._data[tsId][tcId][key]

    def Set(self, key, value):
        tsId, tcId = self.GetContextKey()
        if tsId not in self._data.keys():
            self._data[tsId] = {}

        if tcId not in self._data[tsId].keys():
            self._data[tsId][tcId] = {}

        logger.debug('TcCache: Set: key=%s, tsId=%s, tcId=%s' % (key, tsId, tcId))
        self._data[tsId][tcId][key] = value

    def Del(self, key):
        tsId, tcId = self.GetContextKey()
        if tsId not in self._data.keys():
            raise Exception('error: tsId %s not found in the cache' % tsId)

        if tcId not in self._data[tsId].keys():
            raise Exception('error: tcId %s not found in the cache' % tcId)

        if key not in self._data[tsId][tcId].keys():
            raise Exception('error: key %s not found in the cache' % key)
        del self._data[tsId][tcId][key]


class IFS(Base):
    """
    Represents file-system functions like mapping and unmapping of a share
    """

    def __init__(self, cache=None):
        Base.__init__(self, cache)
        self._cmd = DosCmd()
        self._ipath = IPath()
        self._idir = IDir()

    def MapShare(self, *args, **kwargs):
        args = list(args)
        obj = args.pop(0)

        mapInput = self._getMapInput(obj, args, kwargs)
        driveName = mapInput['driveName']  # Default value
        useDriveLetter = self._canUseDriveLetter(driveName)

        if useDriveLetter:
            self.DeleteShare(driveName)
            return self._mapDrive(mapInput)
        else:
            raise Exception('Drive %s can not be used for mapping' % driveName)

    def _getMapInput(self, obj, *args):

        # This will create varaibles like useDfs, useCloudPath which are keys of dictionary
        args = list(args)
        kwargs = args.pop(-1)
        args = args.pop(0)

        # variables retryAttempts and interval will be created
        for k, v in kwargs.iteritems():
            globals()[k] = v

        # set default value as None
        mapInput = {k: None for k in
                    ('cc', 'shareName', 'driveName', 'adDomain', 'userName', 'userPasswd', 'retryAttempts', 'interval')}
        mapInput['retryAttempts'] = retryAttempts
        mapInput['interval'] = interval
        mapInput['useDFS'] = False

        # args to keyword in test-cases are wrapped in list 'param' of MapShare() in PanRpc.py
        # which further gets wrapped in '*args' of Call() and then reaches here as list containing list and so -
        args = args[0]

        if len(args) >= 1:
            mapInput['cc'] = args[0]
        if len(args) >= 2:
            mapInput['shareName'] = args[1]

        if len(args) <= 2:
            mapInput['driveName'] = (obj['Drive']).upper()
            mapInput['adDomain'] = obj['Domain']
            mapInput['userName'] = obj['Login']
            mapInput['userPasswd'] = obj['Pass']
        elif len(args) >= 6:
            mapInput['driveName'] = (args[2]).upper()
            mapInput['adDomain'] = args[3]
            mapInput['userName'] = args[4]
            mapInput['userPasswd'] = args[5]
        else:
            logger.error("Input for mapping a drive is not formed")

        # From test-bed XML, 'Domain' key will have FQDN value and so assign it 'adFQDN'
        mapInput['adFQDN'] = mapInput['adDomain']
        # Convert adDomain name 'pztest28.com' to 'pztest28' by removing '.com'
        adDomainRegx = re.compile(r'^([^.]+).*')
        m = adDomainRegx.match(mapInput['adFQDN'])
        mapInput['adDomain'] = m.group(1)

        if useDFS:
            driveName = obj.get('DFSDrive')
            if driveName is None:
                raise Exception("In test-bed, 'DFSDrive' which is a drive letter is not specified to map a share")
            mapInput['driveName'] = driveName.upper()
            mapInput['useDFS'] = True

        if useCloudPath:
            mapInput['shareName'] = obj.get('CloudPath')
            if mapInput['shareName'] is None:
                raise Exception("In test-bed, 'CloudPath' which is shareName is not specified to map a share")

        return mapInput

    def DeleteShare(self, *args, **kwargs):
        if len(args) == 1:
            driveName = args[0]  # called from with-in fs.py
        else:
            driveName = args[1]  # called as a keyword and received via Call()

        useDriveLetter = self._canUseDriveLetter(driveName)
        if useDriveLetter:
            return self._unmapDrive(driveName)
        else:
            raise Exception('Drive %s can not be unmapped' % driveName)

    def GetUsedDrives(self):
        """
        This will return a list of
           drives mapped by using 'net use' for accessing SMB shares
           +
           ones like 'C:' used by computer for its own devices
        """
        return self._cmd.GetUsedDrives()

    def GetMappedDrives(self):
        """
        This will return a list of
               drives mapped by using 'net use' for accessing SMB shares ONLY
        """
        return self._cmd.GetMappedDrives()

    def _isDriveMapped(self, driveName):
        mappedDrives = self.GetMappedDrives()
        if driveName in mappedDrives:
            return True
        return False

    def _isDriveUsed(self, driveName):
        usedDrives = self.GetUsedDrives()
        if driveName in usedDrives:
            return True
        return False

    def _canUseDriveLetter(self, driveName):
        """
        A drive letter can be used for both mapping/unmapping
        if it is not like C: used for maping computer's own devices.
        """
        if self._isDriveUsed(driveName):
            if self._isDriveMapped(driveName):
                return True
            else:
                return False
        else:
            return True

    def _mapDrive(self, mapInput):
        # Remove 'useDFS' from 'mapInput' and explicitly assign it to a variable.
        useDFS = mapInput.pop('useDFS')
        # make variables out of dictionary keys
        for k, v in mapInput.iteritems():
            globals()[k] = v
        # Value of resource is based upon 'useDFS' flag.
        # In a normal setup it will be like '\\pune1-cc1\smoke' in '\\<CC name>\<share Name>' format
        resource = '\\\\' + cc + '\\' + shareName
        # FOR DFS it will be like '\\pztest28.com\pune1-cc1\smoke' in '\\<FQDN>\<CC name>\<share Name>' where <CC name>
        #                          is the name of master CC which is used for creating a root in DFS namespace
        if useDFS:
            resource = '\\\\' + adFQDN + '\\' + cc + '\\' + shareName

        return self._cmd.MapDrive(cc, driveName, resource, adDomain, userName, userPasswd, retryAttempts, interval)

    def _unmapDrive(self, driveName):
        if self._isDriveMapped(driveName):
            return self._cmd.UnmapDrive(driveName)
        else:
            logger.info("Drive %s is not mapped. Unmapping is not needed." % (driveName))
            return 0

    def AddShare(self, shareName, dirpath):
        # This is to create a share on a client system itself using a folder in a local drive.
        return self._cmd.AddShare(shareName, dirpath)

    def RemoveShare(self, shareName):
        # This is to remove a share created on a client system itself using above 'AddShare' method.
        return self._cmd.RemoveShare(shareName)


class IPath(Base):
    """ Represents a path for a directory, file or link """

    def __init__(self, cache=None):
        """
        debug  - Set to true if the caller wants debug to be enabled
        """
        Base.__init__(self, cache)

    def PathExists(self, path):
        """
        Checks the file path for existence
        :param path: File path
        :return: Returns True if path exists, False if path does not exist
        """
        try:
            fd = os.open(path, os.O_RDONLY)
            os.close(fd)
        except OSError as e:
            if (e.errno == 2):
                logger.info('file=%s does not exist' % path)
                return False
            logger.info('Error opening file %s.\n%s: %s' % (path, type(e).__name__, e))
        return True

    def CheckExists(self, path, retry_cnt=1, sleep_time=10):
        """
        Checks the path for existance, throws exception otherwise
        :param path: File/Dir path name
        :param retry_cnt: Number of retry in case file does not exists
        :param sleep_time: Amount of time in seconds to sleep in retry
        """
        if not os.path.exists(path):
            # Retry if the file does not exists
            for i in range(retry_cnt):
                if os.path.isfile(path):
                    exists = self.PathExists(path)
                else:
                    exists = os.path.exists(path)
                if exists:
                    logger.info("1 cnt %s path exists %s" % (i, path))
                    break
                else:
                    logger.info("2 cnt %s path not exists %s" % (i, path))
                time.sleep(sleep_time)
            else:
                raise Exception('Path %s does not exist.' % path)
        return 0

    def CheckNotExists(self, path, retry_cnt=1, sleep_time=10):
        """
        Checks the path for non existance, throws exception otherwise
        :param path: File/Dir path name
        :param retry_cnt: Number of retry in case file exists
        :param sleep_time: Amount of time in seconds to sleep in retry
        """
        if os.path.exists(path):
            # Retry if the file exists
            for i in range(retry_cnt):
                if os.path.isfile(path):
                    exists = self.PathExists(path)
                else:
                    exists = os.path.exists(path)
                if not exists:
                    logger.info("111cnt %s path not exists %s" % (i, path))
                    break
                else:
                    logger.info("222cnt %s path exists %s" % (i, path))
                time.sleep(sleep_time)
            else:
                raise Exception('Path %s still exists' % path)
        return 0

    def UpdatePaths(self, src_files, src_data, dest_data):
        """
        Update the src files paths from src data to dest data
        :param src_files: List of file paths
        :param src_data:  Source data to replace from
        :param dest_data:  Destination data to replace to
        :return: Returns the update the src files paths from src data to dest data
        """
        logger.info("src_files %s src_data %s dest_data %s" % \
                       (src_files, src_data, dest_data))
        dest_files = []
        for f in src_files:
            f = f.replace(src_data, dest_data)
            dest_files.append(f)
        logger.info("dest_files %s" % (dest_files))
        return dest_files

    def GetUniqueDirNames(self, filelist):
        """
        Returns the unique list of directory paths in sorted order from the list of files
        :param filelist: List of file paths
        """
        dirs = set()
        for f in filelist:
            d = os.path.dirname(f)
            dirs.add(d)
        # Return dirs listing in sorted order
        dirs = sorted(list(dirs))
        for i, d in enumerate(dirs):
            logger.info("%s %s" % (i, d))
        return dirs

    def Rename(self, path, newPath):
        """ Rename file/dir in source path to destination path, throws exception otherwise """
        try:
            os.rename(path, newPath)
            return 0
        except Exception as e:
            logger.error("Path: Rename failed. %s -> %s\n%s: %s" % (path, newPath, e.__class__.__name__, e))
            raise

    def RenameAll(self, filelist, newprefix="prerenamed", prefixflag=True):
        """
        Rename the files from filelist by adding newprefix
        :param filelist: List of files to rename
        :param newprefix: The prefix used on rename. Default to prerenamed
        :return: Return the final list of filenames
        """
        logger.info("filelist %s newprefix %s" % (filelist, newprefix))
        error_list = []
        new_list = []
        # Only returns the final list
        new_list = []
        for filename in filelist:
            dname = os.path.dirname(filename)
            fname = os.path.basename(filename)
            src_name = filename
            if prefixflag:
                dest_name = os.path.join(dname, "%s_%s" % (newprefix, fname))
            else:
                dest_name = os.path.join(dname, "%s_%s" % (fname, newprefix))
            try:
                logger.info("filename %s src_file %s destfile %s" % \
                               (filename, src_name, dest_name))
                retcode = self.Rename(src_name, dest_name)
                if retcode == 0:
                    new_list.append(dest_name)
            except EnvironmentError as e:
                logger.warning("prerenamed failed: filename %s src_file %s destfile %s" % \
                                  (filename, src_name, dest_name))
                error_list.append((src_name, dest_name))
        if len(error_list):
            logger.warning("error_list: len %s %s" % (len(error_list), error_list))
            return [1]
        return new_list

    def SetAcl(self, path, userPrefix, userIdx, perm, mode):
        """ Applies ACL on the path specified, throws exception otherwise """
        try:
            acl = ACL(userPrefix, userIdx, perm)
            acl.Apply(path, mode)
            return 0
        except Exception as e:
            logger.error("ACL apply failed. %s -> %s, %s, %s\n%s:%s" % (
                path, acl.userName, perm, mode, e.__class__.__name__, e))
            raise

    def GetAcl(self, path, recursive):
        """ Retrieves and returns ACLs for a path"""
        if recursive and (not os.path.isdir(path)):
            raise Exception(
                "GetAcl: Not a directory: %s. Retrieving recursive ACLs is only supported on directory." % path)
        return ACL(None, None, None, self._cache).Get(path, recursive)

    def RemoveAcl(self, path, userPrefix, userIdx, mode=None):
        """ Removes ACL from the path specified, throws exception otherwise """
        try:
            acl = ACL(userPrefix, userIdx, None)
            acl.Remove(path, mode)
            return 0
        except Exception as e:
            logger.error("ACL remove failed. %s -> %s, %s\n%s: %s" % (
                path, acl.userName, mode, e.__class__.__name__, e))
            raise

    def ChangeInheritance(self, path, opCode):
        """ Changes inheritance for the path specified, throws exception otherwise """
        try:
            acl = ACL(None, None, None)
            acl.ChangeInheritance(path, opCode.lower())
            return 0
        except Exception as e:
            logger.error("Changing ACL inheritance for '%s' type of change failed. %s\n%s:%s" % (
            opCode, path, e.__class__.__name__, e))
            raise

    def ValidateAcl(self, path, userPrefix, userIdx, perm, vType, aclMapsId):
        """ Validates ACL on the path specified, throws exception otherwise """
        try:
            acl = ACL(userPrefix, userIdx, perm, self._cache)
            acl.Validate(path, vType, aclMapsId)
            return 0
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb = repr(traceback.format_tb(exc_traceback))
            logger.error('tb: %s' % tb)
            raise Exception("ValidateAcl: ACL validation failed. %s -> %s, %s, %s\n%s:%s" % (
            path, acl.userName, perm, vType, e.__class__.__name__, e))

    def ValidatePathExists(self, path, vType=1, retryCnt=1, sleepTime=10):
        if vType == 0:
            return self.CheckNotExists(path, retryCnt, sleepTime)
        elif vType == 1:
            return self.CheckExists(path, retryCnt, sleepTime)
        else:
            raise Exception('ValidatePathExists: Unsupported validation type %d' % vType)

    def GetDirListing(self, dirlist, vType, list_flag=True):
        """
        Get directory listing for all directories in dirlist
        :param filelist: List of files in full path that exists in filesystem
        :param vType: Supported vType is 1 for exists and 0 for not exists
        :param list_flag: Set this flag to list directory content
        :return: Returns a list of files from dirlist with each directory name as key
        """
        logger.info("dirlist %s vType %s list_flag %s" % \
                       (dirlist, vType, list_flag))
        dset = set([fpath[:fpath.rindex('\\')] for fpath in dirlist])
        logger.info("dset %s" % dset)
        dlisting = {}
        for dname in dset:
            retcode = self.ValidatePathExists(dname, vType)
            if retcode == 0:
                if list_flag:
                    dlist = os.listdir(dname)
                    logger.info("dname: %s dlist %s" % (dname, dlist))
                    dlisting[dname] = dlist
                else:
                    logger.info("dname: %s exist retcode %s" % \
                                   (dname, retcode))
                    # Expect path exists
                logger.info("dname: %s not exist retcode %s" % \
                               (dname, retcode))
        return dlisting

    def ValidateAllPathExists(self, filelist, vType=1):
        """
        Validates all paths in filelist exists
        :param filelist: List of files in full path that exists in filesystem
        :param vType: Supported vType is 1 for exists and 0 for not exists
        Return Value:
        0     - In case of success
        1     - In case of Error
        """
        found_cnt = 0
        error_list = []
        for filename in filelist:
            try:
                logger.info("filename: %s vType %s" % (filename, vType))
                retcode = self.ValidatePathExists(filename, vType)
                if retcode == 0 and vType == 1:
                    # Expect path exists
                    found_cnt += 1
                elif retcode == 0 and vType == 0:
                    # Expect path not exists
                    found_cnt += 1
                elif vType == 1:
                    # Should not get here
                    error_list.append(filename)
                    logger.info("error filename %s retcode %s" % \
                                   (filename, retcode))
            except Exception as e:
                error_list.append(filename)
                logger.info("error filename %s error %s" % \
                               (filename, str(e)))
        logger.info("found_cnt %s len filelist %s error_list %s" % \
                       (found_cnt, len(filelist), error_list))
        if found_cnt == len(filelist):
            return 0
        else:
            # Get directory list for each directory
            dlisting = self.GetDirListing(error_list, 1)
            raise Exception("ValidateAllPathExists error cnt %s errorlst %s dlisting %s" % \
                            (len(error_list), error_list, dlisting))

    def getPathDepth(self, path, startFrom=None):
        """
        # Returns depth of dir or file path
        # param path: File or dirpath whose depth to be returned
        # param startFrom: If None returns absolute depth else relative to startFrom
        """
        if os.name != 'nt':
            raise Exception('Not implemented for Unix platform.')

        if startFrom is None:
            return (len(path.split('\\')) - 1)  # Subtract 1 as drive letter is also counted
        else:
            return len(path.split('\\')) - len(startFrom.split('\\'))


# ======================
# Dir
# ======================
class IDir(IPath):
    """
    This class represents a Directory which may or may not exist
    """

    def __init__(self, cache=None):
        IPath.__init__(self, cache)

    def CheckExists(self, context, path):
        if not os.path.isdir(path):
            raise Exception('dir %s does not exist.' % path)

        return IPath().CheckExists(path)

    def CreateDirs(self, path, subdirs, directory_name="dname"):
        """
        Create a number of directories in directory located in path
        :param path: Path to the directory to create the sub-directories
        :parma subdirs: Number of sub-directories to create
        :parma directory_name: Prefix name of sub-directory to be created
        """
        dlist = []
        for index in range(subdirs):
            dname = os.path.join(path, "%s_%s" % (directory_name, index))
            self.Create(dname)
            dlist.append(dname)
        return dlist

    def Create(self, path, dir=None, depth=0, recursive=True, fail_if_exists=True):
        logger.info('path=%s' % path)
        if depth == 0:
            self.__Create(path, recursive, fail_if_exists)
        else:
            if path == None or path == '' or dir == None:
                raise Exception('Failed in create dir. Path or dir name is empty')

            while depth > 0:
                path = os.path.join(path, dir)
                depth = depth - 1
            self.__Create(path, True, fail_if_exists)
        return 0

    def __Create(self, path, recursive=True, fail_if_exists=True):
        try:
            if path == None or path == '' or os.path.isdir(path):
                return
            parent = os.path.dirname(path)

            # The parent of "Y:" is "Y:" itself. Handle this
            if parent == path:
                return
            if recursive and not os.path.isdir(parent):
                self.__Create(parent, recursive, fail_if_exists)
            os.mkdir(path)

        except OSError as e:
            if not fail_if_exists and str(e).startswith("[Error 183]"):
                return
            logger.error('Failed to create dir %s\n%s: %s' % (path, type(e).__name__, e))
            raise

    def List(self, path, incDir=True, recursive=True, inCache=False):
        if inCache:
            return self._ListInCache(path, incDir, recursive)
        else:
            return self._List(path, incDir, recursive)

    def _List(self, path, incDir, recursive):
        return self.__FindFiles(path, incDir, recursive)

    def _ListInCache(self, path, incDir, recursive):
        listData = self.__FindFiles(path, incDir, recursive)
        listDataId = '%s' % uuid4()
        self._cache.Set(listDataId, listData)
        return listDataId

    def Delete(self, path, recursive=False):
        self.__Delete(path, recursive)
        return 0

    def Delete_Directories(self, dirlist):
        """
        Delete a list of directories
        :param dirlist: A list of directories to be deleted
        :return: 0, 1
        """
        for dirpath in dirlist:
            logger.info('dirpath %s' % (dirpath))
            ret = self.Delete(dirpath, recursive=True)
            if ret != 0:
                logger.warning('error dirpath %s ret %s' % (dirpath, ret))
                return 1
        return 0

    def __Delete(self, dirPath, recursive=True):
        try:
            if not os.path.isdir(dirPath):
                return

            # Delete files under the dir first
            if recursive:
                for name in os.listdir(dirPath):
                    p = os.path.join(dirPath, name)
                    if os.path.isdir(p):
                        self.__Delete(p, True)
                        continue
                    IFile().Delete(p)
            os.rmdir(dirPath)

        except Exception as e:
            logger.error('Failed to delete dir %s\n%s: %s' % (dirPath, e.__class__.__name__, e))
            raise

    # Find files with specified pattern inside Directory
    def __FindFiles(self, path, incDir, recursive):
        files = []

        if path == None:
            return files

        if os.path.isfile(path):
            files.append(path)
            return files

        if not os.path.isdir(path):
            raise Exception('Dir: FindFiles: Directory %s does not exist' % path)

        for e in os.listdir(path):
            p = os.path.join(path, e)
            if os.path.isdir(p):
                if incDir == True:
                    files.append(p)
                if recursive:
                    files.extend(self.__FindFiles(p, incDir, recursive))
                continue
            files.append(p)
        return files

    def GetRandomPath(self, path, dir, dirDepth):
        if path == None or path == '' or dir == None or dir == '' or dirDepth == 0:
            raise Exception('GetRandomPath: path, dir or dir depth is empty')

        depth = random.randint(1, dirDepth)
        while depth > 0:
            path = os.path.join(path, dir)
            depth = depth - 1

        return path

    def Copy(self, srcPath, dstPath):
        if srcPath == None or srcPath == '' or dstPath == None or dstPath == '':
            raise Exception('Copy: source path or destination path is empty')
        if platform.system() == "Darwin":
            return MacCmd().CopyDir(srcPath, dstPath)
        else:
            return DosCmd().CopyDir(srcPath, dstPath)


# ======================
# File
# ======================
class IFile(IPath):
    def __init__(self, cache=None):
        IPath.__init__(self, cache)

    def Create(self, path, size, data, mode, blockSize=65536):
        """
        Interface method for creating a file in a recursive or non-recursive methods
        :param path: Path of a file to be created
        :param data: Data to be written into file
        :param size: Size of the file in bytes
        :param blockSize: Data will be written in file in chunks of block size buffers
        """
        recursiveWrites = False
        if data is not None and len(data) < size:
            recursiveWrites = True
        return self._Create(path, size, data, recursive=recursiveWrites, mode=mode)

    def CreateFiles(self, path, fname, ncnt, size, ext, data=None, mode="rw"):
        """
        Create a number of files on client in the path directory.
        The data is randomly generated if data is not passed in.
        :param path: Directory path
        :param fname: Name used as the leading part to create the file if pass in as string.
                      If pass in as list, then create file using each entry.
        :param ncnt: Number of files to create
        :param size: Size in MB
        :param ext: Supported extension such as txt and dat
        :param data: The data is randomly generated if not passed in
        :param mode: Supported mode is 'r' or 'rw'
        Returns the list of files in full path created
        """
        filelist = []
        errorfiles = []
        logger.info("path %s fname %s ncnt %s size %s mode %s" % \
                       (path, fname, ncnt, size, mode))
        try:
            ncnt = int(ncnt)
            size = int(size)
        except ValueError as e:
            logger.warning("ncnt %s size %s" % (ncnt, size))
            raise
        if ncnt <= 0:
            raise Exception("CreateFiles ncnt %s must be > than 0" % ncnt)
        if size <= 0:
            raise Exception("CreateFiles size %s must be > than 0" % size)
        for i in range(ncnt):
            random_num = random.randint(150, sys.maxint)
            if type(fname) == list:
                filepath = fname[i]
            else:
                filename = "%s_%s.%s" % (fname, random_num, ext)
                filepath = os.path.join(path, filename)
            retcode = self.Create(filepath, size, data, mode)
            if retcode == 0:
                logger.info("created index %s filepath %s" % (i, filepath))
                filelist.append(filepath)
            else:
                logger.warning("error index %s filepath %s" % (i, filepath))
                errorfiles.append(filepath)
        logger.info("filelist %s" % (filelist))
        if len(errorfiles):
            raise Exception("error in creating files %s" % (errorfiles))
        return filelist

    def CreateFilesDeep(self, path, dir_name, levels, fname, ncnt, size, ext, data=None, mode="rw", subdirs=None,
                        subdirname="dname"):
        """
        Create directories at the specified levels deep and in each directory create ncnt number of files
        :param path: Path to base directory
        :param dir_name: Name prefix for directory
        :param levels: Number of levels of directory to create
        :param fname: Name prefix for filename
        :param ncnt: Number of files to create
        :param size: Size of files in bytes
        :param ext: File extension name
        :param data: The data to generate. If none then randomly generate size bytes.
        :param mode: Supported mode or 'r' and 'rw'
        :param subdirs: Number of sub-directories to create at each level
        :param subdirname: Name of the prefix in sub-directories
        :return: Returns the list of files created
        """
        orig_path = path
        filelist = []
        directory_name = path
        logger.info(
            "path %s dir_name %s level %s fname %s ncnt %s size %s ext %s data %s mode %s subdirs %s subdirname %s" % \
            (path, dir_name, levels, fname, ncnt, size, ext, data, mode, subdirs, subdirname))
        for level in range(levels):
            directory_name = "%s_%s" % (dir_name, level)
            dname = os.path.join(path, directory_name)
            logger.info("dname %s" % (dname))
            # Create the directory is not already exists
            if not os.path.exists(dname):
                IDir().Create(dname)
            if ncnt:
                flist = self.CreateFiles(dname, fname, ncnt, size, ext, data, mode)
                filelist.append(flist)
            if subdirs:
                subdirslist = IDir().CreateDirs(dname, subdirs, subdirname)
            path = dname
        logger.info("path %s" % filelist)
        if filelist:
            filelist = list(self._flatten(filelist))
        if subdirs:
            subdirslist = list(self._flatten(subdirslist))
            return filelist, subdirslist
        else:
            return filelist

    def _flatten(self, items, ignore_types=(str, bytes)):
        """
        Flatten a multi-level deep list into a single level list
        :param path: The path name of a multi-level deep list
        :param ignore_types: Ignore strings and bytes
        :return: Returns a single level list
        """
        for x in items:
            if isinstance(x, Iterable) and not isinstance(x, ignore_types):
                for y in self._flatten(x, ignore_types):
                    yield y
            else:
                yield x

    def _Create(self, path, size, data, recursive, mode, blockSize=65536):
        """
        Create file (new) of given size
        :param path: Path of file to be created
        :param data: Contents to be written into file. If None, random data is written
        :param size: size of file to be created
        :param recursive: Passed by self.Create()
        :param mode: mode of file to be created
        :param blockSize: Data will be written in file in chunks of block size buffers
        """
        if mode.lower() == "r":
            mode = stat.S_IREAD
        elif mode.lower() == "rw":
            mode = stat.S_IWRITE | stat.S_IREAD
        length = 80  # Length of a line
        if data is None:
            if size <= length:
                buf = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(size))
            else:
                buf = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))
                recursive = True
        else:
            buf = data
        try:
            logger.info('file=%s size=%d recursive=%s  mode=%s' % (path, size, recursive, mode))
            fd = os.open(path, os.O_WRONLY | os.O_CREAT)
            if recursive is False:
                buf = buf[0:size]  # Truncate data to the size if length of data is more than file size
                cnt = os.write(fd, buf)
                logger.info("cnt %s recursive %s" % (cnt, recursive))
            else:
                self._WriteRecursive(fd, buf, size, blockSize)
            try:
                os.close(fd)
            except OSError as e:
                logger.warning("close file error %s recursive %s" % (str(e), recursive))
            root, ext = os.path.splitext(path)
            logger.info('root=%s ext=%s' % (root, ext))
            if ext != '.slog':  # slog file is handled differently and is not available for read immediately
                self.CheckExists(path)
            if mode is not None and ext != '.slog':
                os.chmod(path, mode)
            return 0
        except Exception as e:
            logger.error("Failed to create file %s\n%s: %s" % (path, type(e).__name__, e))
            raise

    def _WriteRecursive(self, fd, data, size, blockSize=65536):
        """
        Writes data into a file until it's of size
        param fd:   File description of a file opened for write
        param data: String to be used for formulating a line
        param size: Intended file size in bytes
        param blockSize: Block size. Data will be written into file in chunks of block size.
        """
        numBytesWritten = 0
        blockSize = size if size < blockSize else blockSize
        while size > numBytesWritten:
            os.write(fd, self._GetChunk(data, blockSize))
            numBytesWritten += blockSize
            if size - numBytesWritten < blockSize:
                blockSize = size - numBytesWritten
        return 0

    def _GetChunk(self, data, size, length=80):
        """
        Returns a string buffer of specified size by repeating 'data'
        :param data: String to be used for constructing chunk of data
        :param size: Chunk size
        :param length: Length of a line
        """
        line = self._GetLine(data, length)
        lineCount = size / length
        lineList = []
        if lineCount > 0:
            for i in range(lineCount):
                lineList.append(line)
            remainder = size % (lineCount * length)
            lineList.append(line[0:remainder])
            data = ''.join(lineList)
            return data
        else:
            return (line[0:size])

    def _GetLine(self, data, length=80):
        """
        Returns a line of length by repeating 'data'
        :param data: String to be used for formulating a line
        :param length: Length of a line
        """
        dataLength = len(data)
        remainder = length % dataLength
        EOLCharCount = 1
        if os.name == 'nt':
            EOLCharCount = 2  # Windows use #2 chars '\r\n' for EOL
        if remainder > 0:
            return data * (length / dataLength) + data[0:remainder - EOLCharCount] + '\n'
        else:
            # When remainder is 0, strip last character in line and then add '\n'
            line = data * (length / dataLength)
            return line[0:-EOLCharCount] + '\n'

    def Open(self, path, flag=os.O_RDWR):
        """
        Opens the file and keeps it open.
        :param path: Path of file
        :param flag: open flags
        """
        try:
            logger.info('path=%s flag=%s' % (path, flag))
            return os.open(path, flag)
        except Exception as e:
            logger.error('File: Failed to open file %s\n%s: %s' % (path, type(e).__name__, e))
            raise

    def Close(self, path, fd):
        """
        Closes the given file if previously opened
        :param path: Path of file
        :param fd: file descriptor
        """
        try:
            logger.info('path=%s fd=%s' % (path, fd))
            os.close(fd)
            return 0
        except Exception as e:
            logger.error('File: Failed to close file %s\n%s: %s' % (path, type(e).__name__, e))
            raise

    def Touch(self, path):
        """
        Touch the given file
        :param path: Path of file
        """
        fd = self.Open(path)
        self.Close(path, fd)
        return 0

    def TouchFiles(self, filelist, delay):
        """
        Touch all the files in filelist
        :param filelist: List of files to select from
        :return: 0, 1
        """
        logger.info('filelist %s' % (filelist))
        if delay:
            time.sleep(int(delay))
        if filelist is None or len(filelist) == 0:
            logger.warning('error filelist :%s:' % (filelist))
            return 1
        for filepath in filelist:
            logger.info('file %s' % (filepath))
            ret = self.Touch(filepath)
            if ret != 0:
                logger.warning('error file %s ret %s' % (filepath, ret))
                return 1
        return 0

    def TouchRandomFiles(self, filelist, cnt, seed):
        """
        Touch the file based on random selection from filelist.
        :param filelist: List of files to select from
        :param cnt: Number of times to perform the Touch operation
        :param seed: The seed used in random generation
        :return: 0, 1
        """
        logger.info('filelist %s cnt %s seed %s' % (filelist, cnt, seed))
        if filelist is None or len(filelist) == 0:
            logger.warning('error filelist :%s:' % (filelist))
            return 1
        try:
            cnt = int(cnt)
            seed = int(seed)
        except ValueError as e:
            logger.warning('error %s seed %s' % (cnt, seed))
            return 1
        # Seed the random number generator
        random_files = random.Random(seed)
        for i in range(cnt):
            rfile = random_files.choice(filelist)
            logger.info('i %s rfile %s' % (i, rfile))
            ret = self.Touch(rfile)
            if ret != 0:
                logger.warning('error i %s rfile %s ret %s' % (i, rfile, ret))
                return 1
        return 0

    def ValidateSize(self, path, size):
        """
        Validates the size of given file
        :param path: Path of file
        :param size: size
        """
        try:
            logger.info('path=%s size=%d' % (path, size))
            stat = self.Stat(path)
        except Exception as e:
            logger.error('Failed to stat. file=%s\n%s: %s' % (path, type(e).__name__, e))
            raise
        if stat.st_size != size:
            raise Exception('ValidateSize: Failed. Actual=%s Expected=%s' % (stat.st_size, size))

        return 0

    def ValidateAnySize(self, size, filelist):
        """
        Verify whether any files has size bytes
        :param size: Size in bytes to check the file against with
        :param filelist: List of files to check
        :return: Returns 0 if any files has size bytes else 1
        """
        found_cnt = 0
        for filename in filelist:
            logger.info("filename: %s size %s" % (filename, size))
            stat = self.Stat(filename)
            if stat.st_size == size:
                logger.info("FOUND filename: %s stat.st_size %s stat %s" % (filename, stat.st_size, pformat(stat)))
                found_cnt += 1
        if found_cnt:
            return 0
        else:
            return 1

    def Stat(self, path):
        """
        Stat the given file
        :param path: Path of file
        """
        return os.lstat(path)

    def Write(self, path, data=None, size=64, offset=0):
        """
        Writes to file.
        Data is written to the file pointed by path
        :param path: Path of file
        :param data: data to be written to the file
        :param size: size of data to be written
        :param offset: offset at which to write data
        :return: 0 for success else exception
        """
        logger.info('file=%s size=%s offset=%d' % (path, size, offset))
        fd = os.open(path, os.O_RDWR)
        result = self.FdWrite(fd, data, size, offset)
        os.close(fd)
        return result

    def FdWrite(self, fd, data=None, size=64, offset=0):
        """
        Writes to file.
        :param fd: file descriptor
        :param data: data to be written to the file. If None, data is generated.
        :param size: size of data to be written
        :param offset: offset at which to write data
        :return: 0 for success else exception
        """
        if data is None:
            data = os.urandom(size)
        try:
            # Write with retry logic. TODO - handle bytes
            ex, retry = None, 2
            while retry > 0:
                try:
                    os.lseek(fd, offset, os.SEEK_SET)
                    os.write(fd, data)
                    break
                except OSError as e:
                    if e.errno != 13:
                        raise e
                    ex, retry = e, retry - 1
                    continue
            if retry == 0:
                raise ex
        except Exception as e:
            logger.error('Failed for fd=%d\n%s: %s' % (fd, type(e).__name__, e))
            raise
        return 0

    def WriteFiles(self, fileList, size=64, offset=0, data=None):
        """
        Write to all the files in fileList
        :param fileList: List of files to write
        :param size: size of data to be written
        :param offset: offset at which to write data
        :param data: data to be written to the file
        :return: 0 for success else exception
        """
        logger.info('fileList %s' % (fileList))
        if fileList is None or len(fileList) == 0:
            logger.warning('error fileList :%s:' % (fileList))
            raise Exception('IFile: WriteFiles: error fileList %s' % fileList)
        for filepath in fileList:
            logger.info('Writing data to file %s of size=%d at offset=%d' % (filepath, size, offset))
            result = self.Write(filepath, data, size, offset)
        return result

    def Read(self, path, size=64, offset=0):
        """
        Read data from the file.
        :param path: Path of file
        :param size: size of data to be read
        :param offset: offset at which to read data from
        :return: data for success else exception
        """
        logger.info('file=%s size=%s offset=%d' % (path, size, offset))
        if size == 0 and offset == 0:
            size = self.Stat(path).st_size
        fd = os.open(path, os.O_RDONLY)
        data = self.FdRead(fd, size, offset)
        os.close(fd)
        if data:
            logger.info('file=%s, data=%s' % (path, data))
            return data
        else:
            logger.info('Reached end of file %s' % path)
            return None

    def FdRead(self, fd, size=64, offset=0):
        """
        Read from file.
        :param fd: file descriptor
        :param size: size of data to be read
        :param offset: offset at which to read data from
        :return: data for success else exception
        """
        data = None
        try:
            # Read with retry logic.
            ex, retry = None, 2
            while retry > 0:
                try:
                    os.lseek(fd, offset, os.SEEK_SET)
                    data = os.read(fd, size)
                    break
                except OSError as e:
                    if e.errno != 13:
                        raise e
                    ex, retry = e, retry - 1
                    continue
            if retry == 0:
                raise ex
        except Exception as e:
            logger.error('Failed for fd=%d, size=%d, offset=%d\n%s: %s' % (fd, size, offset, type(e).__name__, e))
            raise
        return data

    def Copy(self, filePath, newFilePath, retry=1):
        """
        Copies the file to the given path.
        Supports source file name with wildcard characters.
        :param filePath: source file path
        :param newFilePath: destination file path
        """
        logger.info('path=%s newPath=%s' % (filePath, newFilePath))
        try:
            for file in iglob(filePath):
                logger.info('Source file=%s' % file)
                for i in range(retry):
                    try:
                        shutil.copy(file, newFilePath)
                        break
                    except IOError as e:
                        # retry if file is being used by another process
                        if e.errno != errno.EACCES or i >= retry - 1:
                            logger.error('Failed to copy file %s after %d retries' % (file, i))
                            raise
                        logger.info('Retrying file %s copy. Attempt %d' % (file, i + 1))
                        time.sleep(2)
                        continue
        except Exception as e:
            logger.error('Cant copy %s to %s\n%s: %s' % (filePath, newFilePath, type(e).__name__, e))
            raise
        return 0

    def Delete(self, path):
        """
        This interface Deletes the given file.
        * If delete fails with sharing violation error (errno=13), then retry the operation.
        * If error is other than sharing violation, exception is raised normally.
        * If operation continues to fail after no of retries, raises exception appropriately.
        :param path: Path of file
        """
        ex, retry = None, 5
        i = retry
        while i > 0:
            i = i - 1
            try:
                if os.path.exists(path):
                    os.remove(path)
                    root, ext = os.path.splitext(path)
                    logger.info('root=%s ext=%s' % (root, ext))
                    if ext != '.slog':  # To bypass windows cache, adding retry for .slog files
                        IPath().CheckNotExists(path)
                    else:
                        IPath().CheckNotExists(path, retry_cnt=3)
                break
            except OSError as e:
                if (e.errno != 13):
                    logger.error('Failed file=%s\n%s: %s' % (path, type(e).__name__, e))
                    raise
                ex = e
                # If a 'Read Only' bit is set, clear it and then try os.remove()
                os.chmod(path, stat.S_IWRITE)
                continue
            except Exception as e:
                logger.error('Failed file=%s\n%s: %s' % (path, type(e).__name__, e))
                raise

        if i == 0:
            raise Exception(
                'IFile: Delete failed for %s after #%d retries\n%s: %s' % (path, retry, type(ex).__name__, ex))
        return 0

    def DeleteFiles(self, fileList):
        """
        This interface Deletes the list of input files.
        :param fileList: list of files to be deleted
        """
        logger.info('Deleting fileList %s' % fileList)
        if fileList == None or len(fileList) == 0:
            raise Exception('error fileList %s' % fileList)
        retcodes = 0
        for file in fileList:
            logger.info('Deleting file %s' % file)
            retcode = self.Delete(file)
            retcodes += retcode
        if retcodes > 0:
            return 1
        else:
            return 0

    def Extend(self, path, size, data=None):
        """
        Extends the current file, seek to size and writes a byte
        Caller needs to make sure size > current file size
        :param path: Path of file
        :param size: size to seek to and write a byte
        """
        if data is None:
            data = os.urandom(1)
        dataLen = len(data)
        try:
            logger.info('path=%s size=%s' % (path, size))
            fd = os.open(path, os.O_RDWR)
            os.lseek(fd, size - dataLen, os.SEEK_SET)
            os.write(fd, data)
            os.close(fd)
        except Exception as e:
            logger.error('Cant extend file %s by size %d\n%s: %s' % (path, size, type(e).__name__, e))
            raise
        return 0

    def Truncate(self, path, size):
        """
        Reset size of the specified file to desired size
        :param path: Path of file
        :param size: desired file size
        """
        try:
            fd = open(path, 'r+b')
            os.lseek(fd.fileno(), size, 0)
            fd.truncate()
            fd.close()
            return 0
        except Exception as e:
            logger.error("Failed to Truncate File %s\n:%s: %s" % (path, type(e).__name__, e))
            raise

    def Compare(self, srcPath, dstPath):
        """
        Compare source and destination file.
        :param srcPath: Source file to be compared
        :param dstPath: Destination file to be compared
        """
        try:
            if srcPath == None or srcPath == '' or dstPath == None or dstPath == '':
                raise Exception("IFile: Compare failed. %s -> %s\nEither source or destination path are not set." % (
                Exception.__class__.__name__, Exception))
            if filecmp.cmp(srcPath, dstPath):
                return 0
            else:
                raise Exception("IFile: Compare failed. %s -> %s \n%s:%s" % (
                srcPath, dstPath, Exception.__class__.__name__, Exception))
        except Exception as e:
            logger.error("Compare failed. %s -> %s \n%s:%s" % (srcPath, dstPath, e.__class__.__name__, e))
            raise

    def _GetHasher(self, hashType):
        """
        Creates a hasher of a given hashType
        :param hashType: A hashing algorithm like 'MD5'
        """
        if hashType == 'MD5':
            return hashlib.md5()
        else:
            raise Exception('_GetHasher: Unsupported file hashing library %s' % hashType)

    def _GetHashValue(self, path, hasher, blockSize, hexDigest):
        """
        Returns a hash value of a file
        :param path: A path to a file whose hash value is to be calculated
        :param hasher: A hashing function
        :param blockSize: Size of the block to be read
        :param hexDigest: Boolean flag which decides the format of HASH value of a file
        """
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(blockSize), b''):
                hasher.update(chunk)

            if not hexDigest:
                return hasher.digest()
            return hasher.hexdigest()

    def GetMD5Checksum(self, path, blockSize=256 * 128, hexDigest=True):
        """
        Returns a MD5 checksum of a file
        :param path:      A file path whose MD5 checksum will be calculated
        :param blockSize: A block size to read file chunk by chunk
        :param hexDigest: Boolean flag set to True to return Hash value in HEX character set
        """
        hasher = self._GetHasher('MD5')
        return self._GetHashValue(path, hasher, blockSize, hexDigest)

    def GetMD5ChecksumList(self, fileList, blockSize=256 * 128, hexDigest=True):
        """
        Returns a MD5 checksum of list of files
        :param fileList: List of file paths whose MD5 checksum will be calculated
        :param blockSize: A block size to read file chunk by chunk
        :param hexDigest: Boolean flag set to True to return Hash value in HEX character set
        """
        logger.info('fileList=%s' % fileList)
        md5ChecksumList = []
        for fileName in fileList:
            md5Checksum = self.GetMD5Checksum(fileName, blockSize, hexDigest)
            md5ChecksumList.append(md5Checksum)
        return md5ChecksumList

    def ValidateData(self, path, data, vType='MD5'):
        """
        Validates content of the file
        :param path: A file whose contents needs to be validated
        :param data: Reference provided for doing validations
                    When -
                        vType is 'MD5', data is MD5Checksum of reference file
                        vType is 'data', data is path to a reference file
        """
        if vType == 'MD5':
            return self.CompareMD5Checksum(path, data)
        elif vType == 'data':
            return self.Compare(path, data)
        else:
            raise Exception('IFile: ValidateData: Unsupported validation type %s' % vType)

    def ValidateDataList(self, fileList, dataList, vType='MD5'):
        """
        Validates content of list of files
        :param fileList: List of files whose contents needs to be validated
        :param dataList: Reference provided for doing validations
                    When -
                        vType is 'MD5', dataList is MD5Checksum of reference files
                        vType is 'data', dataList is path to reference files
        """
        logger.info('fileList=%s, dataList=%s' % (fileList, dataList))
        for i in range(len(fileList)):
            self.ValidateData(fileList[i], dataList[i], vType)
        return 0

    def ValidateSizeList(self, fileList, sizeList):
        """
        Validates the size of list of files
        :param fileList: List of file paths
        :param sizeList: List of file size
        """
        logger.info('fileList=%s, sizeList=%s' % (fileList, sizeList))
        for i in range(len(fileList)):
            self.ValidateSize(fileList[i], int(sizeList[i]))
        return 0

    def CompareMD5Checksum(self, path, md5Checksum):
        """
        Validates if MD5 checksum of a path is same as referenceMD5
        :param path:          A filepath whose MD5 checksum will be calcualated
        :param referenceMD5:  Reference value of MD5 checksum
        """
        pathMD5Checksum = self.GetMD5Checksum(path)
        if md5Checksum == pathMD5Checksum:
            return 0
        else:
            raise Exception(
                'IFile: CompareMD5Checksum failed for [%s]. Calculated MD5 [%s] is not same as reference MD5 [%s]' % (
                path, pathMD5Checksum, md5Checksum))

    def SetOwner(self, path, owner):
        """
        # Changes ownership of a file or folder
        # param path:     File/Directory path whose owner has to be changed
        # param owner:    Owner to be set
        """
        logger.info('path=%s owner=%s' % (path, owner))
        if not os.path.isfile(path):
            raise Exception('Error: %s is not a file' % (path))
        return ACL().SetOwner(path, owner)

    def ValidateOwner(self, path, owner):
        """
        # Validates if owner of an object at path is same as 'owner'
        # param path:  File/Directory path owner who ownership has to be evaluated
        # param owner: To be compared against owner value of path
        """
        logger.info('path=%s owner=%s' % (path, owner))

        if not os.path.isfile(path):
            raise Exception('Error: %s is not a file' % (path))

        acl = ACL()
        ownerFound = acl.GetOwner(path)

        # Get owners into DOMAIN\\user format from domain.com\\user or domain\\user
        ownerFound = acl._parseUserName(ownerFound)
        owner = acl._parseUserName(owner)

        if owner != ownerFound:
            raise Exception('IFile: ValidateOwner: Difference in file owner for [%s]. Expected[%s], Actual[%s]' % (
            path, owner, ownerFound))

        return 0

    def GetLines(self, filename):
        """
        Get specified line from given file
        param filename: file name
        """
        logger.info('filename %s' % filename)

        listlines = [line.rstrip('\n') for line in open("%s" % filename).readlines()]
        return listlines

    def VerifyData(self, path, inData, size=64, offset=0):
        """
        Verify data in the file matches input data.
        :param path: file path
        :param inData: input data
        :param size: size of data to be read
        :param offset: offset at which to read data from
        :return: 0 for success else exception
        """
        logger.info('file=%s size=%s offset=%d' % (path, size, offset))
        if path == None or size <= 0 or offset < 0:
            raise Exception('IFile: VerifyData: Invalid input parameter.')
        outData = self.Read(path, size, offset)
        if outData != inData:
            raise Exception('IFile: VerifyData: Data verification for file %s failed.' % path)
        return 0

    def ValidateExists(self, path, vType=1, fType=1):
        """
        Validate file path existence.
        This method has been added to workaround SMB2 client redirector cache specifically for strong consistency files in distributed environment.
        For normal consistency file existence check, existing ValidatePathExists in IPath class should be called.
        SMB2 client redirector maintains a directory cache. Default timeout value for this cache is 10 seconds.
        Python os.path.exists method looks up directory cache to check for file existence and makes a call to
        Samba server only if the file does not exist in the cache.
        This cache affects strong consistency file existence check as file delete event does not reflect on the client till the cache expires.
        This method bypasses SMB2 directory cache by making a call to the SAMBA server to check existence of a file.
        :param path: file path
        :param vType: 0 - Check file does not exist, 1 - Check file exists (default).
        :param fType: 0 - file is normal consistency file, 1 - file is a strong consistency file (default).
        :return: 0 for success else 1
        """
        if path == None or (vType or fType) not in [0, 1]:
            raise Exception('IFile: ValidateExists: Invalid input parameter.')
        # For normal consistency file exists and does not exist check and strong consitency file exists check use existing ValidatePathExists method in IPath
        if fType == 0 or (fType == 1 and vType == 1):
            return self.ValidatePathExists(path, vType)
        elif fType == 1 and vType == 0:
            try:
                fd = os.open(path, os.O_RDONLY)
                os.close(fd)
            except OSError as e:
                if (e.errno == 2):
                    logger.info('file=%s does not exist' % path)
                    return 0
                logger.info('Error opening file %s.\n%s: %s' % (path, type(e).__name__, e))
            return 1


# ======================
# ACL
# ======================
class ACL(Base):
    """
    Represents ACL to be applied to a path
    """

    def __init__(self, userPrefix=None, userIdx=None, perm=None, cache=None):
        self._cache = cache
        self.userName = ''
        if userPrefix is not None:
            self.userName = userPrefix if userIdx is None else userPrefix + str(userIdx)
        self.perm = perm
        self.corePerm = perm  # This will contain 'permission - inheritance flags'
        self._cmd = DosCmd()
        self._ipath = IPath()
        self._idir = IDir()

    def __str__(self):
        _str = '' if self.perm is None else self.perm
        _str += ': '
        _str += '' if self.userName is None else self.userName
        return _str

    def Get(self, path, recursive=False):
        """
        Get ACL set on the specified path
        :param path: Path on which ACL ops will be performed.
        :param recursive: True if to do recursive collection of ACLs
        """
        if recursive:
            aclMapsId = '%s' % uuid4()
            logger.info('cache: %s' % self._cache)
            aclMaps = {}
            entries = []
            entries.append(path)  # Start with root of a directory tree
            entries.extend(self._idir.List(path, True, True))

            for entry in entries:
                aclMaps[entry] = self._Get(entry)
            self._cache.Set(aclMapsId, aclMaps)
            return aclMapsId
        else:
            return self._Get(path)

    def _Get(self, path):
        """
        Get ACL set on the specified path
        :param path: Path on which ACL ops will be performed.
        """
        logger.info('path=%s' % path)
        aclMap = self._cmd.GetAcl(path)
        logger.info('path=%s ACLs=%s' % (path, aclMap))
        return aclMap

    def Apply(self, path, mode='grant:r'):
        """
        Set ACL on the specified path
        :param path: Path on which ACL ops will be performed.
        :param mode: Mode in which 'perm' will be set. Value can be 'grant' (to add perm), 'grant:r' (to replace existing by new one)
        :                                                           'deny' (to deny perm)
        """
        if mode not in ['grant', 'grant:r', 'deny']:
            raise Exception('ACL: SetAcl for %s mode is not supported' % mode)

        logger.info('path=%s user=%s perm=%s mode=%s' % (path, self.userName, self.perm, mode))
        output = self._cmd.SetAcl(path, self.userName, self.perm, mode)
        logger.info('path=%s result=%s' % (path, output))

    def Remove(self, path, mode=None):
        """
        Remove ACL from the specified path
        :param path: Path on which ACL ops will be performed.
        :param mode: ACL mode, value can be 'd' for 'deny', 'g' 'grant' or None to remove all ACLs
        """
        if not (mode is None or mode in ['g', 'd']):
            raise Exception('ACL: RemoveAcl for %s mode is not supported' % mode)

        logger.info('path=%s user=%s acl=%s mode=%s' % (path, self.userName, self.perm, mode))
        output = self._cmd.RemoveAcl(path, self.userName, mode)
        logger.info('path=%s result=%s' % (path, output))

    def ChangeInheritance(self, path, opCode):
        """
        Remove inherited ACL from the specified path
        :param path:     Path on which ACL ops will be performed.
        :param opCode: Supported operations are: e: enable, d: disable, r: remove
        """
        if opCode not in ['r', 'e', 'd']:
            raise Exception('ACL: ChangeInheritance for %s type opCode is not supported' % opCode)

        output = self._cmd.ChangeInheritance(path, opCode)
        logger.info('path=%s result=%s' % (path, output))

    def _parseUserName(self, userName):
        """
        Parse user names such as domain.com\\user1 or domain.inc.com\\user1 and
        construct user name as domain\\user1 (this is how the username appears in ACL list)
        For a user name like CREATOR OWNER which do not have a domain; userName as is will be returned
        :param userName:
        """

        domainName, parsedUserName = None, None
        userNameSplits = re.split(r'\\', userName)
        if len(userNameSplits) == 1:
            parsedUserName = userName  # When userName is 'CREATOR OWNER'
        else:
            domainNameSplits = re.split(r'\.', userNameSplits[0])  # split 'domain.inc.com' to get 'domain' only
            domainName = domainNameSplits[0].upper()
            parsedUserName = domainName + '\\' + userNameSplits[1]
        logger.info('Username [%s] after parsing: %s' % (userName, parsedUserName))
        return parsedUserName

    def Validate(self, path, vType=1, aclMapsId=None):
        """
        Validates ACL of a file/directory or recursively into a directory.
        :param path:      ACLs to be validated for
        :param vType:     1=Validate for existence 0=Validate for absence
        :param aclMapsId: A key in 'cache' to retrieve stored ACLs and valid value means recursive validation
        """
        if vType not in [0, 1]:
            raise Exception('ACL: Supported values for vType are 0, 1. (Given value: %d)' % (vType))

        if aclMapsId is None:
            logger.info('Validating ACLs of %s' % path)
            return self._validate(path, vType)

        if not os.path.isdir(path):
            raise Exception('ACL: %s is not directory. Recursive validation only on directory' % path)
        logger.info('Recursively validating ACLs for entries in  %s' % path)

        aclMapsPrev = self._cache.Get(aclMapsId)
        for k, v in aclMapsPrev.items():
            logger.info('Entry: %s\ncached ACLs: %s' % (k, v))

        inheritFlags = self._getInheritFlags()
        logger.info('inheritFlags: %s' % (inheritFlags))

        result = True
        entries = []
        entries.append(path)  # Start with root of a directory tree
        entries.extend(self._idir.List(path, True, True))

        for entry in entries:
            ACLInheritance = self._isACLInheritanceExpected(entry, path, inheritFlags)
            logger.info('Validating ACLs of %s when ACL inheritance is %s' % (entry, ACLInheritance))
            if ACLInheritance:
                try:
                    self._validate(entry, vType)
                except Exception as e:
                    result = False
                    logger.error('ACL validation falied for %s\nMsg: %s' % (entry, e))
            else:
                aclMap = ACL().Get(entry)
                if self._isACLSame(aclMapsPrev[entry], aclMap):
                    logger.info("ACLs of %s before and after ACL application are same" % entry)
                else:
                    result = False
                    logger.error("ACLs of %s before and after ACL application are different" % entry)

            logger.debug('ACL validation result: %s' % result)

        if result:
            return 0
        else:
            raise Exception('One or more ACL validations failed for %s' % (path))

    def _isACLSame(self, aclMapPrev, aclMapPresent):
        """
        Checks if ACL entriess before and after application of new ACL are same.
        If an ACL is applied on a root of a directory tree, then change in ACLs for
        file/folder in the tree is driven presence of inheritance flags - OI, CI, NP
        Check:
            1) Return True if:
                       both ACL entries are exactly same
                       ACL may change in string value but mean same like as in below example
                          Previous: 'PZTEST22\\test1': ['(I)(OI)(CI)(F)', '(I)(F)']
                          Present:  'PZTEST22\\test1': ['(I)(OI)(CI)(F)']
            2) Return False otherwise
        """
        logger.info("ACL map(previous): %s" % aclMapPrev)
        logger.info("ACL map(present) : %s" % aclMapPresent)
        ret = True

        if aclMapPrev == aclMapPresent:
            return True
        else:
            for aclUser in aclMapPrev.keys():
                logger.info("Verifying ACLs of user[%s] with previous[%s] and present[%s]" % (
                aclUser, aclMapPrev[aclUser], aclMapPresent[aclUser]))
                if aclMapPrev[aclUser] == aclMapPresent[aclUser]:
                    ret = True
                else:
                    # The check is to verify that aclMapPresent is a subset of aclMapPrev
                    # and its based upon observations that aclMapPrev might get consolidated
                    # after applying new ACL. To explain it, take a look at below ACLs seen
                    # before and after applying a ACL for some other user - PZTEST22\test2
                    #
                    # Before: PZTEST22\\test1: ['(I)(OI)(CI)(F)', '(I)(F)']
                    # After : PZTEST22\\test1: ['(I)(OI)(CI)(F)']
                    #
                    # In above example, ACL indicating 'full permissions' by '(F)' is present
                    # before and after applying an ACL and is still an inherited one. And so
                    # considered it to be present and so a check in this case is considered to
                    # be a success.
                    #
                    for acl in aclMapPresent[aclUser]:
                        ret = True if acl in aclMapPrev[aclUser] else False
                        if ret:
                            logger.error("ACLs before and after ACL application for %s are different" % aclUser)
                            break

        return ret

    def _validate(self, path, vType):
        """
        Validates ACL on the file.
        :param acl: ACLs to be validated for
        :param vType: 1=Validate for existence 0=Validate for absence
        """
        logger.info('path=%s vType=%d' % (path, vType))
        aclMap = self.Get(path)
        if len(aclMap.keys()) == 0:
            raise Exception('ACL: Cant obtain ACLs. path=%s' % path)

        userName = self._parseUserName(self.userName)
        if vType == 0 and userName in aclMap.keys() and self._isACLPresent(aclMap[userName]):
            raise Exception('ACL: Validation failed, path=%s Unexpected ACL=%s:%s Actual ACL=%s' % (
                path, userName, self.perm, aclMap))
        if vType == 1 and (userName not in aclMap.keys() or not self._isACLPresent(aclMap[userName])):
            raise Exception('ACL: Validation failed. path=%s Expected ACL=%s:%s Actual ACL=%s' % (
                path, userName, self.perm, aclMap))

    def _isACLPresent(self, userACLs):
        """
        Checks if self.perm is present in userACLS - which contains all ACLs for that user
        This check is done in #2 ways -
          a) self.perm is as present which will happen in case of ACLs applied without inheritance flags
          b) An user's ACLs ends with self.perm by ignoring inheritance flags as checking is done recursively
             on every entry in folder on which ACL was applied.
        """
        foundACL = False
        logger.info('perm=%s' % (self.perm))
        _permList = self._getACLPermList(self.perm)
        if _permList is not None:
            logger.info('_permList=%s' % (_permList))

        for userACL in userACLs:
            logger.info('userACL=%s' % (userACL))
            # An userACL ending with a self.perm is a success and in this case
            # inheritance flags are ignored which is fine as directory tree is
            # recursively checked for presence of ACLs.
            if self.perm == userACL or userACL.endswith(self.perm):
                foundACL = True
                break
            else:
                # This is an extreme comparison where only permissions are taken
                # out of ACL entry by dropping other flags if present and get
                # sorted permissions in ACL entry so that order in which
                # they are seen don't affect result of comparison.
                #
                # e.g.
                #     Permissions used while setting ACLs: (W,D,WDAC,X,WO,DC)
                #     Permissions seen after application : (W,D,WDAC,WO,X,DC)
                #
                _userACLpermList = self._getACLPermList(userACL)
                logger.info('_userACLpermList=%s' % (_userACLpermList))
                if _permList == _userACLpermList:
                    foundACL = True
                    break

        return foundACL

    def _getACLPermList(self, acl):
        """
        Returns a sorted list of permissions in ACL by eliminating inheritance flags.
        Input: (CI)(DENY)(W,D,WDAC,WO,X,DC)
        Returns: ['D', 'DC', 'W', 'WDAC', 'WO', 'X']]
        """
        # To take out '(W,D,WDAC,WO,X,DC)' out of '(CI)(DENY)(W,D,WDAC,WO,X,DC)'
        aclRx = re.compile(r'.*\(([^(]+)\)$')
        m = aclRx.match(acl)

        if m:
            ACLPerm = m.group(1)
            ACLPermList = ACLPerm.split(',')
            # Change permissions to upper case.
            # ACL permission 'RC' is seen as 'Rc' even if 'RC' has been specified while setting ACL.
            for idx, item in enumerate(ACLPermList):
                ACLPermList[idx] = item.upper()
            ACLPermList.sort()
            return ACLPermList
        else:
            return None

    def _isACLInheritanceExpected(self, path, startFrom, inheritFlags):
        """
        # Returns Boolean if inheritance ACL is expected on 'path' whose root is 'startFrom'
        # To make it simple, with inheritance flags, one can specify if an ACL to be applied to sub-folders, folders only or files only
        # path:         File/folder for which expectancy of an inherited ACL is to be decided
        # startFrom:    Folder on which ACL with inheritance flags is applied
        # inheritFlags: Dict. containing boolean values for 'OI', 'CI', 'IO' and 'NP' flags
        #
        # Logic below will decide on 'expectancy of inherited ACL' based upon -
        # 1) relative location of file/folder from 'startFrom'
        # 2) if it's file or folder
        # 3) Flags set in 'inheritFlags' which are interpreted as below
        #   (OI)         This folder and files
        #   (CI)         This folder and sub-folders.
        #   (OI)(CI)     This folder, sub-folders, and files.
        #   (OI)(CI)(IO) Sub-folders and files only.
        #   (CI)(IO)     Sub-folders only.
        #   (OI)(IO)     Files only.
        #
        # Absence of (NP) flag means an ACL with inheritance flag will be applied across directory tree
        # else it is applied ONLY ON entries in the directory to which it is applied.
        #
        """

        # NP: Apply ACL only to 1st/direct entries in the folder
        isNP = True if inheritFlags['NP'] else False
        # OI: ACL to be inherited by files only
        isOI = True if inheritFlags['OI'] else False
        # CI: ACL to be inherited by folders only
        isCI = True if inheritFlags['CI'] else False
        # IO: It means said ACL will not impact the folder on which it is seen but OI/CI flags present
        #     along with will indicate presence of an inherited ACL on file/folder in that folder.
        #     Meaning: When an ACL with 'IO' flag is seen on a folder; then child folder/file will have
        #     have same ACL with 'I' flag indicative inheritance.
        isIO = True if inheritFlags['IO'] else False

        isFile = True if os.path.isfile(path) else False
        isDir = True if os.path.isdir(path) else False

        depth = self._ipath.getPathDepth(path, startFrom)

        if depth == 0:
            # ACL with inheritance flags will always be seen on the folder on which it is applied
            return True

        logger.info(
            "For [%s] with root [%s]\ndepth: %d, isNP: %s, isOI: %s, isCI: %s, isIO: %s, isFile: %s, isDir: %s" % (
            path, startFrom, depth, isNP, isOI, isCI, isIO, isFile, isDir))

        if not (isOI or isCI):
            return False  # When depth => 1 and no inheritance flags present in ACLs of a parent folder
        else:
            if isNP:
                if depth == 1:
                    if isDir and isCI:
                        return True
                    if isFile and isOI:
                        return True
                if depth > 1:
                    return False
            else:
                if isOI:
                    # For propgating OI (object inheritance), ACL with IO (inheritance only) flag is applied
                    # on a folder so that files contained in that folder can inherit ACL and so return True
                    # without checking that a directory entry is a file or folder
                    return True
                if isCI:
                    if isDir:
                        return True
                    if isFile:
                        return False

        return False

    def _getInheritFlags(self):
        """
        Returns a dictionary  of inherit flags set in a path
        """
        map = {'OI': False, 'CI': False, 'IO': False, 'NP': False}
        self.corePerm = None  # Reset self.perm to None
        _perm = self.perm.upper()
        # Ignore last empty element in a string like '(OI)(CI)(RD)' to get ['OI', 'CI', 'RD'] instead of ['OI', 'CI', 'RD', '']
        for k in _perm.replace('(', '').split(')')[:-1]:
            if k in map:
                map[k] = True
            else:
                self.corePerm = k.upper()
        return map

    def SetOwner(self, path, owner):
        """
        # Set a new 'owner' to an object in 'path'
        """
        return self._cmd.SetOwner(path, owner)

    def GetOwner(self, path):
        """
        # Returns an 'owner' of an object in 'path'
        """
        return self._cmd.GetOwner(path)


# ======================
# DosAttr
# ======================
class DosAttr(Base):
    """
    This class represents DOS Attribute. (Windows Only)
    Refer to "attrib /?" to know more details about DOS attribute.

    Following operations can be performed on the file
        1. Set Attribute on a file
        2. Remove/Clear Attribute from the file

    In DOS you have following kinds of attributes (with meaning)
        R - Read-only File
        A - Archive File
        H - Hidden File
        S - System File
        I - Not Content Index File
    """
    _attrSpec = None
    _cmd = None

    def __init__(self, attrSpec=None):
        self._attrSpec = attrSpec
        self._cmd = DosCmd()

    def IGet(self, path):
        """
        Returns DOS Attributes applied to a given file
        :param path: file path
        """
        return self._cmd.GetDosAttr(path)

    def Set(self, path):
        """
        Sets current DOS Attributes on the given path
        :param path: file path
        """
        self._cmd.SetDosAttr(path, self._attrSpec)

    def ISet(self, path, attrSpec):
        """
        Sets given DOS Attributes on the given path
        :param path: file path
        :param attrSpec: Specified on or more of attribute values
        """
        self._cmd.SetDosAttr(path, attrSpec)

    def Clear(self, path):
        """
        Clears current DOS Attributes from the given path
        :param path: file path
        """
        self._cmd.ClearDosAttr(path, self._attrSpec)

    def IClear(self, path, attrSpec):
        """
        Clears given DOS Attributes from the given path
        :param path: file path
        :param attrSpec: Specified on or more of attribute values
        """
        self._cmd.ClearDosAttr(path, attrSpec)

    def Validate(self, path, vType=1):
        """
        Validates if current DOS Attr matches with the one applied on the given path
        :param path: File path
        :param vType: 1 - Check For ATTR Existance, 0 - Check for Absense
        """
        attrSpec = self._cmd.GetDosAttr(path)
        for attr in self._attrSpec:
            if vType == 0 and attr in attrSpec:
                raise Exception(
                    'DOS Attribute Validation failed for %s. UnExpected ATTR %s found in %s' % (path, attr, attrSpec))
            if vType == 1 and attr not in attrSpec:
                raise Exception(
                    'DOS Attribute Validation failed for %s. Expected ATTR %s not found in %s' % (path, attr, attrSpec))


# ======================
# ABE
# ======================
class ABE(Base):
    """
    Provide 'ABE' (Access based enumerations)
    """

    def __init__(self, cache):
        self._idir = IDir()
        self._cache = cache
        self._acl = None

    def Validate(self, searchFor, searchIn, vType, startFrom=None, perm=None, altDrive=None):
        """
        # Validates presence/absence of a file/directory or recursively into a directory.
        # :param searchFor:  Entry to be validated for presence/absence
        # :param searchIn:   Directory to be looked up. In case of recursive, its value will be key in cache
        # :param vType:      1=Validate for presence, 0=Validate for absence
        # :param startFrom:  None for non-recursive validation. When not None, it will be root of the list stored
        #                    dirTree stored cache by key specified in 'searchIn'
        # :param perm:       Permission used for applying ACL on 'searchFor'
        # :param altDrive:   Drive mapped by test-suite set-up which will show-up all the files/folders.
        #                    Path starting with this drive to decide if a given entry is file or folder as
        #                    that entity may not be seen in given path due ACL applied using CI, OI flags.
        """
        if vType not in [0, 1, None]:
            raise Exception('ACL: Validate: Supported values for vType are 0, 1, None. (Given value: %d)' % (vType))

        if startFrom is None:
            result = self._validate(self._isVisibilityExpected(vType, searchFor), searchFor,
                                    self._idir.List(searchIn, True, False))
            if result:
                return 0
            else:
                raise Exception('ABE: Validate: Visibility check failed for %s' % searchFor)

        if not os.path.isdir(startFrom):
            raise Exception('ABE: Validate: %s is not directory. Recursive validation only on directory' % startFrom)

        if vType is None:
            if perm is None:
                raise Exception(
                    "ABE: Validate: For recursive validation, 'perm' can not be None.\nACL with inheritance flags should have been applied on a dirtree")
            if altDrive is None:
                raise Exception(
                    "ABE: Validate: For recursive validation, 'altDrive' can not be None. Its value will be WIN.Drive for the client.")

        dirTree = self._cache.Get(searchIn)  # This list of files and folders before applying ACL
        self._cache.Del(searchIn)

        self._acl = ACL(None, None, perm)
        inheritFlags = None
        if perm is not None:
            inheritFlags = self._acl._getInheritFlags()

        # ACL /grant operation
        if vType == 1:
            if self._isVisible(dirTree, self._idir.List(startFrom)):
                logger.info('ABE: Validate: Dirtrees before and after ACL application are same.')
                return 0
            else:
                raise Exception('ABE: Validate: Dirtrees before and after ACL application are different')

        # ACL /deny operation will result in selective visibility based upon inheritance flags
        searchIn = self._idir.List(searchIn)
        result = True
        for entry in dirTree:
            stepResult = self._validate(self._isVisibilityExpected(vType, entry, startFrom, inheritFlags, altDrive),
                                        entry, searchIn)
            if not stepResult:
                result = False
            else:
                logger.error('ABE: Validate: Visibility check failed for %s' % entry)

        if result:
            return 0
        else:
            raise Exception('ABE: Validate: Visibility check failed for one or more directory entries')

    def _validate(self, visibilityExpected, searchFor, searchIn):
        """
        # Returns boolean based upon finding of 'searchFor' in 'searchIn' w.r.t. expectancy specified by 'visibilityExpected'
        # param visibilityExpected: True if 'SearchFor' is to searched for presence and False for absence
        # param searchFor:          An entity to be searched
        # param searchIn:           A target for doing search-in operation
        """
        if visibilityExpected:
            result = True if self._isVisible(searchFor, searchIn) else False
            if result:
                logger.info('%s is exepcted to be visible and is found in %s' % (searchFor, searchIn))
            else:
                logger.error('%s is exepcted to be visible but not found in %s' % (searchFor, searchIn))
        else:
            result = False if self._isVisible(searchFor, searchIn) else True
            if result:
                logger.info('%s is exepcted to be invisible and not found in %s' % (searchFor, searchIn))
            else:
                logger.error('%s is exepcted to be invisible but found in %s' % (searchFor, searchIn))
        return result

    def _isVisibilityExpected(self, vType, path, startFrom=None, inheritFlags=None, altDrive=None):
        """
        # Returns boolean indicating if a given file/folder should be visible or not.
        # If 'inheritFlags' is None 'vType' alone will decide visibility else ACL and file's position w.r.t. 'startFrom' where ACL is applied will matter.
        # param vType:        1 for expecting visibility anything else for non-visibility
        # param path:         File/dirpath to be evaluated for visibility expectancy
        # param startFrom:    Directory to which ACL with inheritance flags is applied
        # param inheritFlags: Map containing boolean set for inheritance flags: OI, CI, IO
        # param altDrive:     Drive where inheritance ACL is not specified so that file/folder will always be seen and it's needed
        #                     to decide if a given path is file/folder as 'OI' and 'CI' flags are meant for files and folders respectively.
        """
        if startFrom is None:
            ret = True if vType == 1 else False
        else:
            # If startFrom is not None; then ACL may not have been applied for a user where
            # inheritFlags will be None and expect no impact on visibility for a share mapped by that user.
            if inheritFlags is None:
                ret = True
            else:
                # As a file/dir may or may not be visible after applying ACLs, send a path which is available
                path = altDrive + path[1:]
                startFrom = altDrive + path[1:]
                ACLInheritance = self._acl._isACLInheritanceExpected(path, startFrom, inheritFlags)
                if ACLInheritance and 'R' in self.corePerm:
                    ret = True if vType == 1 else False
                else:
                    ret = True  # In case of non Read-ACL, file/dir will be always visible
        if ret:
            logger.info('Expecting visibility of: %s' % (path))
        else:
            logger.info('Expecting non-visibility of: %s' % (path))
        return ret

    def _isVisible(self, searchFor, searchIn):
        """
        # Returns boolean based upon whether 'searchFor' is found 'searchIn'
        # param searchFor: A file/dir path which is a 'string' type data or 'list' type data for recursive listing of a directory
        # param searchIn:  A target for doing search-in operation
        """
        if isinstance(searchFor, str):
            logger.info('Searching for: %s\nin [DataLength: %d] %s' % (searchFor, len(searchIn), searchIn))
        else:
            # 'searchFor' is list of entries
            logger.info('Searching for: [DataLength: %d] %s\nin [DataLength: %d] %s' % (
            len(searchFor), searchFor, len(searchIn), searchIn))

        if isinstance(searchFor, str):
            ret = False
            for entry in searchIn:
                if searchFor == os.path.basename(entry):
                    ret = True
                    break
        else:
            ret = searchFor == searchIn
        return ret


# ======================
# WPV
# ======================
class WPV(Base):
    """
    Provide 'Previous Versions' operations applied to a path
    """
    _cmd = None
    # In volrest based implementation, only latest version of the file will be copied/restored/opened
    _defaultVersion = 'LATEST'
    # In ValidatePreviousVersionFile, when destination of restored file is 'Default', it means
    # file has been restored in-place
    _restoreDestination = 'DEFAULT'
    _driveRegx = re.compile(r'^[a-z]:\\*$', re.I)

    def __init__(self, cache=None):
        self._cmd = DosCmd()

    def GetPreviousVersions(self, path, recursive=True):
        """
        Uses volrest to get a list of Previous Versions for the specified path
        :param path: Path of which associated ops will be performed.
        :return: A list of previous versions with each entry in a map of key-value pairs
        """
        logger.info('Listing previous versions of [%s]' % path)
        return self._cmd.GetPreviousVersions(path, recursive)

    def CopyPreviousVersion(self, path, destination, version='LATEST'):
        """
        Uses volrest, to restore all previous versions associated with the path in given destination
        :param path: File or directory path of which Previous Versions has to be copied
        :param destination: A dirpath in which previous versions will be copied in
        :param version: A snapshot version to be used as a reference for copy
        :return: rc code from cmd/api call
        """

        if version == WPV._defaultVersion:
            logger.info('Restoring previous versions of [%s] in [%s]' % (path, destination))
            if WPV._driveRegx.match(path):
                return self._CopyDrivePreviousVersions(path, destination)
            else:
                return self._cmd.CopyPreviousVersion(path, destination, version)
        else:
            raise Exception('Not implemented: Copy of a specific Previous Version')

    def RestorePreviousVersion(self, path, version='LATEST'):
        """
        Uses volrest, to do in-place restore of all previous versions associated with the path
        Note: 'in-place restore' means, an existing file will be replaced by it's previous version
        :param path: File or directory path of which Previous Versions has to be restored
        :param version: A snapshot version to be used as a reference for restore
        :return: rc code from cmd/api call
        """
        #  TODO: Once an API to restore a specific version of a path is developed, below call
        #        to restore using CMD interface will be replaced by API based implementation

        if version == WPV._defaultVersion:
            return self._cmd.restore_previous_version(path, version)
        else:
            raise Exception('Not implemented: Restore of a specific Previous Version')

    def GetPreviousVersionFile(self, path, restored=False, version='LATEST'):
        """
        Get path of a Previous Version file.
        :param path:     File path which has to be verified
        :parma restored: If a file at path has been restored from it's PV then set this flag to True
        :param version:  If None, latest previous version file has been copied/restored. (Note: This is the behaviour
                        supported by 'volrest')
        """
        if version != WPV._defaultVersion:
            raise Exception('Not implemented: Restore of a specific Previous Version')

        # Index of PV file in PV list will change if file is restored in-place because current file
        # become latest PV in PV list thus increasing the count of PVs available for that file.
        i = 1 if restored else 0
        previousVersions = self.GetPreviousVersions(path)
        return previousVersions[i]['pvPath']

    def ValidateRestoredFile(self, path, destination, version='LATEST'):
        """
        Verifies if size of the file which 'path' refers to is same as one in Previous Version
        file of a given 'version'
        :param path: File path which has to be verified
        :param destination: A dirpath where file has been copied/restored. If None, 'file' has been restored in-place.
        :param version: If None, latest previous version file has been copied/restored. (Note: This is the behaviour
                        supported by 'volrest')
        : return: 0 for correct restoration else raises exception
        """
        # TODO: A logic will need to be placed for a renamed/deleted path if it's was for a file or directory
        #       Current support is limited to file only.

        if os.path.exists(path):
            if not os.path.isfile(path):
                raise Exception(
                    '[%s] is not file. Validation of previous version for size is file only operation.' % path)

        restored = False
        if destination == WPV._restoreDestination:
            destination = os.path.dirname(path)
            restored = True

        if not os.path.isdir(destination):
            raise Exception('[%s] is not dirpath. Destination should be dirpath only.' % destination)

        if version != WPV._defaultVersion:
            raise Exception('Not implemented: Restore of a specific Previous Version')

        pvFilepath = self.GetPreviousVersionFile(path, restored, version)
        pvMD5Checksum = IFile().GetMD5Checksum(pvFilepath)
        restoredFilepath = os.path.join(destination, os.path.basename(path))
        return IFile().ValidateData(restoredFilepath, pvMD5Checksum, 'MD5')

    def ValidatePreviousVersionFile(self, path, referenceMD5Checksum, version='LATEST'):
        """
        Verifies if MD5 of a PV file is same as the referenceMD5.
        ReferenceMD5 is MD5 of a file just before snapshot
        :param path:   File path which has to be verified
        :referenceMD5: MD5 of path before modification or at the time of snapshot
        :param version: If None, latest previous version file has been copied/restored. (Note: This is the behaviour
                        supported by 'volrest')
        """
        if version != WPV._defaultVersion:
            raise Exception('Not implemented: Restore of a specific Previous Version')
        pvFilepath = self.GetPreviousVersionFile(path, False, version)
        return IFile().ValidateData(pvFilepath, referenceMD5Checksum, 'MD5')

    def ValidatePreviousVersionCount(self, path, pvCount):
        """
        Verifies if count of previous version associated with a path is same
        as the one specified by pvCount
        :param path: File path which has to be verified
        :pvCount: Expected value of PVs for a path
        :returns: 0 if actual count previous versions is same as pvCount else raises an exception
        """
        # TODO: A logic will need to be placed for a renamed/deleted path if it's was for a file or directory
        #       If deleted path is a directory then PVs of a path/.. will need to be listed and then
        #       search for Paths for a dirname(path) which will be actual count of PVs
        #       Current support is limited to file only.

        if os.path.exists(path):
            if not os.path.isfile(path):
                raise Exception(
                    '[%s] is not file. Validation of previous version for count is file only operation.' % path)

        pvCount = int(pvCount)
        previousVersions = self.GetPreviousVersions(path)
        pvCountActual = len(previousVersions)

        if pvCountActual == pvCount:
            return 0
        else:
            raise Exception('ValidatePVCount: Difference in #PV(s) for [%s]. Expected[%d], Actual[%d]' % (
            path, pvCount, pvCountActual))

    def GetPreviousVersionContents(self, path, version='LATEST'):
        """
        If 'path' denotes a 'dirpath' then contents of a dirpath are listed.
        :param path: Dirpath whose previous version contents are to be listed
        :version: Name of previous version. If 'Latest', then the top-most entry in the list is selected
        :returns: a list of directory contents
        """

        if not os.path.isdir(path):
            raise Exception('[%s] is not dirpath. Contents of a previous version for dirpath can be listed.' % path)

        if version != WPV._defaultVersion:
            raise Exception('Not implemented: Listing of a specific Previous Version of a directory')

        # To list the previous versions of a given 'path', previous versions of it's parent directory
        # are listed and when version is 'Latest', it's latest previous version of 'path' is selected for
        # listing.

        parentPath = os.path.dirname(path)
        previousVersions = self.GetPreviousVersions(parentPath)

        # Find the 1st entry of previous version corresponding to the dirName
        previousVersion = None
        dirName = os.path.basename(path)
        for pvEntry in previousVersions:
            if dirName == os.path.basename(pvEntry['pvPath']):
                previousVersion = pvEntry['pvPath']
                break

        if previousVersion is None:
            raise Exception('Previous version for [%s] are not available.' % (path))
        else:
            return IDir().List(previousVersion)

    def GetPreviousVersionEntry(self, path, version='LATEST'):
        """
        If 'path' denotes a 'path' then contents of a dirpath are listed.
        :param path: Will be used for listing PVs
        :version: Name of previous version. If 'Latest', then the top-most entry in the list is returned
        :returns: a list of PV entries
        """

        if version != WPV._defaultVersion:
            raise Exception('Not implemented: Listing of a specific Previous Version of a PV entry')

        targetEntry = os.path.basename(path)
        if os.path.isdir(path):
            path = os.path.dirname(path)

        for entry in self.GetPreviousVersions(path, recursive=False):
            if os.path.basename(entry['pvPath']) == targetEntry:
                return entry['pvPath']

        raise Exception('GetPreviousVersionEntry: version %s is not present' % version)

    def _CopyDrivePreviousVersions(self, drive, destination):
        """
        Copies PVs available in a drive to a destination and deletes copied drive folder during cleanup
        :param drive: Whose PV entries will be listed
        :param destination: Dirpath where collected PV entries will be copied
        :returns: 0 on success else raises an exception
        """
        for entry in self.GetPreviousVersions(drive, recursive=False):
            try:
                PVDir = entry['pvPath']
                IDir(None).Copy(PVDir, destination)
            except Exception as e:
                raise Exception('_CopyDrivePreviousVersions(): Failed to copy [%s] to [%s]. (Msg: %s)' % (
                PVDir, destination, str(e)))
        return 0


# ======================
# Archive
# ======================
class Archive(Base):
    """
    # Provides methods for Archive operations on Windows platform.
    # Requirement: Installation of 7-zip software available at http://www.7-zip.org/download.html
    """
    _cmd = None
    _archiver = None
    _x64Archiver = r'C:\Program Files\7-Zip\7z.exe'
    _x86Archiver = r'C:\Program Files (x86)\7-Zip\7z.exe'
    _opCodeRx = re.compile(r'^(add|delete)$', re.I)
    _atypeRx = re.compile(r'^(zip)$')

    def __init__(self, cache=None):
        try:
            IPath().ValidatePathExists(Archive._x64Archiver)
        except Exception as e:
            try:
                IPath().ValidatePathExists(Archive._x86Archiver)
            except Exception as e:
                logger.error('Archive.__init__: 7-zip is not installed on this system')
                raise
            else:
                self._archiver = Archive._x86Archiver
        else:
            self._archiver = Archive._x64Archiver

        self._cmd = DosCmd()

    def CreateArchive(self, source, archive, atype):
        """
        # Creates a new archive by compressing 'source' into 'archive'
        # param source:   File or directory to be compressed
        # param archive:  Filepath of archive file to be created
        # param atype:    Type of archive to be created.
        """
        IPath().CheckExists(source)

        if Archive._atypeRx.search(atype) is None:
            raise Exception('Archive: CreateArchive: Archive type [%s] is not supported' % atype)

        return self._cmd.CreateArchive(self._archiver, atype, source, archive)

    def EditArchive(self, archive, opCode, input):
        """
        # Edits an existing archive by adding/deleting/updating a file in it.
        # param opCode:   Operation to be performed. Allowed values are add|update|delete
        # param archive:  Filepath of an existing archive
        # param input:    File/directory to be processed for a given opCode
        """
        IPath().CheckExists(archive)

        if Archive._opCodeRx.search(opCode) is None:
            raise Exception('Archive: EditArchive: Unsupported opCode [%s] for editing archive' % opCode)

        return self._cmd.EditArchive(self._archiver, archive, opCode.lower(), input)

    def ExtractArchive(self, archive, path):
        """
        # Extract contents from an archive into a given path
        # :param archive:   Filepath of an existing archive
        # :param path:      Dirpath to extract contents of an archive
        """
        IPath().CheckExists(archive)
        return self._cmd.ExtractArchive(self._archiver, archive, path)


if __name__ == '__main__':
    # test

    ip = '10.180.119.44'
    username = 'support'
    password = 'P@ssw0rd'
    print(WPV().GetPreviousVersions('Z:\\test'))
