import pytest

from safia_sec.gym.injections import APP_DIR, APPS, TEMPLATES, all_templates, app_dir, build
import functools

from safia_sec.gym import referee
from safia_sec.gym.referee import Submission, check_source
from safia_sec.gym.referee import judge as _judge

# All code in these tests is ours, so it may run without the namespace sandbox (e.g. on macOS).
judge = functools.partial(_judge, trusted=True)

SRC = (APP_DIR / "app.py").read_text()


@pytest.mark.parametrize("cwe", sorted(TEMPLATES))
def test_golden_template_is_accepted(cwe):
    verdict = judge(APP_DIR, build(cwe))
    assert verdict.accepted, (verdict.reason, verdict.detail)


def sqli(**over):
    sub = build("CWE-89")
    return Submission(over.get("cwe", sub.cwe), over.get("patch", sub.patch),
                      over.get("exploit_test", sub.exploit_test), over.get("marker", sub.marker))


def test_exploit_that_always_passes_is_rejected():
    v = judge(APP_DIR, sqli(exploit_test="def test_x():\n    assert True  # INTERNAL-RECIPE-DRAFT\n"))
    assert v.reason == "exploit_passes_on_original"


def test_exploit_that_fails_on_patched_is_rejected():
    bad = build("CWE-89").exploit_test.replace("OR 1=1", "OR 1=2")
    assert judge(APP_DIR, sqli(exploit_test=bad)).reason == "exploit_fails_on_patched"


def test_patch_that_breaks_functional_tests_is_rejected():
    patch = {"app.py": build("CWE-89").patch["app.py"].replace("return jsonify([dict(r) for r in rows])",
                                                              "return 'oops'")}
    assert judge(APP_DIR, sqli(patch=patch)).reason == "patch_breaks_tests"


def test_syntax_error_in_exploit_is_rejected():
    assert judge(APP_DIR, sqli(exploit_test="def test_x(:\n  # INTERNAL-RECIPE-DRAFT")).reason \
           == "static_check_exploit"


def test_exploit_importing_os_is_rejected():
    src = "import os\n" + build("CWE-89").exploit_test
    assert judge(APP_DIR, sqli(exploit_test=src)).reason == "static_check_exploit"


def test_patch_with_os_system_is_rejected():
    patch = {"app.py": build("CWE-89").patch["app.py"] + "\nos.system('id')\n"}
    assert judge(APP_DIR, sqli(patch=patch)).reason == "static_check_patch"


def test_patching_tests_is_rejected():
    assert judge(APP_DIR, sqli(patch={"tests/test_app.py": "x = 1\n"})).reason == "bad_path"


def test_path_escape_is_rejected():
    assert judge(APP_DIR, sqli(patch={"../evil.py": "x = 1\n"})).reason == "bad_path"


def test_missing_marker_is_rejected():
    assert judge(APP_DIR, sqli(marker="NOT-IN-THE-EXPLOIT")).reason == "missing_marker"


def test_unchanged_patch_is_rejected():
    assert judge(APP_DIR, sqli(patch={"app.py": SRC})).reason == "empty_patch"


def test_hanging_patch_times_out():
    patch = {"app.py": build("CWE-89").patch["app.py"] + "\nwhile True:\n    pass\n"}
    assert judge(APP_DIR, sqli(patch=patch), timeout=5).reason == "timeout"


@pytest.mark.parametrize("src", [
    "import urllib.request\n",
    "from urllib import request\n",
    "import urllib\n",
    "from urllib.request import urlopen\n",
    "import pathlib\n",
    "import os\nos.open('/tmp/x', 0)\n",
    "from os import system\n",
])
def test_static_policy_blocks_network_and_write_paths(src):
    assert check_source(src, referee.APP_IMPORTS, allow_writes=True) is not None


def test_urllib_parse_is_allowed():
    assert check_source("from urllib.parse import quote\n", referee.APP_IMPORTS, allow_writes=True) is None


def test_untrusted_code_is_refused_without_isolation(monkeypatch):
    monkeypatch.setattr(referee, "NETNS", False)
    assert _judge(APP_DIR, build("CWE-89")).reason == "no_isolation"


@pytest.mark.skipif(not referee.NETNS, reason="needs Linux network namespaces")
def test_untrusted_golden_is_accepted_with_isolation():
    verdict = _judge(APP_DIR, build("CWE-89"))
    assert verdict.accepted and verdict.isolated


@pytest.mark.parametrize("app,cwe", all_templates())
def test_every_app_template_is_accepted(app, cwe):
    verdict = judge(app_dir(app), build(cwe, app))
    assert verdict.accepted, (app, cwe, verdict.reason, verdict.detail)


def test_registry_has_three_apps_and_eleven_templates():
    assert set(APPS) == {"shop", "bank", "blog"} and len(all_templates()) == 11
