"""Test utilities in the `lib` module."""
from scripts.lib import aphis


def test_filename_from_url():
    """Test the test_filename_from_url utility."""
    aphis.filename_from_url(
        "https://aphis--c.na21.content.force.com/sfc/dist/version/download/?oid=00Dt0000000GyZH&ids=068t000000Egev8&d=%2Fa%2Ft00000011oSv%2F7XcUxgKr2Q5BbDkcGCEiUIydnBY67t_f07yuEKeG7rU&asPdf=false"  # noqa: E501
    )
