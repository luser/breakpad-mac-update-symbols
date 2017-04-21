#!/bin/env python
# Copyright 2015 Ted Mielczarek. See the LICENSE
# file at the top-level directory of this distribution.
'''
This script triggers taskcluster tasks to scrape symbols out of Apple
system updates and upload them to crash-stats.mozilla.com.
'''

from __future__ import print_function

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


def spawn_task(queue, keys, decision_task_id, template_file):
    task_id = taskcluster.utils.slugId()
    with open(local_file(template_file), 'rb') as template:
        payload = fill_template(template, keys)
        if decision_task_id and not payload.get('dependencies'):
            payload['dependencies'] = [decision_task_id]
        queue.createTask(task_id, payload)
    return task_id


def main():
    decision_task_id = os.environ.get('TASK_ID')
    if decision_task_id:
        task_group_id = decision_task_id
        options = {'baseUrl': 'http://taskcluster/queue/v1/'}
    else:
        task_group_id = taskcluster.utils.slugId()
        options = {'credentials': read_tc_auth()}
    now = datetime.datetime.utcnow()
    keys = {
        'task_group_id': task_group_id,
        'task_created': format_timedelta(now),
        'task_deadline': format_timedelta(now, hours=8),
        'artifacts_expires': format_timedelta(now, days=1),
    }
    queue = taskcluster.Queue(options)
    fetch_task_id = spawn_task(queue, keys, decision_task_id, "fetch-task.json")
    keys['fetch_task_id'] = fetch_task_id
    spawn_task(queue, keys, decision_task_id, "upload-task.json")
    print('https://tools.taskcluster.net/task-group-inspector/#/' + task_group_id)


if __name__ == '__main__':
    main()
