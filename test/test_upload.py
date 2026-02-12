import unittest
import os
import shutil
from pathlib import Path
from flask import Flask
from werkzeug.datastructures import FileStorage
from io import BytesIO

# Add project root to path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.web import app, MEDIA_DIR

class UploadTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        # Create a temporary media directory for testing
        self.test_media_dir = MEDIA_DIR / 'test_uploads'
        self.original_media_dir = MEDIA_DIR
        
        # Monkey patch MEDIA_DIR in app.web (this is tricky because it's a global variable)
        # Instead, we can just use the existing MEDIA_DIR but ensure we clean up
        # For safety, let's just use the real MEDIA_DIR but use specific test filenames
        
        self.test_files = ['test_upload_1.mp3', 'test_upload_2.wav']
        
        # Create dummy content
        for f in self.test_files:
            with open(f, 'wb') as file:
                file.write(b'dummy content')

    def tearDown(self):
        # Clean up uploaded files
        for f in self.test_files:
            path = MEDIA_DIR / f
            if path.exists():
                os.remove(path)
            
            # Clean up local dummy files
            if os.path.exists(f):
                os.remove(f)

    def test_multiple_upload(self):
        data = {}
        # Simulate multiple files
        files = []
        for f in self.test_files:
            with open(f, 'rb') as file:
                content = file.read()
                files.append((BytesIO(content), f))
        
        # Flask test client handles list of files for the same key 'file'
        data = {
            'file': files
        }
        
        response = self.client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        
        # Check if files exist in MEDIA_DIR
        for f in self.test_files:
            self.assertTrue((MEDIA_DIR / f).exists(), f"File {f} should exist in {MEDIA_DIR}")
            
        # Check response for success message
        self.assertIn(b'\xe6\x88\x90\xe5\x8a\x9f\xe4\xb8\x8a\xe4\xbc\xa0 2 \xe4\xb8\xaa\xe6\x96\x87\xe4\xbb\xb6', response.data) # "成功上传 2 个文件" in utf-8

if __name__ == '__main__':
    unittest.main()
