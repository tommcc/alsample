#!/usr/bin/env python

import argparse
import gzip
import os
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

class LibraryException(Exception):
    pass

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

        self.relative_path_type_xml = self.file_ref_xml.find('RelativePathType')
        self.relative_path_type = int(self.relative_path_type_xml.get('Value'))

        self.relative_path_xml = self.file_ref_xml.find('RelativePath')

        # Calculate relative path.
        relative_path_elements = [path_element.get('Dir') for path_element in self.relative_path_xml.findall('RelativePathElement')]
        relative_path_elements.append(self.file_ref_xml.find('Name').get('Value'))
        self.relative_path = os.path.join(*relative_path_elements)

        # Calculate abs path.
        if self.relative_path_type == PATH_TYPE_LIBRARY:
            self.absolute_path = os.path.abspath(os.path.join(self.library, self.relative_path))

        self.path_hint_xml = self.file_ref_xml.find('./SearchHint/PathHint')

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='Manage sample references in Ableton Live file formats.')
    argparser.add_argument('file', nargs='+', help='Any files that contain sample references.')
    argparser.add_argument('--list', action='store_true', help='List all referenced samples.')
    argparser.add_argument('--check', action='store_true', help='Check existence of referenced samples.')
    argparser.add_argument('--library', help='Specifies the Ableton Library path. This must be present for any samples that specify library-specific paths.')

    args = argparser.parse_args()

    if not (args.list or args.check):
        exit('Nothing to do.')

    # Check to make sure library path provided is valid.
    if args.library:
        validate_library_path(args.library)

    for filePath in args.file:
        file_xml = open_file(filePath)
        samples = [Sample(sample_xml, library=args.library) for sample_xml in get_sample_refs(file_xml)]

        if args.list or args.check:
            for (i, sample) in enumerate(samples):
                print('\nSample %d' % (i + 1))
                print('Path type: %s' % PATH_TYPE_LABELS[sample.relative_path_type])
                print(sample.relative_path)
                print(sample.absolute_path)

        if args.check:
            for (i, sample) in enumerate(samples):
                print('\nSample %d' % (i + 1))
                print('Path type: %s' % PATH_TYPE_LABELS[sample.relative_path_type])
                print(sample.relative_path)
                print(sample.absolute_path)
                exists = os.path.exists(sample.absolute_path)
                print('Exists: %s' % exists)
