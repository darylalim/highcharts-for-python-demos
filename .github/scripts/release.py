#!/usr/bin/env python3
"""Release automation for highcharts-studio.

Stdlib-only, importable, and runnable as a CLI. The ``release`` job in
``.github/workflows/ci.yml`` calls it to cut a tag + GitHub release for every
version that has reached ``main`` above the latest released one — so a merged
version bump can never sit un-released again, even when *two* bumps land in one
push. (The drift this closes: the code reached ``0.11.0`` on ``main`` while the
newest GitHub release was still ``0.9.0``, because tagging + releasing was a
manual step that lagged the merge; and both ``0.10.0`` and ``0.11.0`` were merged
before either was released, which is exactly the multi-bump case a
release-only-the-current-version job would skip.)

The facts a release needs — the current version, the changelog notes, and which
versions still need releasing — are all *read* from ``pyproject.toml`` and
``CHANGELOG.md`` (the notes are the ``CHANGELOG.md`` section verbatim and cannot
drift from it; the changelog↔version pinning is
``tests/test_packaging.py::test_changelog_documents_the_current_version``, which
now reuses ``changelog_versions`` here rather than re-encoding the heading regex).
The pure, importable functions carry every decision so ``tests/test_release.py``
can cover them with no subprocess and no network — the ``.claude/hooks/`` pattern
applied to release tooling. ``main()`` is the thin file-IO/stdout wrapper the
workflow calls; the impure parts a release also needs (the latest-release tag via
``gh``, the bump commit via ``git``) stay in the workflow, which passes the
``gh``-derived latest tag into ``to-release``.
"""

import re
import sys
import tomllib
from pathlib import Path

# release.py lives at <root>/.github/scripts/release.py, so root is two up.
ROOT = Path(__file__).resolve().parents[2]

# A released ``## [x.y.z]`` heading — the one parser for the changelog's heading
# shape, shared by changelog_versions() and (via import) the packaging test.
_HEADING = r"^## \[(\d+\.\d+\.\d+)\]"


def read_version(pyproject_text: str) -> str:
    """The ``[project].version`` string from ``pyproject.toml`` text."""
    return tomllib.loads(pyproject_text)["project"]["version"]


def changelog_versions(changelog_text: str) -> list[str]:
    """Every ``## [x.y.z]`` version in ``CHANGELOG.md``, in document order.

    Keep a Changelog is reverse-chronological, so the list is newest-first and its
    first element is the current version. This is the *single* encoding of the
    heading format; ``test_changelog_documents_the_current_version`` reuses it
    instead of re-writing the regex, so the two can't drift.
    """
    return re.findall(_HEADING, changelog_text, re.M)


def extract_release_notes(changelog_text: str, version: str) -> str:
    """The body of ``CHANGELOG.md``'s ``## [<version>]`` section, verbatim.

    Returns everything between that heading and the next ``## [`` heading (or the
    end of the file), stripped of surrounding blank lines. Raises ``ValueError``
    if the section is absent or empty, so the release step fails loudly rather
    than cutting a release with no notes (belt-and-braces: on a green build
    ``test_changelog_documents_the_current_version`` already guarantees the
    current version has a section here). The heading match ends at end-of-line
    rather than requiring a trailing newline, so a section whose heading is the
    file's final line with no newline is diagnosed as *empty*, not as absent.
    """
    heading = re.search(rf"^## \[{re.escape(version)}\][^\n]*$", changelog_text, re.M)
    if heading is None:
        raise ValueError(f"CHANGELOG.md has no `## [{version}]` section")
    rest = changelog_text[heading.end() :]
    nxt = re.search(r"^## \[", rest, re.M)
    body = (rest[: nxt.start()] if nxt else rest).strip()
    if not body:
        raise ValueError(f"CHANGELOG.md's `## [{version}]` section is empty")
    return body


def versions_to_release(changelog_text: str, latest_released: str | None) -> list[str]:
    """CHANGELOG versions newer than the latest released one, oldest-first.

    ``latest_released`` is the latest release's tag (e.g. ``"v0.11.0"``, the
    leading ``v`` optional) or empty/``None`` when the repo has no releases yet.
    Because the changelog is newest-first, "newer than the watermark" is simply
    "listed above it" — the prefix up to the watermark, returned oldest-first so a
    caller creates them in ascending order and marks only the newest ``--latest``.

    With no watermark it returns just the newest version — the conservative choice
    that matches the old single-version behaviour rather than back-filling the
    entire history (this repo's ``0.1.0``–``0.6.0`` carry tags but deliberately no
    releases; the watermark keeps the job from resurrecting them).

    A watermark that is *present but not a changelog version* raises ``ValueError``.
    That branch used to fail **open** — it treated every version as newer and
    returned the whole file, resurrecting exactly the ``0.1.0``–``0.6.0`` the
    paragraph above promises never to release, and doing it green (each of those
    sections is non-empty, so ``extract_release_notes`` would not object either).
    It is reachable from a hand-cut release whose tag has no ``## [x.y.z]`` section,
    or from trimming old entries out of ``CHANGELOG.md``. Failing loudly is the same
    choice ``extract_release_notes`` makes about missing notes.
    """
    versions = changelog_versions(changelog_text)  # newest-first
    watermark = (latest_released or "").lstrip("v")
    if not watermark:
        return versions[:1]
    if watermark not in versions:
        raise ValueError(
            f"latest release {latest_released!r} is not a CHANGELOG.md version"
        )
    return versions[: versions.index(watermark)][::-1]


def main(argv: list[str] | None = None) -> int:
    """CLI for the release job.

    ``version``          prints ``pyproject.toml``'s current version.
    ``notes VERSION``    prints VERSION's changelog section.
    ``to-release TAG``   prints the versions above the latest-release TAG,
                         oldest-first, one per line.
    """
    args = sys.argv[1:] if argv is None else argv
    cmd = args[0] if args else ""
    if cmd == "version" and len(args) == 1:
        print(read_version((ROOT / "pyproject.toml").read_text()))
        return 0
    if cmd == "notes" and len(args) == 2:
        print(extract_release_notes((ROOT / "CHANGELOG.md").read_text(), args[1]))
        return 0
    if cmd == "to-release" and len(args) == 2:
        for v in versions_to_release((ROOT / "CHANGELOG.md").read_text(), args[1]):
            print(v)
        return 0
    print(
        "usage: release.py {version | notes VERSION | to-release LATEST_TAG}",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
