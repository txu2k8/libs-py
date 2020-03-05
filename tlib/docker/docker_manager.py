# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/11/15 16:33
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

""" docker manager
"""

from tlib import log
from tlib.ssh_manager import SSHManager

# =============================
# --- Global
# =============================
logger = log.get_logger()


class DockerManager(SSHManager):

    def __init__(self, ip, username='root', password='password', key_file=None,
                 docker_user='admin', docker_pwd='admin'):
        super(DockerManager, self).__init__(ip, username, password, key_file)
        self.docker_user = docker_user
        self.docker_pwd = docker_pwd

    def docker_login(self, registry):
        cmd = 'docker login {registry} -u {docker_user} -p {docker_pwd}'.format(
            registry=registry, docker_user=self.docker_user,
            docker_pwd=self.docker_pwd)
        rc, output = self.ssh_cmd(cmd, expected_rc='ignore', get_pty=True)
        if 'Login Succeeded' in output:
            logger.info(output)
        else:
            logger.error(output)
            raise Exception('Docker login fail.')

    def docker_load(self, image):
        cmd = 'docker load < {image}'.format(image=image)
        rc, output = self.ssh_cmd(cmd, expected_rc='ignore')
        if 'Loaded image' in output:
            logger.info(output)
        else:
            logger.error(output)
            raise Exception('Docker load fail.')

    def docker_tag(self, old_image, new_image):
        cmd = 'docker tag {old_image} {new_image}'.format(old_image=old_image,
                                                          new_image=new_image)
        rc, output = self.ssh_cmd(cmd, expected_rc=0)
        if 'Error' in output:
            logger.error(output)
            raise Exception('Docker tag fail.')
        logger.info(output)

    def docker_push(self, image):
        cmd = 'docker push {image}'.format(image=image)
        rc, output = self.ssh_cmd(cmd, expected_rc=0)
        if 'Error' in output:
            logger.error(output)
            raise Exception('Docker push fail.')
        logger.info(output)

    def docker_pull(self, image):
        cmd = 'docker pull {image}'.format(image=image)
        rc, output = self.ssh_cmd(cmd, expected_rc=0)
        if 'Error' in output:
            logger.error(output)
            raise Exception('Docker pull fail.')
        logger.info(output)

    def docker_build(self, image, docker_file_path):
        cmd = 'docker build -t {image} {path}'.format(image=image,
                                                      path=docker_file_path)
        rc, output = self.ssh_cmd(cmd, expected_rc='ignore')

        if 'Successfully tagged' in output and 'Successfully built' in output:
            logger.info(output)
        else:
            logger.error(output)
            raise Exception('Generate docker image fail.')

    def docker_kill(self, docker_id):
        cmd = 'docker kill {id}'.format(id=docker_id)
        rc, output = self.ssh_cmd(cmd, expected_rc=0)
        logger.info(output)


if __name__ == '__main__':
    node_ip = '10.25.119.71'
    docker_obj = DockerManager(node_ip)
    print(docker_obj.docker_login('company.ai.registry:5000'))