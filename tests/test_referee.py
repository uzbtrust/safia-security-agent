import pytest

from safia_sec.gym.injections import APP_DIR, TEMPLATES, build
from safia_sec.gym.referee import Submission, judge

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
