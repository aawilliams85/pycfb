import glob
import os
import pprint
import unittest
import uuid

from pycfb import CFBWriter

# Shared paths
LOCAL_BASE_PATH = os.path.abspath(os.path.dirname(__file__))
LOCAL_INPUT_PATH = os.path.join(LOCAL_BASE_PATH, 'input_files')
LOCAL_OUTPUT_PATH = os.path.join(LOCAL_BASE_PATH, 'output_files')

class pycfb_tests(unittest.TestCase):
    def setUp(self):
        pass

    def test_write_cfb(self):
        print('')
        for path1 in glob.glob(os.path.join(LOCAL_INPUT_PATH, '*')):
            print(path1)
            
            names: list[str] = []
            paths: list[str] = []
            sizes: list[int] = []
            data: list[bytes] = []
            search_pattern = os.path.join(path1, '**', '*.*')
            for path2 in glob.glob(search_pattern, recursive=True):
                relative_path = os.path.relpath(path2, path1)
                if relative_path == None: return

                #print(f'Name: {os.path.basename(path2)}, Path: {relative_path}, Size: {os.path.getsize(path2)}')
                names.append(os.path.basename(path2))
                paths.append(relative_path)
                sizes.append(os.path.getsize(path2))
                with open(path2, 'rb') as f: data.append(f.read())

            x = CFBWriter(stream_names=names, stream_paths=paths, stream_data=data, root_clsid=uuid.UUID('BE87C5E3-E3CB-4BAB-8427-578ECCE263F7'))
            with open(os.path.join(LOCAL_OUTPUT_PATH, 'test.ole'), 'wb') as f: f.write(x._data)

    def tearDown(self):
        pass