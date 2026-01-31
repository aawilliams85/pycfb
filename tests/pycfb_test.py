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
            sizes: list[int] = []
            data: list[bytes] = []
            search_pattern = os.path.join(path1, '**', '*.*')
            for path2 in glob.glob(search_pattern, recursive=True):
                print(path2)
                names.append(path2)
                sizes.append(os.path.getsize(path2))
                with open(path2, 'rb') as f: data.append(f.read())

            x = CFBWriter(stream_names=names, stream_data=data, root_clsid=uuid.UUID('BE87C5E3-E3CB-4BAB-8427-578ECCE263F7'))



    def tearDown(self):
        pass