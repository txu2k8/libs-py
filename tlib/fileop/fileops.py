# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/10 13:47
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

r"""various file operations methods
FileOps class contain the various methods for various file operations
"""

import os
import re
import shutil
import time
import random
import hashlib
import itertools
import filecmp
import json
import copy

from tlib import log
from tlib.utils import util


# ======================
# --- Global
# ======================
logger = log.get_logger()
SUPPORT_NAME_LEN = 128
UNICODE_INFO = {}


# ======================
# FileOps
# ======================
class FileOps(object):
    """docstring for FileOps"""

    def __init__(self):
        super(FileOps, self).__init__()
        self.Dirs = []  # this will store all directory names after creation
        self.NewDirs = [] # this will store directory names after rename
        self.NestedDirs = []  # this will created nested directory under a TopLevelDir
        self.NewNestedDirs = []  # this will rename the nested dirs
        self.SubDirs = []  # this will create subdirs inside a Dir
        self.NewSubDirs = []  # this will rename subdirs
        self.Files = []  # this will store all files inside a dir provided
        self.NewFiles = []  # this will store all files after renames
        self.FilesAfterDirRename = []  # this will store all files after dir renames
        self.FilesCreatedBeforeDirRename = []  # this will store all files after dir renames
        self.FilesInSubDir = []  # this will store all files in subdir
        self.FilesInNestedDir = []  # this will store all files in nested dir
        self.FilesInNewNestedDir = []  # this will store all files after nested dir rename
        self.Md5Csum = {}  # dict with filename as the key to hold md5 checksum after file creation
        self.TopLevelDir = "Dir_" + time.strftime("%H%M%S")
        # self.cc_drive1 = sys.argv[1]
        # self.cc_drive2 = sys.argv[2]
        # self.cc_drive3 = sys.argv[3]

    def __del__(self):
        self.TopLevelDir = " "

    def create_dir(self, drive, number_dirs):
        """
        method to create number_dirs dirs and save this in a list
        @params:
          (string) drive
          (int) number_dirs
        @output:
          (void)
        """
        # logger.info("From %s create %s dirs " % (drive, number_dirs))
        for i in range(number_dirs):
            name = "Dir_" + time.strftime("%H%M%S") + "-"  # appending timestamp to "Dir_"
            dir_name = name + str(i)
            self.Dirs.append(dir_name)
        for dir in self.Dirs:
            dir_full_path = os.path.join(drive, dir)
            print("Create DIR: %s" % dir_full_path)
            try:
                if os.path.isdir(dir_full_path):
                    logger.warning("FAIL: %s already exists" % dir_full_path)
                else:
                    os.mkdir(dir_full_path)
            except Exception as e:
                logger.error("FAIL: creating dir {dirname}, {err}".format(dirname=dir_full_path, err=e))

    def create_nested_dirs(self, drive, levels):
        """
        method to create levels nested dirs and save this in a list
        @params:
          (string) drive
          (int) levels
        @output:
          (void)
        """
        # logger.info("From %s create nested(level=%s) dirs " % (drive, levels))
        tmp = [[self.TopLevelDir]]  # temp list storing the TopLevel dir
        # tmp =[]    # temp list storing the TopLevel dir
        dir_nested_path = []
        for i in range(levels):
            tmp.append(["S_" + str(i)])
        for item in itertools.product(*tmp):
            dir_full_path = os.path.join(drive, *item)
            # dir_nested_path=os.path.join(self.TopLevelDir,*item)
            dir_nested_path = os.path.join(*item)
            # print "Deb22" +dir_full_path
            # print "Deb33" +dir_nested_path
            tmp.append(dir_full_path)
            if os.path.isdir(dir_full_path):
                logger.warning("FAIL: %s already exists" % dir_full_path)
            else:
                os.makedirs(dir_full_path)
                # save the dirpath without the drive label
                # tmp_path =   dir_full_path[3:]
                # tmp_path = dir_nested_path
                # print "Deb10" +tmp_path
                # also keep track of top level Dir
        self.Dirs.append(self.TopLevelDir)
        self.NestedDirs.append(dir_nested_path)

    def create_sub_dirs(self, cc_drive, dir):
        """
        Subdir will be created inside the "dir"
        @params:
          (string) cc_drive
          (string) dir
        @output:
          (void)
        """
        name = "SubDir_" + time.strftime("%H%M%S")
        top_dir_path = os.path.join(cc_drive, dir)
        dir_full_path = os.path.join(top_dir_path, name)
        print("Create Sub DIR: %s" % dir_full_path)
        if os.path.isdir(dir_full_path):
            logger.warning("FAIL: %s already exists" % dir_full_path)
        else:
            os.makedirs(dir_full_path)
            # save the dirpath without the drive label
            # tmp_path =   dir_full_path[3:]
            tmp_path = os.path.join(dir, name)  # changed by tao.xu
            self.SubDirs.append(tmp_path)

    def rename_dir(self, drive):
        """
        "_new" will be appended to new name
        @params:
          (string) drive
        @output:
          (void)
        """
        name = "_new"
        for dir in self.Dirs:
            dir_full_path = os.path.join(drive, dir)
            new_dir_full_path = dir_full_path + name
            print("Rename %s -> %s" % (dir_full_path, new_dir_full_path))
            if os.path.isdir(dir_full_path):
                os.rename(dir_full_path, new_dir_full_path)
                # save the dirpath without the drive label
                tmp_path = dir + name
                # tmp_path =   new_dir_full_path[3:]
                self.NewDirs.append(tmp_path)
                # if the files are already created
                tmp_file_path = []
                for dirname, dirnames, filenames in os.walk(new_dir_full_path):
                    tmp_file_path = filenames
                for file in tmp_file_path:
                    tmp_path = os.path.join(drive, dirname)
                    new_path = os.path.join(tmp_path, file)
                    print(new_path)
                    self.FilesCreatedBeforeDirRename.append(new_path)
            else:
                logger.error("FAIL: %s does not exist" % dir_full_path)

    def rename_nested_dirs(self, drive):
        """
        "_new" will be appended to new name
        @params:
          (string) drive
        @output:
          (void)
        """
        name = "_new"
        for dir in self.NestedDirs:
            dir_full_path = os.path.join(drive, dir)
            new_dir_full_path = dir_full_path + name
            print("Rename %s -> %s" % (dir_full_path, new_dir_full_path))
            if os.path.isdir(dir_full_path):
                os.rename(dir_full_path, new_dir_full_path)
                # save the dirpath without the drive label
                tmp_path = dir + name
                # print "Deb66" +tmp_path
                # tmp_path =   new_dir_full_path[3:]
                self.NewNestedDirs.append(tmp_path)
            else:
                logger.error("FAIL: %s does not exist" % dir_full_path)

    def rename_subdir(self, drive):
        """
        "_new" will be appended to new name
        @params:
          (string) drive
        @output:
          (void)
        """
        name = "_new"
        for dir in self.SubDirs:
            dir_full_path = os.path.join(drive, dir)
            new_dir_full_path = dir_full_path + name
            print("Rename %s -> %s" % (dir_full_path, new_dir_full_path))
            if os.path.isdir(dir_full_path):
                os.rename(dir_full_path, new_dir_full_path)
                # save the dirpath without the drive label
                tmp_path = dir + name
                # tmp_path =   new_dir_full_path[3:]
                self.NewSubDirs.append(tmp_path)
            else:
                logger.error("FAIL: %s does not exist" % dir_full_path)

    def list_dir(self, drive, Dirs, number_dirs):
        """
        list drive/dirs
        @params:
          (string) drive
          (string) drive
          (int) number_dirs
        @output:
          (void)
        """
        count = 0
        for dir in Dirs:
            dir_full_path = os.path.join(drive, dir)
            if os.path.isdir(dir_full_path):
                for dirname, dirnames, filenames in os.walk(dir_full_path):
                    print(str(dirname))
                    count = count + 1
            else:
                logger.error("FAIL: %s does not exist" % dir_full_path)
        if count == number_dirs:
            logger.info("PASS: All the directories created exist")
        else:
            logger.error("FAIL: All the directories created dont exist")

    def remove_dir(self, drive, Dirs):
        """
        remove(delete) drive/dirs
        @params:
          (string) drive
          (string) drive
        @output:
          (void)
        """
        for dir in Dirs:
            dir_full_path = os.path.join(drive, dir)
            print("Remove DIR: %s" % dir_full_path)
            if os.path.isdir(dir_full_path):
                # os.rmdir(dir_full_path)
                # logger.debug('Delete folder: %s' % dir_full_path)
                shutil.rmtree(dir_full_path, ignore_errors=True)
            else:
                logger.error("FAIL: %s does not exist" % dir_full_path)

    def randomBytes(self, n):
        """
        returns a byte array of random bytes
        @params:
          (int) n
        @output:
          (byte) return
        """
        return bytearray(random.getrandbits(8) for i in range(n))

    def random_char_gen(self, char_len=16):
        """
        generate random chars,
        @params:
          (int) char_len
        @output:
          (char) random chars
        """
        # ord(xx) -> xx for python3
        return ''.join(map(lambda xx: (hex(xx)[2:]), os.urandom(char_len)))

    def md5(self, fname):
        """
        returns the md5 checksum of the opened file
        @params:
          (string) fname
        @output:
          (string) return
        """
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def get_md5(self, fname, retry=30):
        """
        returns the md5 checksum of the opened file
        @params:
          (string) fname
        @output:
          (string) return
        """
        cur_dir = os.getcwd()
        MD5Tool = os.path.join(cur_dir, "tools\\bin\md5sum.exe ")
        md5_cmd = MD5Tool + " " + fname
        for x in range(1, retry):
            rtn = util.run_cmd(md5_cmd)
            if rtn['returncode'] == 0:
                md5_value = rtn['stdout'].split(' ')[0].split('\\')[-1]
                return md5_value
            else:
                logger.debug(fname + ': ' + str(rtn))
                logger.info("Get MD5 for %s, retry=%d/%d" % (fname, x, retry))
                time.sleep(10)

        return False

    def create_filenames(self, drive, dir, type, number_files, *threaded):
        """
        create file_names with .type extension. optional argument *threaded is for creating names
        with timestamps if multiple threads are used to create the files.
        @params:
          (string) drive
          (string) dir
          (string) type  --eg:txt,xls
          (int) number_files
          (*) *threaded  --timestamps
        @output:
          (void)
        """
        for i in range(number_files):
            # new_dir_full_path = os.path.join(drive, dir)
            if threaded:
                name = "file" + "-" + str(threaded[0]) + "-"
            else:
                name = "file" + "-"
            file_name = name + str(i) + type
            # file_path = os.path.join(new_dir_full_path, file_name)
            # save the file_path without the drive label
            # tmp_path =   file_path[3:]
            tmp_path = os.path.join(dir, file_name)
            self.Files.append(tmp_path)
            # print "Deb1 " +tmp_path
            # if there is a dir rename need to save in this list FilesAfterDirRename
            for dir in self.NewDirs:
                # new_dir_full_path = os.path.join(drive, dir)
                name = "file" + "-"
                file_name = name + str(i) + type
                # file_path = os.path.join(new_dir_full_path, file_name)
                # save the file_path without the drive label
                # tmp_path1 =   file_path[3:]
                tmp_path1 = os.path.join(dir, file_name)
                self.FilesAfterDirRename.append(tmp_path1)
            # if Subdir exists
            for dir in self.SubDirs:
                # new_dir_full_path = os.path.join(drive, dir)
                name = "file" + "-"
                file_name = name + str(i) + type
                # file_path = os.path.join(new_dir_full_path, file_name)
                # save the file_path without the drive label
                # tmp_path1 =   file_path[3:]
                tmp_path1 = os.path.join(dir, file_name)
                self.FilesInSubDir.append(tmp_path1)
            # if NestedDir exists
            for dir in self.NestedDirs:
                # new_dir_full_path = os.path.join(drive, dir)
                name = "file" + "-"
                file_name = name + str(i) + type
                # file_path = os.path.join(new_dir_full_path, file_name)
                # save the file_path without the drive label
                # tmp_path1 =   file_path[3:]
                tmp_path1 = os.path.join(dir, file_name)
                self.FilesInNestedDir.append(tmp_path1)
            # if NewNestedDir exists
            for dir in self.NewNestedDirs:
                # new_dir_full_path = os.path.join(drive, dir)
                name = "file" + "-"
                file_name = name + str(i) + type
                # file_path = os.path.join(new_dir_full_path, file_name)
                # save the file_path without the drive label
                # tmp_path1 =   file_path[3:]
                tmp_path1 = os.path.join(dir, file_name)
                self.FilesInNewNestedDir.append(tmp_path1)

    def create_file_and_calculate_csm(self, drive, bytes, *threaded):
        """
        create file and calculate md5 checksum
        @params:
          (string) drive
          (string) bytes
          (*) *threaded  --timestamps
        @output:
          (void)
        """
        for file in self.Files:
            file_full_path = os.path.join(drive, file)
            try:
                if threaded:
                    if str(threaded[0]) in file:
                        with open(file_full_path, 'a+') as f:
                            f.write(self.random_char_gen(bytes) + '!@#$%%^&*(\n')
                            f.flush()
                            os.fsync(f.fileno())
                        # fl = open(file_full_path, 'w')
                        # rand_bytes = self.randomBytes(bytes)
                        # fl.write(str(rand_bytes))
                        # fl.close()
                        md5checksum = self.md5(file_full_path)
                        self.Md5Csum[file_full_path] = md5checksum
                else:
                    with open(file_full_path, 'a+') as f:
                        f.write(self.random_char_gen(bytes) + '!@#$%%^&*(\n')
                        f.flush()
                        os.fsync(f.fileno())
                    # fl = open(file_full_path, 'w')
                    # rand_bytes = self.randomBytes(bytes)
                    # fl.write(str(rand_bytes))
                    # fl.close()
                    md5checksum = self.md5(file_full_path)
                    self.Md5Csum[file_full_path] = md5checksum
                    print("File: %s, MD5: %s" % (file_full_path, md5checksum))
            except Exception as e:
                logger.error("FAIL: creating file {filename}, {err}".format(filename=file_full_path, err=e))
                return False
        for file in self.FilesAfterDirRename:
            file_full_path = os.path.join(drive, file)
            try:
                with open(file_full_path, 'a+') as f:
                    f.write(self.random_char_gen(bytes) + '!@#$%%^&*(\n')
                    f.flush()
                    os.fsync(f.fileno())
                # fl = open(file_full_path, 'w')
                # rand_bytes = self.randomBytes(bytes)
                # fl.write(str(rand_bytes))
                # fl.close()
                md5checksum = self.md5(file_full_path)
                self.Md5Csum[file_full_path] = md5checksum
                print("File: %s, MD5: %s" % (file_full_path, md5checksum))
            except Exception as e:
                logger.error("FAIL: creating file {filename}, {err}".format(filename=file_full_path, err=e))
                return False

        return True

    def create_large_size_file_names(self, drive, dir, type, number_files):
        """
        create large size file names
        @params:
          (string) drive
          (string) dir
          (string) type
          (int) number_files
        @output:
          (void)
        """
        for i in range(number_files):
            # new_dir_full_path = os.path.join(drive, dir)
            name = "file" + "-"
            file_name = name + str(i) + type
            # file_path = os.path.join(new_dir_full_path, file_name)
            # save the file_path without the drive label
            # tmp_path =   file_path[3:]
            tmp_path = os.path.join(dir, file_name)
            self.Files.append(tmp_path)
            # if there is a dir rename need to save in this list FilesAfterDirRename
            for dir in self.NewDirs:
                # new_dir_full_path = os.path.join(drive, dir)
                name = "file" + "-"
                file_name = name + str(i) + type
                # file_path = os.path.join(new_dir_full_path, file_name)
                # save the file_path without the drive label
                # tmp_path1 = file_path[3:]
                tmp_path1 = os.path.join(dir, file_name)
                self.FilesAfterDirRename.append(tmp_path1)

    def create_large_size_file(self, drive, size=10):
        """
        create large size file
        @params:
          (string) drive
          (string) dir
          (string) type
          (int) number_files
        @output:
          (void)
        """
        for file in self.Files:
            try:
                file_full_path = os.path.join(drive, file)
                bs = '1M'
                dd_count = size
                util.dd_w(file_full_path, bs, dd_count)

                # with open(file_full_path, 'a+') as f:
                #     f.write(self.random_char_gen(bytes) + '!@#$%%^&*(\n')
                # with open(file_full_path, "wb") as out:
                #     out.truncate(bytes)
                md5checksum = self.md5(file_full_path)
                self.Md5Csum[file_full_path] = md5checksum
                logger.debug("File: %s, MD5: %s" % (file_full_path, md5checksum))
                return True
            except Exception as e:
                logger.error("FAIL: creating file!")
                logger.error(str(e))
                return False

    def write_file(self, file_full_path, bytes):
        """
        Write files with size: bytes
        :param file_full_path:
        :param bytes:
        :return: bool True / False
        """
        try:
            with open(file_full_path, 'a+') as f:
                print("Write %s bytes data in %s" % (bytes, file_full_path))
                f.write(self.random_char_gen(bytes) + '!@#$%%^&*(\n')
                f.flush()
                os.fsync(f.fileno())
            return True
        except Exception as e:
            logger.error("FAIL: writing to file %s" % file_full_path)
            logger.error(str(e))
            return False

    def modify_files(self, drive, file, bytes):
        """
        if there is a dir rename need to save in this list FilesAfterDirRename
        @params:
          (string) drive
          (string) file
          (string) bytes
        @output:
          (void)
        """

        if self.NewDirs:
            for dir in self.NewDirs:
                # taking out file_name, it would just return base file_name
                file_name = os.path.basename(file)
                file_path = os.path.join(dir, file_name)
                file_full_path = os.path.join(drive, file_path)
                # save the file_path without the drive label
                # tmp_path1 =   file_full_path[3:]
                # tmp_path1 = file_path
                # print "Deb77" +tmp_path1
                rtn = self.write_file(file_full_path, bytes)

        elif self.NewNestedDirs:
            for dir in self.NewNestedDirs:
                # taking out file_name, it would just return base file_name
                file_name = os.path.basename(file)
                file_path = os.path.join(dir, file_name)
                file_full_path = os.path.join(drive, file_path)
                # save the file_path without the drive label
                # tmp_path1 =   file_full_path[3:]
                # tmp_path1 = file_path
                # print "Deb77" +tmp_path1
                rtn = self.write_file(file_full_path, bytes)
        else:
            file_full_path = os.path.join(drive, file)
            rtn = self.write_file(file_full_path, bytes)

        return rtn

    def add_attributes(self, drive, dir):
        """
        add attributes to drive/dir
        @params:
          (string) drive
          (string) dir
        @output:
          (void)
        """
        try:
            dir_path = os.path.join(drive, dir)
            print("Add attributes: %s" % dir_path)
            os.system("attrib +a " + dir_path)
            os.system("attrib +r " + dir_path)
            os.system("attrib +h " + dir_path)
            # os.system("attrib +s " +file_full_path)
            return True
        except Exception as e:
            logger.error("FAIL: setting attribute to dir %s" % dir_path)
            logger.error(str(e))
            return False

    def remove_attributes(self, drive, dir):
        """
        remove attributes to drive/dir
        @params:
          (string) drive
          (string) dir
        @output:
          (void)
        """
        try:
            dir_path = os.path.join(drive, dir)
            print("Remove attributes: %s" % dir_path)
            os.system("attrib -a " + dir_path)
            os.system("attrib -r " + dir_path)
            os.system("attrib -h " + dir_path)
            # os.system("attrib -s " +file_full_path)
            return True
        except Exception as e:
            logger.error("FAIL: removing attribute to dir %s" % dir_path)
            logger.error(str(e))
            return False

    def add_acls(self, drive, dir, acl='test1'):
        """
        add acls to drive/dir
        @params:
          (string) drive
          (string) dir
        @output:
          (void)
        """
        try:
            dir_path = os.path.join(drive, dir)
            print("Add acls: %s" % dir_path)
            # os.system("icacls " + dir_path + " /grant Everyone:f")
            # os.system("icacls " + dir_path + " /grant test1:(OI)(CI)F")
            add_acls_cmd = "icacls %s /grant %s:(OI)(CI)F" % (dir_path, acl)
            logger.debug(add_acls_cmd)
            os.system(add_acls_cmd)
            return True
        except Exception as e:
            logger.error("FAIL: setting acls to dir %s" % dir_path)
            logger.error(str(e))
            return False

    def remove_acls(self, drive, dir, acl='test1'):
        """
        remove acls to drive/dir
        @params:
          (string) drive
          (string) dir
        @output:
          (void)
        """
        try:
            dir_path = os.path.join(drive, dir)
            print("Remove acls: %s" % dir_path)
            # os.system("icacls " + dir_path + " /remove Everyone:g")
            # os.system("icacls " + dir_path + " /remove test1:g")
            rm_acls_cmd = "icacls %s /remove:g %s" % (dir_path, acl)
            logger.debug(rm_acls_cmd)
            os.system(rm_acls_cmd)
            return True
        except Exception as e:
            logger.error("FAIL: setting acls to dir %s" % dir_path)
            logger.error(str(e))
            return False

    def get_acls(self, dir_path):
        get_acls_cmd = "icacls %s" % dir_path
        try:
            acls_info = util.run_cmd(get_acls_cmd)['stdout'].replace(dir_path, '')
            pattern = re.compile(r'\w.+\)')
            acls_list = pattern.findall(acls_info)
            return acls_list
        except Exception as e:
            logger.error("FAIL: Get dir %s acls" % dir_path)
            logger.error(str(e))
            return False

    def rename_files(self, drive, file):
        """
        rename file: drive/dir
        @params:
          (string) drive
          (string) dir
        @output:
          (void)
        """
        try:
            file_full_path = os.path.join(drive, file)
            file_name_parts = file.split(".")  # split actual filename and extension
            new_file_name = file_name_parts[0] + "_new." + file_name_parts[1]
            new_full_path = os.path.join(drive, new_file_name) # constructing the new name
            print("Rename %s -> %s" % (file_full_path, new_full_path))
            os.rename(file_full_path, new_full_path)
            # save the file_path without the drive label
            # tmp_path = new_full_path[3:]
            self.NewFiles.append(new_file_name)
            return True
        except Exception as e:
            logger.error("FAIL: renaming the file %s " % file_full_path)
            logger.error(str(e))
            return False

    def delete_files(self, drive, file):
        """
        delete file: drive/dir
        @params:
          (string) drive
          (string) dir
        @output:
          (void)
        """
        file_full_path = os.path.join(drive, file)
        print("Delete %s" % file_full_path)
        try:
            os.remove(file_full_path)
            return True
        except Exception as e:
            logger.error("FAIL: deleting the file " + file_full_path)
            logger.error(str(e))
            return False

    def helper_create_files(self, drive, bytes, threaded):
        self.create_file_and_calculate_csm(drive, bytes, threaded)

    def robocopy_files(self, drive1, drive2, dir):
        source = os.path.join(drive1, dir)
        dest = os.path.join(drive2, dir)
        robocopy_cmd = "robocopy %s %s /E /MIR" % (source, dest)
        try:
            os.system(robocopy_cmd)
            return True
        except Exception as e:
            logger.error("FAIL: setting acls to dir %s" % dir)
            logger.error(str(e))
            return False

    def wait_data_sync(self, drive1, drive2, check_data=False, check_acls=False, retry=360):
        """
        wait for data sync between drive1 and drive2
        @params:
          (char) drive1
          (char) drive2
        @output:
          (bool) True / False
        """

        for x in range(1, retry + 1):
            sync_flag = False
            try:
                obj_filecmp = filecmp.dircmp(drive1, drive2)
                left_right_only = obj_filecmp.left_only + obj_filecmp.right_only
                if left_right_only:
                    sync_flag = False
                    logger.warning('FAIL: Check meta sync between %s and %s ' % (drive1, drive2))
                    logger.warning("Wait to meta sync between %s and %s --> \n %s" % (drive1, drive2, json.dumps(left_right_only, indent=4)))
                    util.sleep_progressbar(30)
                    continue
                else:
                    if check_data and obj_filecmp.diff_files:
                        # logger.warning('FAIL: Check data sync(all file the same) between %s and %s ' % (drive1, drive2))
                        logger.warning("Wait to data sync between %s and %s --> \n %s" % (
                                            drive1, drive2, json.dumps(obj_filecmp.diff_files, indent=4)))
                        util.sleep_progressbar(30)
                        continue
                    if check_acls:
                        drive1_acls = self.get_acls(drive1)
                        drive2_acls = self.get_acls(drive2)
                        not_sync_acls_list = util.get_list_difference(drive1_acls, drive2_acls)
                        if not_sync_acls_list:
                            sync_flag = False
                            # logger.warning('FAIL: Check acls sync between %s and %s ' % (drive1, drive2))
                            logger.warning("Wait to acls sync between %s and %s --> \n %s" % (
                                                drive1, drive2, json.dumps(not_sync_acls_list, indent=4)))
                            util.sleep_progressbar(30)
                            continue

                    sync_flag = True
                    logger.info('PASS: Check data sync between %s and %s (check_data=%s, check_acls=%s)' % (drive1, drive2, check_data, check_acls))
                    break
            except Exception as e:
                logger.error("ERROR: run wait_data_sync, Will retry %d/%d \n %s" % (x, retry, str(e)))
                if 'Access is denied' in str(e):
                    break
                util.sleep_progressbar(30)
                continue
        else:
            sync_flag = False
            logger.error('Check data sync timeout between %s and %s (check_data=%s, check_acls=%s)...' % (drive1, drive2, check_data, check_acls))

        if len(obj_filecmp.common_dirs) > 0:
            for item in obj_filecmp.common_dirs:
                self.wait_data_sync(os.path.join(drive1,item), os.path.abspath(os.path.join(drive2,item)), check_data, check_acls, retry)

        return sync_flag

    def wait_data_sync_list(self, drive_base, drive_list, check_data=False, check_acls=False, retry=360):
        """
        wait for data sync between drive_base and all drive_list, return False once anyone can not sync
        @params:
          (char) drive_base
          (char) drive_list
        @output:
          (bool) True / False
        """
        sync_drive_list = copy.deepcopy(drive_list)
        if drive_base in sync_drive_list:
            sync_drive_list.remove(drive_base)

        sync_flag = False
        if not sync_drive_list:
            logger.warning("No drive need to be sync from %s!" % drive_base)
            return True

        for drive_tmp in sync_drive_list:
            sync_flag = self.wait_data_sync(drive_base, drive_tmp, check_data, check_acls, retry)
            if not sync_flag:
                return False

        return True


    def create_longname_dir(self, drive, number_dirs):
        """
        create longname dir
        @params:
          (string) drive
          (int) number_dirs
          (int) name_len_max
        @output:
          (void)
        """
        for i in range(number_dirs):
            language_type = random.choice(UNICODE_INFO.keys())
            chr_start = UNICODE_INFO[language_type]['start']
            chr_end = UNICODE_INFO[language_type]['end']
            chr_size = UNICODE_INFO[language_type]['size']
            name_len = SUPPORT_NAME_LEN - 4 - len(str(i)) -1
            num = name_len / chr_size
            # print("name used: %s * %d" % (language_type, num))
            tmp_longname = util.unicode_chr(chr_start, chr_end, num)

            dir_name = "Dir_" + tmp_longname + "-" + str(i)
            self.Dirs.append(dir_name)

        for dir in self.Dirs:
            dir_full_path = os.path.join(drive, dir)
            # print("Create DIR: %s" % dir_full_path)
            if os.path.isdir(dir_full_path):
                logger.warning("FAIL: %s already exists" % dir_full_path)
            else:
                os.mkdir(dir_full_path)

    def create_long_filenames(self, drive, dir, file_type, number_files):
        """
        create longname dir
        @params:
          (string) drive
          (int) number_dirs
          (int) name_len_max
        @output:
          (void)
        """
        file_type = file_type if file_type.startswith('.') else '.' + file_type
        for i in range(number_files):
            language_type = random.choice(UNICODE_INFO.keys())
            chr_start = UNICODE_INFO[language_type]['start']
            chr_end = UNICODE_INFO[language_type]['end']
            chr_size = UNICODE_INFO[language_type]['size']
            name_len = SUPPORT_NAME_LEN - 5 - len(str(i)) -1 - len(file_type)
            num = name_len / chr_size
            # print("name used: %s * %d" % (language_type, num))
            tmp_longname = util.unicode_chr(chr_start, chr_end, num)

            file_name = "file_" + tmp_longname + "-" + str(i) + file_type
            tmp_path = os.path.join(dir, file_name)
            self.Files.append(tmp_path)

            for dir in self.NewDirs:
                tmp_path1 = os.path.join(dir, file_name)
                self.FilesAfterDirRename.append(tmp_path1)
            # if Subdir exists
            for dir in self.SubDirs:
                tmp_path1 = os.path.join(dir, file_name)
                self.FilesInSubDir.append(tmp_path1)
            # if NestedDir exists
            for dir in self.NestedDirs:
                tmp_path1 = os.path.join(dir, file_name)
                self.FilesInNestedDir.append(tmp_path1)
            # if NewNestedDir exists
            for dir in self.NewNestedDirs:
                tmp_path1 = os.path.join(dir, file_name)
                self.FilesInNewNestedDir.append(tmp_path1)

    def write_longname_file(self, file_full_path, bytes):
        try:
            with open(file_full_path, 'a+') as f:
                # print("Write %s bytes data in %s" % (bytes, file_full_path))
                f.write(self.random_char_gen(bytes) + '!@#$%%^&*(\n')
                f.flush()
                os.fsync(f.fileno())
            return True
        except Exception as e:
            logger.error("FAIL: writing to file %s" % file_full_path)
            logger.error(str(e))
            return False

    def modify_longname_files(self, drive, file, bytes):
        """
        if there is a dir rename need to save in this list FilesAfterDirRename
        @params:
          (string) drive
          (string) file
          (string) bytes
        @output:
          (void)
        """

        if self.NewDirs:
            for dir in self.NewDirs:
                # taking out file_name, it would just return base file_name
                file_name = os.path.basename(file)
                file_path = os.path.join(dir, file_name)
                file_full_path = os.path.join(drive, file_path)
                # save the file_path without the drive label
                # tmp_path1 =   file_full_path[3:]
                # tmp_path1 = file_path
                # print "Deb77" +tmp_path1
                rtn = self.write_longname_file(file_full_path, bytes)

        elif self.NewNestedDirs:
            for dir in self.NewNestedDirs:
                # taking out file_name, it would just return base file_name
                file_name = os.path.basename(file)
                file_path = os.path.join(dir, file_name)
                file_full_path = os.path.join(drive, file_path)
                # save the file_path without the drive label
                # tmp_path1 =   file_full_path[3:]
                # tmp_path1 = file_path
                # print "Deb77" +tmp_path1
                rtn = self.write_longname_file(file_full_path, bytes)
        else:
            file_full_path = os.path.join(drive, file)
            rtn = self.write_longname_file(file_full_path, bytes)

        return rtn

    def list_longname_dir(self, drive, Dirs, number_dirs):
        """
        list drive/dirs
        @params:
          (string) drive
          (string) drive
          (int) number_dirs
        @output:
          (void)
        """
        count = 0
        for dir in Dirs:
            dir_full_path = os.path.join(drive, dir)
            if os.path.isdir(dir_full_path):
                for dirname, dirnames, filenames in os.walk(dir_full_path):
                    # print str(dirname)
                    count = count + 1
            else:
                logger.error("FAIL: %s does not exist" % dir_full_path)
        if count == number_dirs:
            logger.info("PASS: All the directories created exist")
        else:
            logger.error("FAIL: All the directories created dont exist")

    def rename_longname_files(self, drive, file):
        """
        rename file: drive/dir
        @params:
          (string) drive
          (string) dir
        @output:
          (void)
        """
        try:
            file_full_path = os.path.join(drive, file)
            file_name_parts = file.split(".")  # split actual filename and extension
            new_file_name = file_name_parts[0] + "_new." + file_name_parts[1]
            new_full_path = os.path.join(drive, new_file_name)  # constructing the new name
            # print("Rename %s -> %s" % (file_full_path, new_full_path))
            os.rename(file_full_path, new_full_path)
            # save the file_path without the drive label
            # tmp_path = new_full_path[3:]
            self.NewFiles.append(new_file_name)
            return True
        except Exception as e:
            logger.error("FAIL: renaming the file %s " % file_full_path)
            logger.error(str(e))
            return False

    def rename_longname_dir(self, drive):
        """
        "_new" will be appended to new name
        @params:
          (string) drive
        @output:
          (void)
        """
        name = "_new"
        for dir in self.Dirs:
            dir_full_path = os.path.join(drive, dir)
            new_dir_full_path = dir_full_path + name
            # print("Rename %s -> %s" % (dir_full_path, new_dir_full_path))
            if os.path.isdir(dir_full_path):
                os.rename(dir_full_path, new_dir_full_path)
                # save the dirpath without the drive label
                tmp_path = dir + name
                # tmp_path =   new_dir_full_path[3:]
                self.NewDirs.append(tmp_path)
                # if the files are already created
                tmp_file_path = []
                for dirname, dirnames, filenames in os.walk(new_dir_full_path):
                    tmp_file_path = filenames
                for file in tmp_file_path:
                    tmp_path = os.path.join(drive, dirname)
                    new_path = os.path.join(tmp_path, file)
                    # print(new_path)
                    self.FilesCreatedBeforeDirRename.append(new_path)
            else:
                logger.error("FAIL: %s does not exist" % dir_full_path)
                return False
        return True

    def remove_longname_dir(self, drive, Dirs):
        """
        remove(delete) drive/dirs
        @params:
          (string) drive
          (string) drive
        @output:
          (void)
        """
        for dir in Dirs:
            dir_full_path = os.path.join(drive, dir)
            # print("Remove DIR: %s" % dir_full_path)
            if os.path.isdir(dir_full_path):
                # os.rmdir(dir_full_path)
                logger.debug('Delete folder: %s' % dir_full_path)
                shutil.rmtree(dir_full_path, ignore_errors=True)
            else:
                logger.error("FAIL: %s does not exist" % dir_full_path)
                return False
        return True


if __name__ == '__main__':
    import fire

    fire.Fire()
