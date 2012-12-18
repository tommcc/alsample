#!/usr/bin/env python

import argparse
import gzip
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

def open_file(path):  
    with gzip.open(path, 'r') as f:
        xml = f.read()
    return ET.fromstring(xml)

def get_sample_refs(xml):
    return list(xml.iter('SampleRef'))

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

    args = argparser.parse_args()

    for filePath in args.file:
        file_xml = open_file(filePath)
        samples = [Sample(sample_xml) for sample_xml in get_sample_refs(file_xml)]

        for sample in samples:
            print(sample.library_path)
