"""Tests for version resolution."""

from importlib.metadata import PackageNotFoundError
from types import SimpleNamespace
from unittest.mock import patch

from monokl.version import _format_describe_output
from monokl.version import _version_from_git
from monokl.version import get_version


class TestFormatDescribeOutput:
    """Tests for parsing `git describe` output."""

    def test_parses_exact_tag(self) -> None:
        assert _format_describe_output("v1.2.3-0-gabc1234") == "1.2.3"

    def test_parses_commits_after_tag(self) -> None:
        assert _format_describe_output("v1.2.3-5-gabc1234") == "1.2.3+5.gabc1234"

    def test_parses_dirty_tree(self) -> None:
        assert _format_describe_output("v1.2.3-5-gabc1234-dirty") == "1.2.3+5.gabc1234.dirty"

    def test_parses_hash_only(self) -> None:
        assert _format_describe_output("abc1234") == "0.0.0+gabc1234"

    def test_returns_none_for_unexpected_format(self) -> None:
        assert _format_describe_output("not-a-version") is None


class TestVersionFromGit:
    """Tests for git-based version resolution."""

    @patch("monokl.version.subprocess.run")
    def test_returns_none_when_git_fails(self, mock_run) -> None:  # type: ignore[no-untyped-def]
        mock_run.return_value = SimpleNamespace(returncode=1, stdout="")
        assert _version_from_git() is None

    @patch("monokl.version.subprocess.run")
    def test_returns_parsed_version(self, mock_run) -> None:  # type: ignore[no-untyped-def]
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="v2.0.0-2-gdeadbee\n")
        assert _version_from_git() == "2.0.0+2.gdeadbee"


class TestGetVersion:
    """Tests for full version fallback chain."""

    def test_uses_git_when_available(self) -> None:
        get_version.cache_clear()
        with (
            patch("monokl.version._version_from_git", return_value="1.0.0+1.gabc1234"),
            patch("monokl.version.package_version"),
        ):
            assert get_version() == "1.0.0+1.gabc1234"

    def test_falls_back_to_package_metadata(self) -> None:
        get_version.cache_clear()
        with (
            patch("monokl.version._version_from_git", return_value=None),
            patch("monokl.version.package_version", return_value="3.4.5"),
        ):
            assert get_version() == "3.4.5"

    def test_falls_back_to_unknown_when_no_metadata(self) -> None:
        get_version.cache_clear()
        with (
            patch("monokl.version._version_from_git", return_value=None),
            patch("monokl.version.package_version", side_effect=PackageNotFoundError()),
        ):
            assert get_version() == "0.0.0+unknown"
