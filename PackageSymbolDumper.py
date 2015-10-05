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
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from DumpBreakpadSymbols import dump_breakpad_symbols

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
    Returns a list of file paths matching a filter function by walking the
    hierarchy rooted at path.
    
    @param function: a function taking in a filename that returns true to
        include the path
    @param path: the root path of the hierarchy to traverse
    '''
    filtered_files = []
    for root, _dirs, files in os.walk(path):
        paths = map(lambda filename:os.path.join(root, filename), files)
        filtered_files.extend(filter(function, paths))
    return filtered_files
        
def find_packages(path):
    '''
    Returns a list of installer packages (as determined by the .pkg extension)
    found within path.
    
    @param path: root path to search for .pkg files
    '''
    return filter_files(lambda filename:
                            os.path.splitext(filename)[1] == '.pkg',
                        path)
    
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
    '''
    subprocess.check_call('cd {dest} && bzcat {gzip} | pax -r -k -s ":^/::"'.format(gzip=payload_path, dest=output_path), shell=True)

def dump_symbols(dump_syms, root, dest):
    '''
    Dumps Breakpad symbols from a directory tree based at root using dump_syms.
    
    @param dump_syms: path to the dump_syms executable
    @param root: the root directory of the hierarchy to walk for binaries
    @param dest: the destination directory for the Breakpad symbols
    '''
    dump_breakpad_symbols(dump_syms, root, dest)

def shutil_error_handler(caller, path, excinfo):
    logging.error('Could not remove "{path}": {info}'.format(path=path, info=excinfo))

def dump_symbols_from_payload(dump_syms, payload_path, dest):
    '''
    Dumps all the symbols found inside the payload of an installer package.
    
    @param dump_syms: path to the dump_syms executable
    @param payload_path: path to an installer package's payload
    @param dest: output path for symbols
    '''
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        logging.info('Extracting payload to {path}.'.format(path=temp_dir))
        extract_payload(payload_path, temp_dir)

        # dump the symbols for the payload contents
        system_library = os.path.join('System', 'Library')
        subdirectories = [os.path.join(system_library, 'Frameworks'), os.path.join(system_library, 'PrivateFrameworks'), os.path.join('usr', 'lib')]
        paths_to_dump = map(lambda d: os.path.join(temp_dir, d), subdirectories)
        for path in paths_to_dump:
            if os.path.exists(path):
                dump_symbols(dump_syms, path, dest)
    finally:
        if temp_dir is not None:
            shutil.rmtree(temp_dir, onerror=shutil_error_handler)

def dump_symbols_from_package(dump_syms, pkg, dest):
    '''
    Dumps all the symbols found inside an installer package.
    
    @param dump_syms: path to the dump_syms executable
    @param pkg: path to an installer package
    @param dest: output path for symbols
    '''
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        expand_pkg(pkg, temp_dir)
        
        # check for any subpackages
        subpackages = find_packages(temp_dir)
        for subpackage in subpackages:
            logging.warning('UNTESTED: Found subpackage at: ' + ',\n'.join(subpackage))
            dump_symbols_from_package(dump_syms, subpackage, dest)
        
        # dump symbols from any payloads (only expecting one) in the package
        payloads = find_payloads(temp_dir)
        logging.info('Found payloads at: ' + ',\n'.join(payloads))
        for payload in payloads:
            dump_symbols_from_payload(dump_syms, payload, dest)
            
    finally:
        if temp_dir is not None:
            shutil.rmtree(temp_dir, onerror=shutil_error_handler)

def main(args):
    if not os.path.exists(args.updater):
        logging.error('Invalid path to update disk image or package')
        return
    if not os.path.exists(args.to):
        logging.error('Invalid path to destination')
        return
    
    mount_point = None
    
    try:
        # if the updater path points to a dmg (as determined by its extension),
        # mount the image and find any possible packages inside
        if os.path.splitext(args.updater)[1] == '.dmg':
            mount_point = tempfile.mkdtemp()
            mount_dmg(args.dmg, args.updater, mount_point)
            pkg_paths = find_packages(mount_point)
        else:
            pkg_paths = [args.updater]
            
        logging.info('Found packages at: ' + ',\n'.join(pkg_paths))
        
        for pkg in pkg_paths:
            dump_symbols_from_package(args.dump_syms, pkg, args.to)
    finally:
        # if we mounted an image, unmount it and delete the temp mount point
        if mount_point is not None:
            try:
                unmount_dmg(mount_point)
            except:
                pass
            finally:
                os.rmdir(mount_point)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extracts Breakpad symbols from a Mac OS X support update.')
    parser.add_argument('-s', '--search', default='./', type=str, help='a comma-separated list of relative paths (including their subdirectories) to search')
    parser.add_argument('--dmg', default='dmg', type=str, help='path to the xpwn dmg extractor, if running on Linux')
    parser.add_argument('--dump_syms', default='dump_syms', type=str, help='path to the Breakpad dump_syms executable')
    parser.add_argument('updater', type=str, help='path to an updater dmg or a pkg')
    parser.add_argument('to', default='./', type=str, help='destination path for the symbols')
    args = parser.parse_args()
    
    logging.getLogger().setLevel(logging.DEBUG)

    main(args)
