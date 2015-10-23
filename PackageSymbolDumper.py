#!/usr/bin/env python
# Copyright 2015 Michael R. Miller. See the LICENSE
# file at the top-level directory of this distribution.
'''
PackageSymbolDumper.py

Dumps Breakpad symbols for the contents of an Apple update installer.  Given a
path to an Apple update installer as a .dmg or a path to a specific package
within the disk image, PackageSymbolDumper mounts, traverses, and dumps symbols
for all applicable frameworks and dylibs found within.

Required tools for Linux:
    pax
    gzip
    tar
    xar (http://code.google.com/p/xar/)
    xpwn's dmg (https://github.com/planetbeing/xpwn)

Created on Apr 11, 2012

@author: mrmiller
'''
import argparse
import concurrent.futures
import errno
import logging
import os
import shutil
import subprocess
import sys
import tempfile

from scrapesymbols.gathersymbols import process_paths

def mount_dmg(dmg_extractor, path, mount_point):
    '''
    Mount a disk image at a given mount point.

    @param path: a path to the disk image file (.dmg)
    @param mount_point: path at which the image should be mounted

    @raise subprocess.CalledProcessError if there is an error mounting
    '''
    if sys.platform == 'darwin':
        subprocess.check_call(['hdiutil', 'attach', path, '-nobrowse', '-mountpoint', mount_point, '-plist'])
    else:
        with tempfile.NamedTemporaryFile() as f:
            subprocess.check_call([dmg_extractor, 'extract', path, f.name])
            subprocess.check_call(['mount', '-o', 'loop', f.name, mount_point])

def unmount_dmg(mount_point):
    '''
    Unmount a mounted disk image given its mount point.

    @param mount_point: path where the image is mounted, e.g. "/Volumes/test"

    @raise subprocess.CalledProcessError if there is an error unmounting
    '''
    if sys.platform == 'darwin':
        subprocess.check_call(['hdiutil', 'detach', mount_point])
    else:
        subprocess.check_call(['umount', mount_point])

def expand_pkg(pkg_path, out_path):
    '''
    Expands the contents of an installer package to some directory.

    @param pkg_path: a path to an installer package (.pkg)
    @param out_path: a path to hold the package contents
    '''
    subprocess.check_call('cd "{dest}" && xar -x -f "{src}"'.format(src=pkg_path, dest=out_path), shell=True)

def filter_files(function, path):
    '''
    Yield file paths matching a filter function by walking the
    hierarchy rooted at path.

    @param function: a function taking in a filename that returns true to
        include the path
    @param path: the root path of the hierarchy to traverse
    '''
    for root, _dirs, files in os.walk(path):
        for filename in files:
            if function(filename):
                yield os.path.join(root, filename)

def find_packages(path):
    '''
    Returns a list of installer packages (as determined by the .pkg extension)
    found within path.

    @param path: root path to search for .pkg files
    '''
    return filter_files(lambda filename:
                            os.path.splitext(filename)[1] == '.pkg',
                        path)

def find_all_packages(paths):
    '''
    Yield installer package files found in all of `paths`.

    @param path: list of root paths to search for .pkg files
    '''
    for path in paths:
        for pkg in find_packages(path):
            yield pkg

def find_payloads(path):
    '''
    Returns a list of possible installer package payload paths.

    @param path: root path for an installer package
    '''
    return filter_files(lambda filename:
                            'Payload' in filename or '.pax.gz' in filename,
                        path)

def extract_payload(payload_path, output_path):
    '''
    Extracts the contents of an installer package payload to a given directory.

    @param payload_path: path to an installer package's payload
    @param output_path: output path for the payload's contents
    @return True for success, False for failure.
    '''
    header = open(payload_path, 'rb').read(2)
    if header == 'BZ':
        extract = 'bzip2'
    elif header == '\x1f\x8b':
        extract = 'gzip'
    else:
        # Unsupported format
        logging.error('Unknown payload format: 0x{0:x}{1:x}'.format(ord(header[0]), ord(header[1])))
        return False
    try:
        # XXX: This sucks because if the extraction fails pax will hang with
        # a prompt instead of just failing.
        subprocess.check_call('cd {dest} && {extract} -dc {payload} | pax -r -k -s ":^/::"'.format(extract=extract, payload=payload_path, dest=output_path), shell=True)
        return True
    except subprocess.CalledProcessError:
        return False


def shutil_error_handler(caller, path, excinfo):
    logging.error('Could not remove "{path}": {info}'.format(path=path, info=excinfo))


def write_symbol_file(dest, filename, contents):
    full_path = os.path.join(dest, filename)
    try:
        os.makedirs(os.path.dirname(full_path))
        open(full_path, 'wb').write(contents)
    except os.error as e:
        if e.errno != errno.EEXIST:
            raise

def dump_symbols_from_payload(executor, dump_syms, payload_path, dest):
    '''
    Dumps all the symbols found inside the payload of an installer package.

    @param dump_syms: path to the dump_syms executable
    @param payload_path: path to an installer package's payload
    @param dest: output path for symbols
    '''
    temp_dir = None
    logging.info('Dumping symbols from payload: ' + payload_path)
    try:
        temp_dir = tempfile.mkdtemp()
        logging.info('Extracting payload to {path}.'.format(path=temp_dir))
        if not extract_payload(payload_path, temp_dir):
            logging.error('Could not extract payload: ' + payload_path)
            return

        # dump the symbols for the payload contents
        system_library = os.path.join('System', 'Library')
        subdirectories = [os.path.join(system_library, 'Frameworks'), os.path.join(system_library, 'PrivateFrameworks'), os.path.join('usr', 'lib')]
        paths_to_dump = map(lambda d: os.path.join(temp_dir, d), subdirectories)

        for filename, contents in process_paths(paths_to_dump, executor, dump_syms, False, platform='darwin'):
            if filename and contents:
                write_symbol_file(dest, filename, contents)

    finally:
        if temp_dir is not None:
            shutil.rmtree(temp_dir, onerror=shutil_error_handler)

def dump_symbols_from_package(executor, dump_syms, pkg, dest):
    '''
    Dumps all the symbols found inside an installer package.

    @param dump_syms: path to the dump_syms executable
    @param pkg: path to an installer package
    @param dest: output path for symbols
    '''
    temp_dir = None
    logging.info('Dumping symbols from package: ' + pkg)
    try:
        temp_dir = tempfile.mkdtemp()
        expand_pkg(pkg, temp_dir)

        # check for any subpackages
        for subpackage in find_packages(temp_dir):
            logging.warning('UNTESTED: Found subpackage at: ' + subpackage)
            dump_symbols_from_package(executor, dump_syms, subpackage, dest)

        # dump symbols from any payloads (only expecting one) in the package
        for payload in find_payloads(temp_dir):
            dump_symbols_from_payload(executor, dump_syms, payload, dest)

    finally:
        if temp_dir is not None:
            shutil.rmtree(temp_dir, onerror=shutil_error_handler)


def read_processed_packages(tracking_file):
    if tracking_file is None or not os.path.exists(tracking_file):
        return set()

    return set(open(tracking_file, 'rb').read().splitlines())


def write_processed_packages(tracking_file, processed_packages):
    if tracking_file is None:
        return

    open(tracking_file, 'wb').write('\n'.join(processed_packages))


def main(args):
    if not args.search or not all(os.path.exists(p) for p in args.search):
        logging.error('Invalid search path')
        return
    if not os.path.exists(args.to):
        logging.error('Invalid path to destination')
        return

    processed_packages = read_processed_packages(args.tracking_file)
    executor = concurrent.futures.ProcessPoolExecutor()
    for pkg in find_all_packages(args.search):
        if pkg not in processed_packages:
            dump_symbols_from_package(executor, args.dump_syms, pkg, args.to)
            processed_packages.add(pkg)
            write_processed_packages(args.tracking_file, processed_packages)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Extracts Breakpad symbols from a Mac OS X support update.')
    parser.add_argument('--dmg', default='dmg', type=str,
                        help='path to the xpwn dmg extractor, ' +
                        'if running on Linux')
    parser.add_argument('--dump_syms', default='dump_syms', type=str,
                        help='path to the Breakpad dump_syms executable')
    parser.add_argument('--tracking-file', type=str,
                        help='Path to a file in which to store information ' +
                        'about already-processed packages')
    parser.add_argument('search', nargs='+',
                        help='Paths to search recursively for packages')
    parser.add_argument('to', type=str, help='destination path for the symbols')
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.DEBUG)

    main(args)
