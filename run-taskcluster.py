#!/bin/env python
# Copyright 2015 Ted Mielczarek. See the LICENSE
# file at the top-level directory of this distribution.
'''
This script triggers taskcluster tasks to scrape symbols out of Apple
system updates and upload them to crash-stats.mozilla.com.
'''

from __future__ import print_function

import argparse
import datetime
import json
import os
import taskcluster

import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()


def local_file(filename):
    '''
    Return a path to a file next to this script.
    '''
    return os.path.join(os.path.dirname(__file__), filename)


def read_tc_auth(tc_auth_file):
    '''
    Read taskcluster credentials from tc_auth_file and return them as a dict.
    '''
    return json.load(open(tc_auth_file, 'rb'))


def fill_template_property(val, keys):
    if isinstance(val, basestring) and '{' in val:
         return val.format(**keys)
    elif isinstance(val, dict):
        return fill_template_dict(val, keys)
    elif isinstance(val, list):
        return fill_template_list(val, keys)
    return val


def fill_template_list(l, keys):
    return [fill_template_property(v, keys) for v in l]


def fill_template_dict(d, keys):
    for key, val in d.items():
        d[key] = fill_template_property(val, keys)
    return d


def fill_template(template_file, keys):
    '''
    Take the file object template_file, parse it as JSON, and
    interpolate (using str.template) its keys using keys.
    '''
    template = json.load(template_file)
    return fill_template_dict(template, keys)


def format_timedelta(d, **kwargs):
    if kwargs:
        d = d + datetime.timedelta(**kwargs)
    return d.isoformat() + 'Z'


def spawn_task_graph(scheduler):
    '''
    Spawn a Taskcluster task graph in scheduler.
    '''
    graph_id = taskcluster.utils.slugId()
    keys = {}
    for i in range(2):
        keys['task_id_{}'.format(i)] = taskcluster.utils.slugId()
    with open(local_file('task.json'), 'rb') as template:
        now = datetime.datetime.utcnow()
        keys['task_created'] = format_timedelta(now)
        keys['task_deadline'] = format_timedelta(now, hours=5)
        keys['artifacts_expires'] = format_timedelta(now, days=1)
        payload = fill_template(template, keys)
    scheduler.createTaskGraph(graph_id, payload)
    return graph_id


def main():
    parser = argparse.ArgumentParser(
        description='Scrape and upload OS X system symbols')
    parser.add_argument('taskcluster_auth',
                        help='Path to a file containing Taskcluster client' +
                        ' ID and authentication token as a JSON file in the' +
                        ' form {"clientId": "...", "accessToken": "..."}')

    args = parser.parse_args()
    tc_auth = read_tc_auth(args.taskcluster_auth)
    scheduler = taskcluster.Scheduler({'credentials': tc_auth})
    graph_id = spawn_task_graph(scheduler)
    u = 'https://tools.taskcluster.net/task-graph-inspector/#{0}/'.format(
        graph_id
    )
    print(u)


if __name__ == '__main__':
    main()
