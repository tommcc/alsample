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

def sample_refs(xml):
    return list(xml.iter('SampleRef'))

def validate_library_path(library_path):
    if not os.path.exists(library_path):
        raise LibraryException('Library path not found.')

    library_check_path = os.path.join(library_path, 'Ableton Project Info', 'AbletonLibrary.ini')
    if not os.path.exists(library_check_path):
        raise LibraryException('Library path does not appear to be a valid Ableton Library.')

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def move_file(src, dest):
    if dry_run:
        print('Would move file:\n\tsrc : %s\n\tdest: %s' % (src, dest))
    else:
        print('Moving file:\n\tsrc : %s\n\tdest: %s' % (src, dest))

        # Create destination directory if needed.
        dest_path = os.path.split(dest)[0]
        mkdir_p(dest_path)

        #shutil.move(src, dest)
        #TODO: replace with move after development.
        shutil.copy2(src, dest)

def asd(path):
    return '%s.asd' % path

def move_sample(src, dest):
    move_file(src, dest)

    # Move accompanying .asd if it exists.
    src_asd = asd(src)
    if os.path.isfile(src_asd):
        move_file(src_asd, asd(dest))

def split_dirs(path):
    parts = []

    while True:
        path, part = os.path.split(path)
        if not part:
            break
        parts.append(part)

    parts.reverse()
    return parts

def parse_rel_path(path_xml):
    parts = [part.get('Dir') for part in path_xml.findall('RelativePathElement')]
    return os.path.join(*parts)

def rel_path_elements(path):
    parts = split_dirs(path)
    return [ET.Element('RelativePathElement', {'Dir': part}) for part in parts]

def sync(preset_path, sample, preset_base, sample_base):
    preset_relative_path = os.path.relpath(file_path, args.preset_base)
    # Strip extension from preset name
    preset_relative_path = os.path.splitext(preset_relative_path)[0]
    print('preset relative path is %s' % preset_relative_path)

    sample_tail = os.path.split(sample.relative_path)[1]
    expected_path = os.path.join(args.sample_base, preset_relative_path, sample_tail)
    expected_path = os.path.abspath(expected_path)
    print('expected path is %s' % expected_path)
    print('actual path is %s' % sample.absolute_path)

    path_is_correct = sample.absolute_path == expected_path
    print('correct path? %s' % path_is_correct)

    if not path_is_correct:
        # Move file to correct location.
        move_sample(sample.absolute_path, expected_path)

        # Update xml to point to new location.
        sample.set_path(expected_path)


class Sample(object):
    def __init__(self, xml, library=''):
        self.xml = xml
        self.library = library

        self.file_ref_xml = self.xml.find('FileRef')

        self.name_xml = self.file_ref_xml.find('Name')
        self.name = self.name_xml.get('Value')

        self.path_type_xml = self.file_ref_xml.find('RelativePathType')
        self.path_type = int(self.path_type_xml.get('Value'))

        self.relative_path_xml = self.file_ref_xml.find('RelativePath')

        # Calculate relative path.
        self.relative_path = os.path.join(
            parse_rel_path(self.relative_path_xml),
            self.name
            )

        # Calculate abs path.
        if self.path_type == PATH_TYPE_LIBRARY:
            self.absolute_path = os.path.abspath(os.path.join(self.library, self.relative_path))
        #TODO Handle other relative path types?

        # Set if the sample could be found.
        self.exists = os.path.exists(self.absolute_path)

    def set_path(self, new_path):
        self.relative_path_xml.clear()
        self.relative_path_xml.extend(rel_path_elements(new_path))
        print(ET.tostring(self.xml))

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='Manage sample references in Ableton Live file formats.')

    argparser.add_argument('--library', help='Specifies the Ableton Library path. This must be present for any samples that specify library-specific paths.')
    argparser.add_argument('--dry-run', '-n', action='store_true', default=False, help='For any operations that make changes, only print what they would be.')

    subparsers = argparser.add_subparsers(dest='action')

    check_parser = subparsers.add_parser('check', help='Check existence of referenced samples.')
    check_parser.add_argument('file', nargs='+', help='Any files that contain sample references.')

    sync_parser = subparsers.add_parser('sync', help='Attempt to move samples into a folder structure that mimics that of the presets. Requires the --sample-base and --preset-base paths to be set.')
    sync_parser.add_argument('--preset-base', required=True, help='Specify the base preset directory to use when syncing sample locations.')
    sync_parser.add_argument('--sample-base', required=True, help='Specify the base sample folder to use when syncing sample locations.')
    sync_parser.add_argument('file', nargs='+', help='Any files that contain sample references.')

    args = argparser.parse_args()

    # Set dry-run
    dry_run = args.dry_run

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
        samples = [Sample(sample_xml, library=args.library) for sample_xml in sample_refs(file_xml)]
        samples_by_file[file_path] = samples

    if args.action == 'check':
        for (file_path, samples) in samples_by_file.items():
            print('\nFile %s:' % (file_path))
            num_samples = len(samples)
            for (i, sample) in enumerate(samples):
                print('\nSample %d/%d, %s, %s' % (i + 1, num_samples, sample.name, sample.absolute_path))
                print('Exists: %s' % sample.exists)
    elif args.action == 'sync':
        for (file_path, samples) in samples_by_file.items():
            print('\nFile %s:' % (file_path))
            num_samples = len(samples)
            for (i, sample) in enumerate(samples):
                print('\nSample %d/%d, %s' % (i + 1, num_samples, sample.name))

                sync(file_path, sample, args.preset_base, args.sample_base)
