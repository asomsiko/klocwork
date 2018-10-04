#!/usr/bin/env python
############################################################################
# Copyright 2017-2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
############################################################################
# pylint: disable=locally-disabled, invalid-name, no-self-use, relative-import, too-few-public-methods, too-many-arguments, bare-except
"""
Provide interface to interact with Klocwork
"""
import socket
import os
import urllib2
import urllib
import json
import multiprocessing.pool

MAX_PARALLEL_FETCH_COUNT = 20  # maximum number of URL fetch jobs run in parallel


def get_token(host, port, preferred_user=None):
    """
    Return login token and user given Klocwork server address and port.
    User must be authenticated prior with kwauth tool to create token.
    Args:
        host: Klocwork host name (without protocol specified)
        port: Port Klocwork run on a host
        preferred_user: User name for login token

    Returns:
        Klocwork login token
    """
    host = socket.getfqdn(host)  # ensure fully qualified name
    ltoken = os.path.normpath(os.path.expanduser("~/.klocwork/ltoken"))
    with open(ltoken, 'r') as ltoken_file:
        for entry in ltoken_file:
            values = entry.strip().split(';')
            if socket.getfqdn(values[0]) == host and values[1] == str(port):
                if preferred_user and values[2] != preferred_user:
                    continue
                return values[3], values[2]
    return None, None


def strip_path(path, roots):
    """
    Remove path prefix when path starts from given root
    Args:
        path: path to strip.
        roots: roots to strip from a path.

    Returns:
        When path starts from one of a given roots stripped path is returned,
        original path otherwise.
    """
    for root in roots:
        pos = path.rfind(os.sep + os.path.normpath(root) + os.sep)
        if pos >= 0:
            return path[pos:]
    return path


def fetch(url, params, common_params):
    """
    fetch a url given query parameters
    """
    params.update(common_params)
    request = urllib2.Request(url, urllib.urlencode(params))
    response = urllib2.urlopen(request)
    result = []
    for line in response:
        result.append(json.loads(line))
    return result


class MultiFetchHelper(object):
    """
    Worker for multi threaded URL fetching.
    """

    def __init__(self, url):
        """
        Initialize worker for multi threaded URL fetching.
        Args:
            url: URL to fetch from.
        """
        self.url = url

    def fetch(self, params):
        """
        A thread worker function multi threaded URL fetching.
        Can be used with multiprocessing.pool.ThreadPool.
        Args:
            params: URL parameters dictionary.

        Returns:
            A pair <list of response dictionaries, parameters dictionary>
        """
        request = urllib2.Request(self.url, urllib.urlencode(params))
        response = urllib2.urlopen(request)
        result = []
        for line in response:
            result.append(json.loads(line))
        return result


def multifetch(url, params, common_params):
    """
    do multiple fetch operations (one for each item in params)
    """
    for p in params:
        p.update(common_params)
    threads = min(len(params), MAX_PARALLEL_FETCH_COUNT)
    if threads > 0:
        return multiprocessing.pool.ThreadPool(threads).imap_unordered(
            MultiFetchHelper(url).fetch, params)
    return []


class KlocworkWebApi(object):
    """
    Handling Klocwork WEB API requests
    """

    def __init__(self, host, port, preferred_user=None):
        """
        Initialize Klocwork Web API.
        Args:
            host: Klocwork host name (without protocol specified)
            port: Port Klocwork run on a host
            preferred_user: User name to access Klocwork
        """
        self.url = "http://%s:%d/review/api" % (host, port)
        self.ltoken, self.user = get_token(host, port, preferred_user)
        if not self.ltoken:
            raise RuntimeError(
                'Klocwork WEB API login token was not found. '
                'Authenticate with kwauth to fix the problem.\n'
                'Run: kwauth --host {host} --port {port}'.format(
                    host=host, port=port))

    def get_klocwork_issues(self, build, project, project_root):
        """
        Get issues from Klocwork Web server.
        Args:
            build: build name
            project: project name
            project_root: root for relative paths

        Returns: Klocwork issues list of rows dictionaries

        :rtype: list()
        """
        common = {}
        common['user'] = self.user
        common['ltoken'] = self.ltoken

        # request list of issues
        issues_response = fetch(self.url, {
            'action': 'search',
            'project': project,
            'build': build
        }, common)
        # request issues details
        issues_table = {}
        issue_details_requests = []
        for issue in issues_response:
            issues_table[str(issue['id'])] = issue
            issue_details_requests.append({
                'action': 'issue_details',
                'project': project,
                'id': issue['id']
            })
        issues_details_response = multifetch(self.url, issue_details_requests,
                                             common)
        for response in issues_details_response:
            for r in response:
                issues_table[r['id']].update(r)

        issues_table = issues_table.values()
        for issue in issues_table:
            # get the latest comment from the history or leave empty string
            issue['comment'] = issue.get('history', [{}])[0].get('comment', '')
            # Issue is dispositioned if code is not Analyze and comment is not empty
            if not issue['comment'] or issue['code'] == 'Analyze':
                issue['dispositioned'] = 'no'
            else:
                issue['dispositioned'] = 'yes'
            location = os.path.normpath(issue['location'])
            relpath = location
            if project_root:
                try:
                    relpath = os.path.relpath(location, project_root)
                except:
                    pass

            issue['location'] = relpath.replace('\\', '/')
        return issues_table

    def get_klocwork_checkers(self, project):
        """Get info on checkers in Klocwork"""
        common = {}
        common['user'] = self.user
        common['ltoken'] = self.ltoken
        response = fetch(self.url, {
            'action': 'defect_types',
            'project': project
        }, common)
        return response
