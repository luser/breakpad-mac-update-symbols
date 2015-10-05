#!/usr/bin/python
#
# Dump Breakpad symbol files from binaries in and below a supplied directory.
#

import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile

logger = logging.getLogger('DumpBreakpadSymbols')
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s: %(asctime)s - %(name)s - %(message)s'))
logger.addHandler(handler)

# pattern to match the FUNC section in the Breakpad symbol files
func_pattern = re.compile('FUNC ([^ ]+?) ([^ ]+?) ([^ ]+?) (.*)')

def is_binary_according_to_file(path):
	'''True if this file is a recognized binary executable according to the
	"file" command.
	
	@param path: path to a file to test
	'''
	proc = subprocess.Popen(['file', '-b', '-h', path], stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
	output = "".join([line for line in proc.stdout]).lower()
	
	for executable_type in ['mach-o', 'elf']:
		if executable_type in output:
			return True
		
	return False

def is_binary(path):
	'''True if this file is an executable binary on some platform.  Works
	across platforms, if possible.
	
	@param path: path to a file to test
	'''	
	# Check for a known extension
	_root, extension = os.path.splitext(path)
	if extension.lower() in ['.dylib', '.so', '.pdb']:
		return True
	elif extension is '':
		# Check for a known executable type
		if sys.platform is not 'win32' and is_binary_according_to_file(path):
			return True
		
		# Check to see if it's executable
		if os.access(path, os.X_OK):
			return True
	
	return False 

def demangle_symbols(path):
	'''Demangles the FUNC sections of the provided symbols file using c++filt.
	'''
	temp_path = path + '.unmangled'
	subprocess.check_call('cat "{input}" | c++filt > "{output}"'.format(input=path, output=temp_path), shell=True)
	shutil.move(temp_path, path)
	
def dump_symbols_for_file(dump_syms, input_path, output_dir):
	'''Dumps the Breakpad symbols for the file found at input_path.
		
	@param dump_syms: path to the dump_syms executable
	@param input_path: path to a binary from which to dump symbols
	@param output_dir: directory in which to write the symbols
	'''
	with open(os.devnull, 'w') as devnull:
		
		out = devnull
		if logger.level <= logging.DEBUG:
			out = None
		
		# dump symbols for all possible architectures
		arches = ['i386', 'x86_64', 'ppc'] if sys.platform == 'darwin' else ['all']
		for arch in arches:
			try:
				dump_succeeded = False
				with tempfile.NamedTemporaryFile(delete=False) as temp:
					if sys.platform == 'darwin':
						args = [dump_syms, '-a', arch, input_path]
					else:
						args = [dump_syms, input_path]
					subprocess.check_call(args, stderr=out, stdout=temp)
				
					temp.seek(0)
					module_line = temp.readline()
					if module_line.startswith('MODULE'):
						module_tokens = module_line.split()
						guid = module_tokens[3]
						
						# The name may contain a space, so make sure to keep the spaces
						executable_filename = ' '.join(module_tokens[4:])
						symbol_filename = re.sub('\.pdb$', '', executable_filename) + '.sym'
						
						subdir = os.path.join(output_dir, executable_filename, guid)
						output_path = os.path.join(subdir, symbol_filename)
						if not os.path.exists(subdir):
							os.makedirs(subdir)
						dump_succeeded = True
						
				if dump_succeeded:
					# Move our temporary file
					shutil.move(temp.name, output_path)
	
					# The FUNC sections may not be demangled (at least on Mac)
					if sys.platform != 'win32':
						demangle_symbols(output_path)
						
					logger.info('Dumped {arch} symbols to "{output}".'.format(arch=arch, output=output_path.replace(output_dir, '')[1:]))
			except Exception as e:
				logger.debug(e)
			finally:
				# If it wasn't moved, remove the temp file
				if os.path.exists(temp.name):
					os.unlink(temp.name)

def dump_breakpad_symbols(dump_syms, input_dir, output_dir):
	'''Dumps the breakpad symbols for all executable binaries found in the
	given root directory and outputs all the valid architectures with the
	correct naming conventions to output_dir.
	
	On Mac, the directory tree is structured like:
		output_dir/filename/GUID/filename.sym
	For OSFoundation.dylib, this would then be something like:
		output_dir/OSFoundation.dylib/301EE4F0BD1F7BAECDEF3FC78DC785890/OSFoundation.dylib.sym
	On Windows, we strip the .pdb before appending .sym, so you would have:
		output_dir/OSFoundation.pdb/301EE4F0BD1F7BAECDEF3FC78DC785890/OSFoundation.sym
		
	@param dump_syms: path to the dump_syms executable
	@param input_dir: directory tree to traverse for valid binaries
	@param output_dir: directory in which to write the symbols
	'''
	for root, _folders, files in os.walk(input_dir):
		for filename in files:
			input_path = os.path.join(root, filename)
			if not os.path.islink(input_path) and is_binary(input_path):
				logger.info('Generating symbols for "{input}"'.format(input=input_path.replace(input_dir,'')[1:]))
				dump_symbols_for_file(dump_syms, input_path, output_dir)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Dump Breakpad symbols for all binaries in a directory tree.')
	parser.add_argument('-v', '--verbose', default=0, action='count', help='print detailed information')
	parser.add_argument('--dump_syms', default='dump_syms', type=str, help='path to the Breakpad dump_syms executable')
	parser.add_argument('input', type=str, help='root directory for tree to dump')
	parser.add_argument('output', default='./', type=str, help='destination path for the symbols')
	args = parser.parse_args()
	
	logger.setLevel([logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG][args.verbose])

	dump_breakpad_symbols(args.dump_syms, args.input, args.output)
