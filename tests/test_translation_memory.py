import unittest
import tempfile
import os
from utils.translation_memory import TranslationMemory


class TestTranslationMemory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tm_path = os.path.join(self.temp_dir.name, 'tm.json')

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_add_and_retrieve(self):
        tm = TranslationMemory(self.tm_path)
        tm.add('Hello', '你好', 'english', 'simp_chinese')
        tm.save()

        tm2 = TranslationMemory(self.tm_path)
        result = tm2.get('Hello', 'english', 'simp_chinese')
        self.assertEqual(result, '你好')


if __name__ == '__main__':
    unittest.main()
