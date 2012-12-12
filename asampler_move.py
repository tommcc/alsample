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

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='Manage sample references of Ableton Live device files.')
    argparser.add_argument('device', nargs='+', help='Device files (.adg and .adv)')

    args = argparser.parse_args()

    for devicePath in args.device:
        device = open_device(devicePath)
        sample_refs = get_sample_refs(device)
        for sample_ref in sample_refs:
            sample = Sample(sample_ref)
            print(sample)
