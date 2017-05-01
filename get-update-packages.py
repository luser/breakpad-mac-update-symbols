#!/usr/bin/env python

import argparse
import logging
import os
import re
import requests
import urlparse

OSX_RE = re.compile(r'10\.[0-9]+\.[0-9]+')

def get_update_packages():
    for i in xrange(16):
        url = 'https://km.support.apple.com/kb/index?page=downloads_browse&sort=recency&facet=all&category=PF6&locale=en_US&offset=%d' % i
        res = requests.get(url)
        if res.status_code != 200:
            break
        data = res.json()
        downloads = data.get('downloads', [])
        if not downloads:
            break
        for d in downloads:
            title = d.get('title', '')
            if OSX_RE.search(title) and 'Combo' not in title:
                logging.info('Title: ' + title)
                if 'fileurl' in d:
                    yield d['fileurl']
                else:
                    log.warn('No fileurl in download!')

def fetch_url_to_file(url, download_dir):
    filename = os.path.basename(urlparse.urlsplit(url).path)
    local_filename = os.path.join(download_dir, filename)
    r = requests.get(url, stream=True)
    res_len = int(r.headers.get('content-length', '0'))
    logging.info('Downloading {} -> {} ({} bytes)'.format(url, local_filename, res_len))
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)

def main():
    parser = argparse.ArgumentParser(
        description='Download OS X update packages')
    parser.add_argument('to', type=str, help='destination path for packages')
    args = parser.parse_args()
    logging.getLogger().setLevel(logging.DEBUG)
    for p in ('requests.packages.urllib3.connectionpool', 'urllib3'):
        urllib3_logger = logging.getLogger(p)
        urllib3_logger.setLevel(logging.ERROR)
    for url in get_update_packages():
        fetch_url_to_file(url, args.to)

if __name__ == '__main__':
    main()
