#!/usr/bin/env python

import argparse
import gzip
import xml.etree.cElementTree as ET

def open_adv(path):  
    with gzip.open(path, 'r') as f:
        xml = f.read()
    return ET.fromstring(xml)

def get_sample_refs(xml):
    return xml.iter('SampleRef')

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='Manage sample references of Ableton Live device files.')
    argparser.add_argument('devices', help='Device files (.adg and .adv)')

    args = argparser.parse_args()
