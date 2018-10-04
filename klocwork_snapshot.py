#!/usr/bin/env python
#
# Copyright 2018 Intel Corporation
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
"""Get the snapshot of the Klocwork issues disposition
"""

import sys
import csv
import argparse
from lib import klocwork


def main():
    """Main entry point
    """
    parser = argparse.ArgumentParser(
        description='Get the snapshot of the Klocwork issues disposition',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--host', help='Klocwork server host')
    parser.add_argument('--port', type=int, help='Klocwork server port')
    parser.add_argument('--license_host', help='Klocwork license server host')
    parser.add_argument(
        '--license_port', type=int, help='Klocwork license server port')
    parser.add_argument(
        '--user',
        default=None,
        help='User name. Must be authenticated prior with kwauth tool.')
    parser.add_argument('project', help='Klocwork project name')
    parser.add_argument('build', help='Klocwork build')
    args = parser.parse_args()

    # Get Klocwork Web based API
    kw_api = klocwork.KlocworkWebApi(args.host, args.port, args.user)
    # Download issues found
    issues_table = kw_api.get_klocwork_issues(args.build, args.project, None)
    # Write Report
    writer = csv.writer(sys.stdout, dialect='excel')
    fields = [
        'id', 'dispositioned', 'code', 'severity', 'status', 'location',
        'name', 'url', 'comment'
    ]
    writer.writerow(fields)
    for row in issues_table:
        writer.writerow([row.get(field, '') for field in fields])


if __name__ == "__main__":
    main()
