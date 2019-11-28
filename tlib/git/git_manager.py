# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/11/28 14:10
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

import os

from tlib.log import log
from tlib.utils import util
from tlib.ssh_manager import SSHManager

# =============================
# --- Global
# =============================
logger = log.get_logger()


class GitManager(object):
    """Git manager"""

    def __init__(self, build_path, remote_ip=None, username=None,
                 password=None, key_file=None):
        super(GitManager, self).__init__()
        self.build_path = build_path
        if remote_ip:
            ssh_mgr = SSHManager(remote_ip, username, password, key_file)
            self.run_cmd = ssh_mgr.ssh_cmd
        else:
            self.run_cmd = util.run_cmd

    def pull(self):
        cmd_branch = 'cd {0} && git branch -a'.format(self.build_path)
        rc, output = self.run_cmd(cmd_branch)
        logger.info('\n{0}'.format(output))

        cmd_pull = 'cd {0} && git pull'.format(self.build_path)
        rc, output = self.run_cmd(cmd_pull, expected_rc='ignore')
        logger.info('\n{0}'.format(output))
        if 'error' in output or ('fatal' in output):
            raise Exception("Git pull failed!")

        return rc, output

    def tag(self, tag_name):
        cmd_tag = 'cd {0} && git tag -a {1} -m "tag for test build"'.format(
            self.build_path, tag_name)
        rc, output = self.run_cmd(cmd_tag, expected_rc=0)
        logger.info(output)

        cmd_push_tag = 'cd {build_path} && git push origin {tag_name}'.format(
            build_path=self.build_path, tag_name=tag_name)
        rc, output = self.run_cmd(cmd_push_tag, expected_rc='ignore')
        logger.info(output)

        return rc, output

    def get_current_branch(self):
        cmd_branch = "cd {0} && git rev-parse --abbrev-ref HEAD".format(self.build_path)

        rc, output = self.run_cmd(cmd_branch, expected_rc='ignore')
        logger.info(output.strip('\n'))
        branch = output.strip('\n')
        return branch

    def get_change_list(self, since=None):
        if since is None:
            since = '1.day'

        rc, output1 = self.run_cmd('date', expected_rc=0)
        logger.info(output1)

        cmd_log = 'cd {0} && git log --since="{1}" --date=local --pretty=format:"%an - %h - %ad: %n%s%n"'.format(
            self.build_path, since)
        rc, output2 = self.run_cmd(cmd_log, expected_rc=0)
        logger.info(output2)
        return output1.strip(), output2.strip()

    def make(self, binary_name, binary_path):
        # make realclean
        cmd_realclean = 'cd {0} && make realclean'.format(binary_path)
        rc, output = self.run_cmd(cmd_realclean, expected_rc='ignore')
        logger.debug(output)

        # grep binary, make sure "make realclean" success
        cmd_grep_binary = 'ls {0} |grep -w ^{1}$'.format(binary_path, binary_name)
        rc, output = self.run_cmd(cmd_grep_binary, expected_rc=0)
        logger.info(output)

        # make new binary
        if output == '':
            cmd_make = 'cd {0} && make -j8'.format(binary_path)
            rc, output = self.run_cmd(cmd_make, expected_rc='ignore')
            if 'Error' in output or 'error' in output:
                logger.warning(output)
            else:
                logger.debug(output)

        # get new binary MD5
        cmd_get_md5 = 'md5sum {0}'.format(os.path.join(binary_path, binary_name))
        rc, output = self.run_cmd(cmd_get_md5, expected_rc=0)
        logger.info(output.strip('\n'))

        md5sum = output.strip('\n').split(' ')[0]
        assert md5sum

        return md5sum


if __name__ == '__main__':
    git_1 = GitManager('C:\\GitRepository\\pztest')
    git_1.pull()
    git_1.get_current_branch()

    git_2 = GitManager('/root/Git/pztest', '10.180.119.1', 'root', 'password')
    git_2.get_current_branch()
