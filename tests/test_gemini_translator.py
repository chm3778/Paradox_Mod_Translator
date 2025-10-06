import unittest
from unittest.mock import MagicMock, patch
from core.gemini_translator import GeminiTranslator

class TestGeminiTranslator(unittest.TestCase):
    """Tests for the GeminiTranslator class."""

    def setUp(self):
        """Set up a mock application reference for each test."""
        self.mock_app_ref = MagicMock()
        self.mock_app_ref.log_message = MagicMock()

    def test_translate_returns_error_on_missing_format_markers(self):
        """
        Tests that the translate method returns a specific error when the API
        response is missing the expected '$$' delimiters.
        """
        # Arrange
        translator = GeminiTranslator(app_ref=self.mock_app_ref, translator_id="test_translator")
        original_text = "An untranslated string."
        # Simulate an API response that is valid text but lacks the required '$$' markers.
        malformed_api_response = "Une chaîne non traduite."

        # Act
        # We patch _call_actual_api to simulate a response from the Gemini API.
        with patch.object(translator, '_call_actual_api', return_value=(malformed_api_response, 20)):
            translated_text, token_count, error = translator.translate(
                text_to_translate=original_text,
                source_lang_name="english",
                target_lang_name="french",
                game_mod_style="general",
                model_name="gemini-pro",
                api_key_to_use="DUMMY_KEY"
            )

        # Assert
        # The bug is that this check fails. The method should return an error.
        # Instead, it currently returns the original text with a `None` error.
        self.assertEqual(error, "TRANSLATION_FORMAT_ERROR", "The error should indicate a formatting issue.")
        self.assertEqual(translated_text, original_text, "The original text should be returned on format failure.")
        self.assertEqual(token_count, 0, "Token count should be 0 on format failure.")

if __name__ == '__main__':
    unittest.main()