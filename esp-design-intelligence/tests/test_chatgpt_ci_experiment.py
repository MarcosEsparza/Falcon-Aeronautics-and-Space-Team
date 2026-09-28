"""Temporary test for verifying that CI catches a deliberate failure.

Never merge this experimental test file.
"""

def test_ci_detects_intentional_failure():
    assert False, "EXPECTED CI FAILURE: ChatGPT workflow experiment"
