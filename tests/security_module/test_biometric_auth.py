import unittest
import sys
import os

# Add the parent directory of 'security_module' to sys.path
# This allows the test runner to find the 'security_module'
# This is a common pattern for tests located in a subdirectory.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from security_module.biometric_auth import BiometricAuthenticator

class TestBiometricAuthenticator(unittest.TestCase):
    """
    Test cases for the BiometricAuthenticator class.
    """

    def setUp(self):
        """
        Set up for test methods. This method is called before each test.
        """
        self.authenticator = BiometricAuthenticator()

    def test_authenticate_voice_simulated_success(self):
        """
        Test voice authentication simulation (currently hardcoded to True).
        """
        print("Running test_authenticate_voice_simulated_success...")
        # The current implementation of authenticate_voice returns True
        self.assertTrue(self.authenticator.authenticate_voice(), "Voice authentication should succeed (simulated).")
        print("Finished test_authenticate_voice_simulated_success.")

    def test_authenticate_face_simulated_failure(self):
        """
        Test face authentication simulation (currently hardcoded to False).
        """
        print("Running test_authenticate_face_simulated_failure...")
        # The current implementation of authenticate_face returns False
        self.assertFalse(self.authenticator.authenticate_face(), "Face authentication should fail (simulated).")
        print("Finished test_authenticate_face_simulated_failure.")

    def test_authenticate_fingerprint_simulated_success(self):
        """
        Test fingerprint authentication simulation (currently hardcoded to True).
        """
        print("Running test_authenticate_fingerprint_simulated_success...")
        # The current implementation of authenticate_fingerprint returns True
        self.assertTrue(self.authenticator.authenticate_fingerprint(), "Fingerprint authentication should succeed (simulated).")
        print("Finished test_authenticate_fingerprint_simulated_success.")

    # Example of how you might adapt tests later if methods change:
    # def test_authenticate_voice_with_mocking(self):
    #     """
    #     Example of a test if the method's behavior was more complex and needed mocking.
    #     This is not directly testing the current simple implementation but serves as a guide.
    #     """
    #     # To make this test runnable, you'd need to modify BiometricAuthenticator
    #     # or use unittest.mock.patch if it were calling external services.
    #     # For now, this is commented out as it doesn't apply to the simple simulation.
    #
    #     # from unittest.mock import patch
    #     # with patch.object(self.authenticator, '_internal_voice_check_method', return_value=True) as mock_method:
    #     #     self.assertTrue(self.authenticator.authenticate_voice())
    #     #     mock_method.assert_called_once()
    #     pass

if __name__ == '__main__':
    # This allows running the tests directly from this file
    print(f"Current sys.path for test execution: {sys.path}")
    unittest.main()
