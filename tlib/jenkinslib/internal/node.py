# !/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#                                                        version: v1.0.0
#                                                             by: Tao.Xu
#                                                           date: 5/28/2019
#                                                      copyright: N/A
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NO INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
##############################################################################

"""
This module provides Node object.
"""

from tlib.jenkinslib.internal import base


class Node(base.JenkinsBase):
    """Represents a node."""
    def __init__(self, url, name, jenkins):
        """initialize Node object.

        Args:
            url: url of node.
            name: name of node.
            node: Node object.
        """
        self.name = name
        self.jenkins = jenkins
        super(Node, self).__init__(url, static=jenkins.is_static)

    def get_jenkins_obj(self):
        """get object of current jenkins."""
        return self.jenkins

    def __str__(self):
        return self.name

    @property
    def is_online(self):
        """node is online or not."""
        return not self.poll(tree="offline")["offline"]

    @property
    def is_temporarily_offline(self):
        """node is temporarily offline or not."""
        return not self.poll(tree="temporarilyOffline")["temporarilyOffline"]

    @property
    def is_idle(self):
        """node is idle or not."""
        return self.poll(tree="idle")["idle"]

