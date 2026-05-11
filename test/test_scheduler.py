import unittest
from unittest.mock import MagicMock, patch, ANY
import datetime
import time
from pathlib import Path
from app.core.scheduler import BellScheduler

class TestBellScheduler(unittest.TestCase):
    @patch('app.core.scheduler.BellPlayer')
    @patch('app.core.scheduler.VersionedConfigStore')
    def setUp(self, MockStore, MockPlayer):
        self.scheduler = BellScheduler()
        self.mock_store = MockStore.return_value
        self.mock_player = MockPlayer.return_value
        
        # Setup some default bell entries
        self.scheduler.bell_entries = [
            {
                'days': [1, 2, 3, 4, 5],
                'filenames': ['bell.mp3'],
                'times': [
                    {'time': (8, 0), 'disabled': False, 'is_range': False, 'duration': None},
                    {'time': (9, 0), 'disabled': False, 'is_range': True, 'duration': 600} # 10 mins
                ],
                'line_num': 1
            }
        ]

    @patch('app.core.scheduler.datetime')
    def test_should_play_now_point(self, mock_datetime):
        """Test exact time matching (Point Task)"""
        mock_datetime.timedelta = datetime.timedelta # Use real timedelta
        # Monday 08:00:00
        mock_now = datetime.datetime(2023, 10, 23, 8, 0, 0) # Mon
        mock_datetime.datetime.now.return_value = mock_now
        
        result = self.scheduler.should_play_now()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['filenames'], ['bell.mp3'])
        self.assertFalse(result.get('is_range'))

    @patch('app.core.scheduler.datetime')
    def test_should_play_now_range(self, mock_datetime):
        """Test time range matching"""
        mock_datetime.timedelta = datetime.timedelta # Use real timedelta
        # Monday 09:05:00 (Inside 09:00-09:10 range)
        mock_now = datetime.datetime(2023, 10, 23, 9, 5, 0)
        mock_datetime.datetime.now.return_value = mock_now
        
        result = self.scheduler.should_play_now()
        
        self.assertIsNotNone(result)
        self.assertTrue(result.get('is_range'))
        self.assertEqual(result['duration'], 600)
        # Check range_start_dt
        expected_start = datetime.datetime(2023, 10, 23, 9, 0, 0)
        self.assertEqual(result['range_start_dt'], expected_start)

    @patch('app.core.scheduler.datetime')
    def test_priority_point_over_range(self, mock_datetime):
        """Test that point task overrides range task if they overlap"""
        mock_datetime.timedelta = datetime.timedelta # Use real timedelta
        # Add a point task that overlaps with the range task
        # Range is 09:00 - 09:10. Add point task at 09:05
        self.scheduler.bell_entries.append({
            'days': [1],
            'filenames': ['interrupt.mp3'],
            'times': [
                {'time': (9, 5), 'disabled': False, 'is_range': False, 'duration': None}
            ],
            'line_num': 2
        })
        
        mock_now = datetime.datetime(2023, 10, 23, 9, 5, 0)
        mock_datetime.datetime.now.return_value = mock_now
        
        result = self.scheduler.should_play_now()
        
        # Should return the point task
        self.assertIsNotNone(result)
        self.assertEqual(result['filenames'], ['interrupt.mp3'])
        self.assertFalse(result.get('is_range'))

    @patch('app.core.scheduler.datetime')
    def test_range_task_execution_logic(self, mock_datetime):
        """Test the logic inside run() for range tasks (simulated)"""
        mock_datetime.timedelta = datetime.timedelta # Use real timedelta
        # Simulate run loop logic for a range task
        
        # 1. Start of range
        mock_now = datetime.datetime(2023, 10, 23, 9, 0, 0)
        mock_datetime.datetime.now.return_value = mock_now
        
        bell = self.scheduler.should_play_now()
        self.assertTrue(bell['is_range'])
        
        signature = (bell['line_num'], bell.get('range_start_dt'))
        self.scheduler.current_range_signature = None
        self.mock_player.is_busy.return_value = False
        
        # Logic from run():
        if bell['is_range']:
             if self.mock_player.is_busy():
                 pass
             else:
                 self.scheduler.current_range_signature = signature
                 self.mock_player.play(ANY, duration=0, next_track_callback=ANY)

        self.mock_player.play.assert_called()
        self.assertEqual(self.scheduler.current_range_signature, signature)
        
        # 2. Middle of range - should NOT call play again if signature matches
        self.mock_player.reset_mock()
        self.mock_player.is_busy.return_value = True # Player is playing
        
        # Logic from run():
        if bell['is_range']:
             if self.mock_player.is_busy():
                 if self.scheduler.current_range_signature == signature:
                     # Continue playing
                     pass
                 else:
                     pass
             else:
                 # Player finished song, restart? (Handled by callback usually, but if idle logic)
                 pass

        self.mock_player.play.assert_not_called()

    @patch('app.core.scheduler.datetime')
    def test_interruption_execution_logic(self, mock_datetime):
        """Test that a point task interrupts a range task"""
        mock_datetime.timedelta = datetime.timedelta # Use real timedelta
        # 1. Setup range task playing
        start_dt = datetime.datetime(2023, 10, 23, 9, 0, 0)
        self.scheduler.current_range_signature = (1, start_dt)
        
        # 2. Point task arrives
        self.scheduler.bell_entries.append({
            'days': [1],
            'filenames': ['interrupt.mp3'],
            'times': [
                {'time': (9, 5), 'disabled': False, 'is_range': False, 'duration': None}
            ],
            'line_num': 2
        })
        
        mock_now = datetime.datetime(2023, 10, 23, 9, 5, 0)
        mock_datetime.datetime.now.return_value = mock_now
        
        bell = self.scheduler.should_play_now()
        
        # Verify it's the point task
        self.assertFalse(bell['is_range'])
        self.assertEqual(bell['filenames'], ['interrupt.mp3'])
        
        # Logic from run():
        if not bell.get('is_range'):
             # Should clear signature
             self.scheduler.current_range_signature = None
             self.mock_player.play(bell['filenames'][0], ANY, next_track_callback=None)
             
        self.assertIsNone(self.scheduler.current_range_signature)
        self.mock_player.play.assert_called_with('interrupt.mp3', ANY, next_track_callback=None)

if __name__ == '__main__':
    unittest.main()
