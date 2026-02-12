import unittest
import os
import shutil
import glob
from pathlib import Path

# Mock main.py's loading logic
class ConfigLoader:
    def __init__(self, config_file, media_dir):
        self.config_file = config_file
        self.media_dir = media_dir
        
    def load_files(self, file_field):
        raw_filenames = []
        if file_field.startswith('[') and file_field.endswith(']'):
            inner = file_field[1:-1]
            raw_filenames = [fn.strip() for fn in inner.split(',') if fn.strip()]
        else:
            raw_filenames = [file_field]
            
        filenames = []
        for fn in raw_filenames:
            if '*' in fn or '?' in fn:
                pattern = str(self.media_dir / fn)
                matched_paths = glob.glob(pattern)
                if matched_paths:
                    for p in matched_paths:
                        filenames.append(os.path.basename(p))
                else:
                    filenames.append(fn) # Keep original if no match
            else:
                filenames.append(fn)
        
        return list(set(filenames))

class TestGlobSupport(unittest.TestCase):
    def setUp(self):
        # Setup test environment
        self.test_dir = Path('test_env')
        self.test_dir.mkdir(exist_ok=True)
        self.media_dir = self.test_dir / 'music'
        self.media_dir.mkdir(exist_ok=True)
        
        # Create dummy music files
        (self.media_dir / 'jazz_1.mp3').touch()
        (self.media_dir / 'jazz_2.mp3').touch()
        (self.media_dir / 'pop_1.mp3').touch()
        (self.media_dir / 'other.wav').touch()
        
        self.loader = ConfigLoader('dummy.conf', self.media_dir)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_single_wildcard(self):
        # Test [jazz_*.mp3]
        files = self.loader.load_files('[jazz_*.mp3]')
        self.assertEqual(len(files), 2)
        self.assertIn('jazz_1.mp3', files)
        self.assertIn('jazz_2.mp3', files)

    def test_mixed_wildcard(self):
        # Test [pop_*.mp3, jazz_1.mp3]
        files = self.loader.load_files('[pop_*.mp3, jazz_1.mp3]')
        self.assertEqual(len(files), 2)
        self.assertIn('pop_1.mp3', files)
        self.assertIn('jazz_1.mp3', files)

    def test_no_match(self):
        # Test [rock_*.mp3] -> should keep original string
        files = self.loader.load_files('[rock_*.mp3]')
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], 'rock_*.mp3')

    def test_all_mp3(self):
        # Test [*.mp3]
        files = self.loader.load_files('[*.mp3]')
        self.assertEqual(len(files), 3) # jazz_1, jazz_2, pop_1

if __name__ == '__main__':
    unittest.main()
