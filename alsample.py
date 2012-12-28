#!/usr/bin/env python

import argparse
import gzip
import os
import xml.etree.cElementTree as ET

PATH_TYPES = {
    'MISSING': 0,
    'EXTERNAL': 1,
    'LIBRARY': 2,
    'CURRENT_PROJECT': 3
}

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

    library_check_path = os.path.join(library_path, 'Ableton Project Info')
    if not os.path.exists(library_check_path):
        raise LibraryException('Library path does not appear to be a valid Ableton Library.')

class Sample(object):
    def __init__(self, xml):
        self.xml = xml
        self.file_ref_xml = xml.find('FileRef')
        self.relative_path_xml = self.file_ref_xml.find('RelativePath')
        self.path_hint_xml = self.file_ref_xml.find('./SearchHint/PathHint')

        # Calculate library path.
        relative_path_elements = [path_element.get('Dir') for path_element in self.relative_path_xml.findall('RelativePathElement')]
        relative_path_elements.append(self.file_ref_xml.find('Name').get('Value'))
        self.library_path = '/'.join(relative_path_elements)

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='Manage sample references in Ableton Live file formats.')
    argparser.add_argument('file', nargs='+', help='Any files that contain sample references.')
    argparser.add_argument('--list', '-l', action='store_true', help='List referenced samples.')
    argparser.add_argument('--library', help='Specifies the Ableton Library path. This must be present for any samples that specify library-specific paths.')

    args = argparser.parse_args()

    if not args.list:
        print('Nothing to do.')
        exit(1)

    # Check to make sure library path provided is valid.
    if args.library:
        validate_library_path(args.library)

    for filePath in args.file:
        file_xml = open_file(filePath)
        samples = [Sample(sample_xml) for sample_xml in get_sample_refs(file_xml)]

        if args.list:
            for sample in samples:
                print(sample.library_path)
