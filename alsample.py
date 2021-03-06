#!/usr/bin/env python

import argparse
import errno
import gzip
import os
import re
import shutil
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

def validate_library(path):
    if not os.path.exists(path):
        raise LibraryException('Library path not found.')

    check_path = os.path.join(path, 'Ableton Project Info', 'AbletonLibrary.ini')
    if not os.path.exists(check_path):
        raise LibraryException('Library path does not appear to be a valid Ableton Library.')

def find_presets(path):
    results = []
    for root, dirs, files in os.walk(path):
        for f in files:
            if FILE_TYPES_REGEX.search(f):
                results.append(os.path.join(root, f))
    return results

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def move_file(src, dst):
    if dry_run:
        print('Would move file:\n\tsrc : %s\n\tdest: %s' % (src, dst))
    else:
        print('Moving file:\n\tsrc : %s\n\tdest: %s' % (src, dst))

        #TODO: replace with move after development.
        shutil.copy2(src, dst)
        # shutil.move(src, dest)

def asd(path):
    return '%s.asd' % path

def move_sample(src, dst):
    # Make sure destination dir exists.
    mkdir_p(os.path.dirname(dst))

    # Move sample.
    move_file(src, dst)

    # Move accompanying .asd if it exists.
    src_asd = asd(src)
    if os.path.isfile(src_asd):
        move_file(src_asd, asd(dst))

def split_dirs(path):
    parts = []

    while True:
        path, part = os.path.split(path)
        if not part:
            break
        parts.append(part)

    parts.reverse()
    return parts

def find_samples(xml):
    return list(xml.iter('SampleRef'))

def parse_rel_path(xml):
    parts = [part.get('Dir') for part in xml.findall('RelativePathElement')]
    return os.path.join(*parts)

def rel_path_elements(path):
    parts = split_dirs(path)
    return [ET.Element('RelativePathElement', {'Dir': part}) for part in parts]

def strip_ext(path):
    return os.path.splitext(path)[0]

def sync(preset_path, sample, preset_base, sample_base):
    #TODO Don't assume there is only a single preset referring to this sample.
    preset_rel_path = os.path.relpath(strip_ext(preset_path), args.preset_base)
    print('preset relative path is %s' % preset_rel_path)

    expected_path = os.path.abspath(os.path.join(args.sample_base, preset_rel_path, sample.name))
    print('expected path is %s' % expected_path)
    print('actual path is %s' % sample.abs_path)

    path_is_correct = sample.abs_path == expected_path
    print('correct path? %s' % path_is_correct)

    if not path_is_correct:
        # Move file to correct location.
        move_sample(sample.abs_path, expected_path)

        # Update xml to point to new location.
        ref_path = os.path.relpath(expected_path, library)
        print('ref path %s' % ref_path)
        sample.set_path(ref_path)

class Sample(object):
    def __init__(self, xml):
        self.xml = xml

        file_ref_xml = self.xml.find('FileRef')

        self.name = file_ref_xml.find('Name').get('Value')

        path_type_xml = file_ref_xml.find('RelativePathType')
        self.path_type = int(path_type_xml.get('Value'))

        self.rel_path_xml = file_ref_xml.find('RelativePath')

        # Calculate relative path.
        self.rel_path = os.path.join(
            parse_rel_path(self.rel_path_xml),
            self.name
            )

        # Calculate abs path.
        if self.path_type == PATH_TYPE_LIBRARY:
            self.abs_path = os.path.join(library, self.rel_path)
        #TODO Handle other relative path types?

        # Set if the sample could be found.
        self.exists = os.path.exists(self.abs_path)

    def set_path(self, new_path):
        self.rel_path_xml.clear()
        self.rel_path_xml.extend(rel_path_elements(new_path))
        #print(ET.tostring(self.xml))

class Preset(object):
    def __init__(self, path):
        self.path = path

        # Un-gzip.
        with gzip.open(path, 'r') as f:
            raw_xml = f.read()

        # Parse XML.
        self.xml = ET.fromstring(raw_xml)

        self.samples = [Sample(sample_xml) for sample_xml in find_samples(self.xml)]

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='Manage sample references in Ableton Live file formats.')

    argparser.add_argument('--library', help='Specifies the Ableton Library path. This must be present for any samples that specify library-specific paths.')
    argparser.add_argument('--dry-run', '-n', action='store_true', default=False, help='For any operations that make changes, only print what they would be.')

    subparsers = argparser.add_subparsers(dest='action')

    check_parser = subparsers.add_parser('check', help='Check existence of referenced samples.')
    check_parser.add_argument('file', nargs='+', help='Any Ableton Live files that contain sample references (%s). If given a folder, searches recursively for the files.' % ', '.join(FILE_TYPES))

    sync_parser = subparsers.add_parser('sync', help='Attempt to move samples into a folder structure that mimics that of the presets.')
    sync_parser.add_argument('--preset-base', required=True, help='Specify the base preset directory to use when syncing sample locations.')
    sync_parser.add_argument('--sample-base', required=True, help='Specify the base sample directory to use when syncing sample locations.')
    sync_parser.add_argument('file', nargs='+', help='Any Ableton Live files that contain sample references (%s). If given a folder, searches recursively for the files.' % ', '.join(FILE_TYPES))

    args = argparser.parse_args()

    # Set dry-run
    dry_run = args.dry_run

    # Check to make sure library path provided is valid.
    if args.library:
        validate_library(args.library)
        library = os.path.abspath(args.library)

    # Go through input files and expand folders.
    files = []
    for arg_file in args.file:
        if os.path.isdir(arg_file):
            files += find_presets(arg_file)
        else:
            files.append(arg_file)

    presets = [Preset(file_path) for file_path in files]

    if args.action == 'check':
        for preset in presets:
            print('\nFile %s:' % (preset.path))
            num_samples = len(preset.samples)
            for (i, sample) in enumerate(preset.samples):
                print('\nSample %d/%d, %s, %s' % (i + 1, num_samples, sample.name, sample.abs_path))
                print('Exists: %s' % sample.exists)
    elif args.action == 'sync':
        for preset in presets:
            print('\nFile %s:' % (preset.path))
            num_samples = len(preset.samples)
            for (i, sample) in enumerate(preset.samples):
                print('\nSample %d/%d, %s' % (i + 1, num_samples, sample.name))

                sync(preset.path, sample, args.preset_base, args.sample_base)
