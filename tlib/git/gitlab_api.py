# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/11/28 14:08
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

import gitlab

from tlib.log import log
from tlib.retry import retry_call

# =============================
# --- Global
# =============================
logger = log.get_logger()


class GitlabAPI(object):
    _session = None

    def __init__(self, url, private_token):
        self.url = url
        self.private_token = private_token

    @property
    def session(self):
        if self._session is None:
            self._session = gitlab.Gitlab(url=self.url, private_token=self.private_token)

        return self._session

    def get_project_obj_by_name(self, name):
        return self.session.projects.get(name)

    def get_pipeline_obj_by_name(self, tag_name, project_name):
        project_obj = self.get_project_obj_by_name(project_name)
        for pipeline_obj in project_obj.pipelines.list(per_page=200, as_list=False):
            if pipeline_obj.ref == tag_name:
                return pipeline_obj

    def get_job_obj_by_name(self, job_name, tag_name, project_name):
        pipeline_obj = self.get_pipeline_obj_by_name(tag_name, project_name)
        rtn_obj = None
        for job_obj in pipeline_obj.jobs.list():
            if job_obj.name == job_name:
                rtn_obj = job_obj
        return rtn_obj

    def is_job_status_ok(self, job_name, tag_name, project_name, status='success'):
        job_obj = self.get_job_obj_by_name(job_name, tag_name, project_name)
        if job_name in ['test'] and job_obj is None:
            logger.warning("No job: {0}".format(job_name))
            return True
        status_msg = '[{0}:{1}] Job {2} status: {3}'.format(project_name, tag_name, job_name, job_obj.status)
        if job_obj.status == status:
            logger.info(status_msg)
            return True
        elif job_obj.status in ['failed', 'canceled']:
            logger.error(status_msg)
            return False
        else:
            raise Exception(status_msg)

    def is_job_build_image_success(self, tag_name, project_name):
        job_success = retry_call(self.is_job_status_ok,
                                 fkwargs={'job_name': 'build-image', 'tag_name': tag_name,
                                          'project_name': project_name, 'status': 'success'},
                                 tries=240, delay=30)
        return job_success

    def is_job_test_success(self, tag_name, project_name):
        job_success = retry_call(self.is_job_status_ok,
                                 fkwargs={'job_name': 'test', 'tag_name': tag_name,
                                          'project_name': project_name, 'status': 'success'},
                                 tries=240, delay=30)
        return job_success

    def is_job_test_failed(self, tag_name, project_name):
        job_name = 'test'
        job_obj = self.get_job_obj_by_name(job_name, tag_name, project_name)
        if job_obj is None:
            logger.warning("No job: {0}".format(job_name))
            return False
        status_msg = '[{0}:{1}] Job {2} status: {3}'.format(project_name, tag_name, job_name, job_obj.status)
        if job_obj.status == 'failed':
            logger.warning(status_msg)
            return True
        else:
            logger.info(status_msg)
            return False

    def is_image_available(self, tag_name, project_name):
        build_image_success = self.is_job_build_image_success(tag_name, project_name)
        if build_image_success:
            test_success = self.is_job_test_success(tag_name, project_name)
            if test_success:
                return True
        return False


if __name__ == '__main__':
    pass
