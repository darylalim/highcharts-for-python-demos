"""Tests for the release automation script in ``.github/scripts/release.py``.

Run with: ``uv run pytest``

``release.py`` is dev/CI tooling — the ``release`` job in ``.github/workflows/
ci.yml`` calls it to cut a tag + GitHub release for every version above the
latest released one (so a merged bump, even one of two in a single push, can't sit
un-released). Its pure functions carry every decision worth regression-testing:
reading the current version, listing the changelog's versions, slicing a section
out **verbatim** (so the notes can't drift from the changelog), and deciding which
versions still need releasing given the latest-release watermark. They're
exercised directly here — no subprocess, no git, no network — like the
``.claude/hooks/`` decision functions in ``test_hooks.py``, and ``main()``'s CLI
contract is pinned too (the workflow parses its stdout, so a stray print would
silently corrupt a tag name).

The script lives outside any importable package, so it's loaded by file path via
``importlib`` (importing only defines functions; ``main()`` is behind an
``if __name__ == "__main__"`` guard, so there are no import side effects).
"""

from pathlib import Path

import pytest
from conftest import load_script

ROOT = Path(__file__).resolve().parent.parent

release = load_script(ROOT / ".github" / "scripts" / "release.py", "_release")

# A miniature CHANGELOG in the repo's real shape: a prose preamble (which must not
# be mistaken for a section), then reverse-chronological ``## [x.y.z]`` entries,
# some with an ``### Added``/``### Notes`` split, the oldest running to EOF.
SAMPLE = """# Changelog

Preamble prose. `0.7.0` was the first release; nothing here is a ## heading.

## [0.11.0] - 2026-07-16

### Added

- funnel and pyramid.

## [0.10.0] - 2026-07-15

### Added

- columnrange.

### Notes

- a measured note.

## [0.9.0] - 2026-07-15

- older stuff.
"""


# --------------------------------------------------------------------------- #
# read_version / changelog_versions
# --------------------------------------------------------------------------- #
def test_read_version_pulls_project_version():
    assert release.read_version('[project]\nversion = "1.2.3"\n') == "1.2.3"


def test_changelog_versions_lists_every_heading_newest_first():
    assert release.changelog_versions(SAMPLE) == ["0.11.0", "0.10.0", "0.9.0"]


def test_changelog_versions_ignores_prose_and_non_semver_headings():
    text = "## [Unreleased]\n\n## [1.0.0] - x\n\n## not a version\n"
    assert release.changelog_versions(text) == ["1.0.0"]


# --------------------------------------------------------------------------- #
# extract_release_notes
# --------------------------------------------------------------------------- #
def test_extract_release_notes_is_bounded_by_its_two_headings():
    # Exact match pins the whole body verbatim (sub-headings included) and, being
    # exact, proves no bleed from the newer section above or the older one below.
    assert release.extract_release_notes(SAMPLE, "0.10.0") == (
        "### Added\n\n- columnrange.\n\n### Notes\n\n- a measured note."
    )


def test_extract_release_notes_last_section_runs_to_eof():
    # The oldest section has no following ``## [`` heading to stop at.
    assert release.extract_release_notes(SAMPLE, "0.9.0") == "- older stuff."


def test_extract_release_notes_strips_surrounding_blank_lines():
    # The heading is followed by a blank line and the section by another; neither
    # should survive into the emitted notes.
    notes = release.extract_release_notes(SAMPLE, "0.11.0")
    assert notes == "### Added\n\n- funnel and pyramid."


def test_extract_release_notes_missing_version_raises():
    with pytest.raises(ValueError, match="9.9.9"):
        release.extract_release_notes(SAMPLE, "9.9.9")


def test_extract_release_notes_empty_section_raises():
    # A version whose section body is only whitespace must fail loudly, never cut a
    # blank release.
    changelog = "## [1.0.0] - x\n\n## [0.9.0] - y\n\nbody\n"
    with pytest.raises(ValueError, match="empty"):
        release.extract_release_notes(changelog, "1.0.0")


def test_extract_release_notes_heading_without_trailing_newline_reads_as_empty():
    # A heading that is the file's final line with no trailing newline (a truncated
    # or hand-edited changelog) must be diagnosed as *empty*, not *absent* — the
    # heading match ends at end-of-line, not at a required ``\n``.
    with pytest.raises(ValueError, match="empty"):
        release.extract_release_notes("## [1.0.0] - 2026-07-16", "1.0.0")


# --------------------------------------------------------------------------- #
# versions_to_release — the watermark that fixes the two-bumps-in-one-push gap
# --------------------------------------------------------------------------- #
def test_to_release_is_empty_when_the_top_version_is_already_released():
    # Normal push with no bump: the newest version already has a release.
    assert release.versions_to_release(SAMPLE, "v0.11.0") == []


def test_to_release_returns_the_single_new_version_after_one_bump():
    # Latest release is 0.10.0; only 0.11.0 is above it.
    assert release.versions_to_release(SAMPLE, "v0.10.0") == ["0.11.0"]


def test_to_release_returns_both_after_two_bumps_in_one_push_oldest_first():
    # The headline fix: 0.10.0 and 0.11.0 both land above the 0.9.0 watermark, and
    # come back oldest-first so the caller marks only 0.11.0 --latest.
    assert release.versions_to_release(SAMPLE, "v0.9.0") == ["0.10.0", "0.11.0"]


def test_to_release_accepts_a_bare_version_without_the_v_prefix():
    assert release.versions_to_release(SAMPLE, "0.10.0") == ["0.11.0"]


def test_to_release_with_no_watermark_does_only_the_current_version():
    # No releases yet: be conservative, never back-fill the whole history — this
    # repo's 0.1.0–0.6.0 carry tags but no releases. This is the *only* state that
    # reaches here as an empty watermark; the workflow now fails on a gh error
    # rather than passing "" for it, so the two can no longer be confused.
    assert release.versions_to_release(SAMPLE, "") == ["0.11.0"]
    assert release.versions_to_release(SAMPLE, None) == ["0.11.0"]


def test_to_release_raises_on_a_watermark_that_is_not_a_changelog_version():
    # The fail-open bug: this branch used to return EVERY version in the file, which
    # in the real repo means resurrecting the deliberately release-less 0.1.0–0.6.0.
    # Reachable from a hand-cut release whose tag has no `## [x.y.z]` section.
    with pytest.raises(ValueError, match="not a CHANGELOG"):
        release.versions_to_release(SAMPLE, "v9.9.9")
    # The failure must name the tag as the caller passed it, `v` prefix and all.
    with pytest.raises(ValueError, match="v0.18.1"):
        release.versions_to_release(SAMPLE, "v0.18.1")


# --------------------------------------------------------------------------- #
# main() — the CLI contract the workflow parses (stdout must be clean)
# --------------------------------------------------------------------------- #
def test_main_version_prints_only_the_version(capsys):
    # The workflow does `current="$(release.py version)"`; stdout must be exactly
    # the version and nothing else, or `tag="v${current}"` is corrupted.
    assert release.main(["version"]) == 0
    out = capsys.readouterr()
    assert out.out == release.read_version((ROOT / "pyproject.toml").read_text()) + "\n"
    assert out.err == ""


def test_main_notes_prints_the_named_versions_section(capsys):
    # `notes VERSION` reads the real changelog; assert it round-trips the section.
    version = release.read_version((ROOT / "pyproject.toml").read_text())
    assert release.main(["notes", version]) == 0
    printed = capsys.readouterr().out
    expected = release.extract_release_notes(
        (ROOT / "CHANGELOG.md").read_text(), version
    )
    assert printed == expected + "\n"


def test_main_to_release_prints_one_version_per_line(capsys, monkeypatch, tmp_path):
    # Drive `to-release` against a controlled changelog so the output is pinned
    # without depending on the repo's real release state.
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(SAMPLE)
    monkeypatch.setattr(release, "ROOT", tmp_path)
    assert release.main(["to-release", "v0.9.0"]) == 0
    assert capsys.readouterr().out == "0.10.0\n0.11.0\n"


@pytest.mark.parametrize("argv", [[], ["bogus"], ["version", "extra"], ["to-release"]])
def test_main_bad_args_return_2_and_write_nothing_to_stdout(capsys, argv):
    # The workflow relies on exit codes; a misuse must fail (2), and must not print
    # anything to stdout that a caller could mistake for real output.
    assert release.main(argv) == 2
    out = capsys.readouterr()
    assert out.out == ""
    assert "usage" in out.err


# --------------------------------------------------------------------------- #
# No-drift, against the real files
# --------------------------------------------------------------------------- #
def test_current_version_has_nonempty_release_notes():
    """The version the workflow reads has a non-empty CHANGELOG section, so a push
    that bumps it can actually be released.

    (``test_changelog_documents_the_current_version`` pins that the section is for
    the *right* version; this pins that the extractor the workflow runs can read
    it.)"""
    version = release.read_version((ROOT / "pyproject.toml").read_text())
    notes = release.extract_release_notes((ROOT / "CHANGELOG.md").read_text(), version)
    assert notes
