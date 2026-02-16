import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import os
from app.core.parser import BellParser

class TestBellParser(unittest.TestCase):
    def setUp(self):
        self.media_dir = Path("/fake/media")
        self.config_file = Path("/fake/bells.conf")
        self.parser = BellParser(self.config_file, self.media_dir)

    def test_parse_comments(self):
        """Test parsing with various comment styles"""
        content = """
        // Line comment at start
        (1,2,3,4,5) school_bell.mp3, 08:00 // End of line comment
        /* Block comment start */ (1,2) test_block.mp3, 09:00
        (3) test_inline.mp3, /* Inline comment */ 10:00
        /* Multi
           line
           comment */
        (4) test_multiline.mp3, 11:00
        """
        
        with patch("builtins.open", unittest.mock.mock_open(read_data=content)):
            with patch.object(Path, "exists", return_value=True):
                 # Mock _resolve_filenames to just return the filename to avoid fs checks
                with patch.object(self.parser, "_resolve_filenames", side_effect=lambda x, y: [x]):
                    entries = self.parser.parse()

        self.assertEqual(len(entries), 4)
        
        # Check 08:00 entry
        self.assertEqual(entries[0]['times'][0]['time'], (8, 0))
        self.assertEqual(entries[0]['filenames'], ['school_bell.mp3'])
        
        # Check 09:00 entry
        self.assertEqual(entries[1]['times'][0]['time'], (9, 0))
        self.assertEqual(entries[1]['filenames'], ['test_block.mp3'])
        
        # Check 10:00 entry
        self.assertEqual(entries[2]['times'][0]['time'], (10, 0))
        self.assertEqual(entries[2]['filenames'], ['test_inline.mp3'])
        
        # Check 11:00 entry
        self.assertEqual(entries[3]['times'][0]['time'], (11, 0))
        self.assertEqual(entries[3]['filenames'], ['test_multiline.mp3'])

    def test_parse_time_ranges(self):
        """Test parsing time ranges (HH:MM-HH:MM)"""
        content = "(1) background.mp3, 08:00-08:10"
        
        with patch("builtins.open", unittest.mock.mock_open(read_data=content)):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(self.parser, "_resolve_filenames", side_effect=lambda x, y: [x]):
                    entries = self.parser.parse()
        
        self.assertEqual(len(entries), 1)
        time_entry = entries[0]['times'][0]
        
        self.assertTrue(time_entry['is_range'])
        self.assertEqual(time_entry['time'], (8, 0)) # Start time
        self.assertEqual(time_entry['duration'], 10 * 60) # 10 minutes in seconds

    def test_parse_mixed_times(self):
        """Test parsing mixed single times and ranges"""
        content = "(1) mix.mp3, 08:00, 09:00-09:30, 10:00"
        
        with patch("builtins.open", unittest.mock.mock_open(read_data=content)):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(self.parser, "_resolve_filenames", side_effect=lambda x, y: [x]):
                    entries = self.parser.parse()
        
        self.assertEqual(len(entries), 1)
        times = entries[0]['times']
        self.assertEqual(len(times), 3)
        
        # 08:00
        self.assertFalse(times[0]['is_range'])
        self.assertEqual(times[0]['time'], (8, 0))
        
        # 09:00-09:30
        self.assertTrue(times[1]['is_range'])
        self.assertEqual(times[1]['time'], (9, 0))
        self.assertEqual(times[1]['duration'], 30 * 60)
        
        # 10:00
        self.assertFalse(times[2]['is_range'])
        self.assertEqual(times[2]['time'], (10, 0))

    def test_resolve_filenames_glob(self):
        """Test filename resolution with glob"""
        # Mock glob and exists
        with patch("app.core.parser.glob.glob") as mock_glob:
            with patch.object(Path, "exists", return_value=True):
                mock_glob.return_value = ["/fake/media/song1.mp3", "/fake/media/song2.mp3"]
                
                filenames = self.parser._resolve_filenames("*.mp3", 1)
                
                # Should return basenames
                self.assertIn("song1.mp3", filenames)
                self.assertIn("song2.mp3", filenames)
                self.assertEqual(len(filenames), 2)

    def test_parse_cross_day_range(self):
        """Test parsing time range that crosses midnight"""
        content = "(1) sleep.mp3, 23:50-00:10"
        
        with patch("builtins.open", unittest.mock.mock_open(read_data=content)):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(self.parser, "_resolve_filenames", side_effect=lambda x, y: [x]):
                    entries = self.parser.parse()
        
        self.assertEqual(len(entries), 1)
        time_entry = entries[0]['times'][0]
        
        self.assertTrue(time_entry['is_range'])
        self.assertEqual(time_entry['time'], (23, 50))
        # 10 mins (until 00:00) + 10 mins (until 00:10) = 20 mins
        self.assertEqual(time_entry['duration'], 20 * 60)

if __name__ == '__main__':
    unittest.main()
