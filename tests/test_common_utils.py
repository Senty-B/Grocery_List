import unittest

from app.common.utils import generate_invite_code


class CommonUtilsTestCase(unittest.TestCase):
    def test_generate_invite_code_returns_expected_length(self):
        code = generate_invite_code()

        self.assertEqual(len(code), 8)
        self.assertTrue(code.isalnum())
        self.assertEqual(code.upper(), code)

    def test_generate_invite_code_respects_custom_length(self):
        code = generate_invite_code(length=12)

        self.assertEqual(len(code), 12)
