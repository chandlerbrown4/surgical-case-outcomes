from dataclasses import replace
import unittest

from surgical.fixture import make_fixture
from surgical.validation import validate_implants


class ImplantValidationTests(unittest.TestCase):
    def test_replayed_line_is_rejected_but_separate_lines_can_use_the_same_item(self):
        data = make_fixture()
        line = data.implants[0]
        data.implants.append(replace(line, line_id="another-delivery"))
        validate_implants(data)
        data.implants.append(line)
        with self.assertRaisesRegex(ValueError, "duplicate implant line"):
            validate_implants(data)

    def test_device_actually_implanted_must_agree_with_case_group(self):
        data = make_fixture()
        data.implants[0] = replace(data.implants[0], device_id="MESH-B")
        with self.assertRaisesRegex(ValueError, "mesh group disagrees"):
            validate_implants(data)
