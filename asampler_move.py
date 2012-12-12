#!/usr/bin/env python

import argparse
import gzip
import xml.etree.cElementTree as ET

def open_device(path):  
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

class Device(object):
    def __init__(self, xml):
        self.xml = xml
        self.samples = [Sample(sample_xml) for sample_xml in get_sample_refs(self.xml)]

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='Manage sample references of Ableton Live device files.')
    argparser.add_argument('device', nargs='+', help='Device files (.adg and .adv)')

    args = argparser.parse_args()

    for devicePath in args.device:
        device_xml = open_device(devicePath)
        device = Device(device_xml)

        for sample in device.samples:
            print(sample.library_path)
