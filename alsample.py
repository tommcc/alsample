#!/usr/bin/env python

import argparse
import gzip
import os
import re
import xml.etree.cElementTree as ET

PATH_TYPE_MISSING = 0
PATH_TYPE_EXTERNAL = 1
PATH_TYPE_LIBRARY = 2
PATH_TYPE_CURRENT_PROJECT = 3

PATH_TYPE_LABELS = [
    'Missing',
    'External',
    'Library',
    'Current Project'
]

FILE_TYPES = [
    'adv',
    'adg',
    'alc',
    'als'
]

FILE_TYPES_REGEX = re.compile(
    '\.(%s)$' % '|'.join(FILE_TYPES),
    re.IGNORECASE
)

class LibraryException(Exception):
    pass

def find_files(path):
    results = []
    for root, dirs, files in os.walk(path):
        #print ('root %s, dirs %s, files %s' % (root, dirs, files))
        for f in files:
            if FILE_TYPES_REGEX.search(f):
                results.append(os.path.join(root, f))
    return results

def open_file(path):  
    with gzip.open(path, 'r') as f:
        xml = f.read()
    return ET.fromstring(xml)

def get_sample_refs(xml):
    return list(xml.iter('SampleRef'))

def validate_library_path(library_path):
    if not os.path.exists(library_path):
        raise LibraryException('Library path not found.')

    library_check_path = os.path.join(library_path, 'Ableton Project Info', 'AbletonLibrary.ini')
    if not os.path.exists(library_check_path):
        raise LibraryException('Library path does not appear to be a valid Ableton Library.')

class Sample(object):
    def __init__(self, xml, library=''):
        self.xml = xml
        self.library = library

        self.file_ref_xml = xml.find('FileRef')

        self.name = self.file_ref_xml.find('Name').get('Value')

        self.relative_path_type_xml = self.file_ref_xml.find('RelativePathType')
        self.relative_path_type = int(self.relative_path_type_xml.get('Value'))

        self.relative_path_xml = self.file_ref_xml.find('RelativePath')

        # Calculate relative path.
        relative_path_elements = [path_element.get('Dir') for path_element in self.relative_path_xml.findall('RelativePathElement')]
        relative_path_elements.append(self.name)
        self.relative_path = os.path.join(*relative_path_elements)

        # Calculate abs path.
        if self.relative_path_type == PATH_TYPE_LIBRARY:
            self.absolute_path = os.path.abspath(os.path.join(self.library, self.relative_path))

        self.path_hint_xml = self.file_ref_xml.find('./SearchHint/PathHint')

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='Manage sample references in Ableton Live file formats.')

    argparser.add_argument('--library', help='Specifies the Ableton Library path. This must be present for any samples that specify library-specific paths.')

    subparsers = argparser.add_subparsers(dest='action')

    check_parser = subparsers.add_parser('check', help='Check existence of referenced samples.')

    sync_parser = subparsers.add_parser('sync', help='Attempt to move samples into a folder structure that mimics that of the presets. Requires the --sample-base and --preset-base paths to be set.')
    sync_parser.add_argument('--preset-base', required=True, help='Specify the base preset directory to use when syncing sample locations.')
    sync_parser.add_argument('--sample-base', required=True, help='Specify the base sample folder to use when syncing sample locations.')

    argparser.add_argument('file', nargs='+', help='Any files that contain sample references.')

    args = argparser.parse_args()

    # Go through input files and expand folders.
    files = []
    for file_path in args.file:
        if os.path.isdir(file_path):
            files += find_files(file_path)
        else:
            files.append(file_path)

    # Check to make sure library path provided is valid.
    if args.library:
        validate_library_path(args.library)

    samples_by_file = {}

    for file_path in files:
        file_xml = open_file(file_path)
        samples = [Sample(sample_xml, library=args.library) for sample_xml in get_sample_refs(file_xml)]
        samples_by_file[file_path] = samples

    if args.action == 'check':
        for (file_path, samples) in samples_by_file.items():
            print('\nFile %s:' % (file_path))
            num_samples = len(samples)
            for (i, sample) in enumerate(samples):
                print('\nSample %d/%d, %s, %s' % (i + 1, num_samples, sample.name, sample.absolute_path))
                exists = os.path.exists(sample.absolute_path)
                print('Exists: %s' % exists)
