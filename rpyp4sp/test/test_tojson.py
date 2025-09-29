import pytest
import os
import glob
from rpyp4sp import objects, rpyjson


class TestTojsonIntegration(object):
    """Integration tests for tojson methods using real P4 test data."""

    @pytest.mark.parametrize(
        "json_file",
         glob.glob("p4-spectec/p4c/testdata/p4_16_samples/*.json")[:50]
    )
    def test_tojson_roundtrip(self, json_file):
        """Test that tojson -> loads creates equivalent values."""
        # Read the original JSON file
        with open(json_file, 'r') as f:
            json_content = f.read()

        # Skip files that aren't valid JSON (error messages, etc.)
        if not json_content.strip().startswith('{'):
            pytest.skip("File does not contain valid JSON: %s" % os.path.basename(json_file))

        # Parse to get BaseV object
        try:
            json_parsed = rpyjson.loads(json_content)
            value1 = objects.BaseV.fromjson(json_parsed)
        except (ValueError, KeyError) as e:
            pytest.skip("Could not parse JSON file %s: %s" % (os.path.basename(json_file), str(e)))

        # Convert back to JSON using tojson
        json_result = value1.tojson()
        json_serialized = rpyjson.dumps(json_result)

        # Parse the serialized JSON back to BaseV
        json_reparsed = rpyjson.loads(json_serialized)
        value2 = objects.BaseV.fromjson(json_reparsed)

        # Check equality
        assert value1.eq(value2), "Values not equal after roundtrip for %s" % os.path.basename(json_file)
