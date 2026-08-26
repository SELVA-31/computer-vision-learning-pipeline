"""
check_repo.py - audit the repository for things that drift out of sync.

Documentation rots silently. A slider default changes in code, the README keeps
the old number, and nobody notices until a reader tries it. This checks the
claims that can be checked mechanically:

  1. File sizes        - nothing large enough to bloat the repo or be rejected
  2. Referenced images - every image a README points at exists on disk
  3. Placeholders      - no template text left behind
  4. Trackbar tables   - README control tables match cv2.createTrackbar() calls
  5. Line citations    - "line N" references land inside their file
  6. Dependencies      - requirements.txt covers what the modules import
  7. Content claims    - cited lines still contain what the README says they do
  8. Camera config     - all modules pin the same camera properties
  9. Shared scaffold   - copied helper functions have not drifted apart

Run:  python tools/check_repo.py
Exit code 0 = clean, 1 = findings.
"""

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

SIZE_FAIL_MB = 10.0
SIZE_WARN_MB = 5.0

PLACEHOLDERS = [
    "YOUR_REAL_ID", "Your Full Name", "12345678+", "TODO:", "FIXME",
    "Lorem ipsum", "<placeholder>", "TBD",
]

STDLIB = {"math", "time", "os", "sys", "argparse", "shutil", "subprocess",
          "pathlib", "importlib", "py_compile", "ast", "re", "io"}

DIST_TO_IMPORT = {"opencv-python": "cv2", "imageio-ffmpeg": "imageio_ffmpeg"}

# (module dir, function name, text that must appear inside it, what the README says)
# Pinned to functions rather than line numbers: line numbers moved three times
# during development and invalidated every citation each time. Function names
# survive edits above them.
CLAIMS = [
    ("module-01-camera-conditioning", "main", "exposure = cap.get(cv2.CAP_PROP_EXPOSURE)",
     "module 1 README: exposure read once in main() before the loop"),
    ("module-01-camera-conditioning", "main", "gain = cap.get(cv2.CAP_PROP_GAIN)",
     "module 1 README: gain read once in main() before the loop"),
    ("module-03-preprocessing", "main", '"h_lower": 0, "s_lower": 120',
     "module 2 README: module 3 holds its own HSV bounds in main()"),
    ("module-04-pattern-detection", "detect_hough_circles", "minDist=50",
     "module 4 README: Hough minDist hardcoded in detect_hough_circles()"),
    ("module-04-pattern-detection", "detect_hough_circles", "param1=100",
     "module 4 README: Hough param1 hardcoded in detect_hough_circles()"),
]

# Facts asserted in prose that must remain true of the source as a whole.
SUBSTRING_CLAIMS = [
    ("module-01-camera-conditioning", "cv2.CAP_PROP_AUTO_WB, 0.0",
     "module 1 README: auto white balance disabled"),
    ("module-01-camera-conditioning", "cv2.CAP_PROP_EXPOSURE, -6.0",
     "module 1 README: exposure pinned to -6.0"),
    ("module-01-camera-conditioning", "hist.flatten()",
     "module 1 README: numpy 2.x histogram fix applied"),
    ("module-02-hsv-segmentation", "np.array([170,",
     "module 2 README: dual-range red upper band at 170"),
    ("module-04-pattern-detection", "param1=100",
     "module 4: Hough param1 is hardcoded, not a slider"),
    ("module-04-pattern-detection", "minDist=50",
     "module 4: Hough minDist is hardcoded"),
]

# Text that must NOT be present - regressions we have already removed.
ABSENT_CLAIMS = [
    ("module-02-hsv-segmentation", "create_color_wheel",
     "module 2: dead colour-wheel code stays removed"),
]

findings = []
warnings = []


def fail(msg):
    findings.append(msg)
    print(f"  FAIL  {msg}")


def warn(msg):
    warnings.append(msg)
    print(f"  WARN  {msg}")


def ok(msg):
    print(f"  ok    {msg}")


def readmes():
    return sorted(ROOT.glob("README.md")) + sorted(ROOT.glob("module-0*/README.md"))


def rel(path):
    return path.relative_to(ROOT).as_posix()


def source_for(module):
    matches = sorted(ROOT.glob(f"{module}/code/*.py"))
    return matches[0] if matches else None


def check_sizes():
    print()
    print("[1] File sizes")
    oversized = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        mb = path.stat().st_size / (1024 * 1024)
        if mb >= SIZE_WARN_MB:
            oversized.append((mb, path))
    for mb, path in sorted(oversized, reverse=True):
        if mb >= SIZE_FAIL_MB:
            fail(f"{rel(path)} is {mb:.1f} MB (limit {SIZE_FAIL_MB:.0f} MB)")
        else:
            warn(f"{rel(path)} is {mb:.1f} MB")
    if not oversized:
        ok(f"no file over {SIZE_WARN_MB:.0f} MB")

    clips = sorted(ROOT.glob("module-0*/video/*.mp4"))
    if clips:
        total = sum(c.stat().st_size for c in clips) / (1024 * 1024)
        ok(f"{len(clips)} clip(s), {total:.1f} MB total")
    else:
        warn("no clips present - module READMEs reference video that is not here")


def check_links():
    print()
    print("[2] Referenced images and links")
    pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    checked = 0
    for md in readmes():
        for target in pattern.findall(md.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = target.split("#")[0]
            if not target:
                continue
            checked += 1
            if not (md.parent / target).resolve().exists():
                fail(f"{rel(md)} -> missing target '{target}'")
    ok(f"{checked} local link(s)/image(s) resolve")


def check_placeholders():
    print()
    print("[3] Placeholder text")
    hits = 0
    for path in list(readmes()) + [ROOT / "LICENSE", ROOT / "requirements.txt"]:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in PLACEHOLDERS:
            if token in text:
                fail(f"{rel(path)} contains placeholder '{token}'")
                hits += 1
    if not hits:
        ok("none found")


def trackbars_in(source):
    """Extract {name: (default, maximum)} from cv2.createTrackbar() calls."""
    found = {}
    for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if not (isinstance(fn, ast.Attribute) and fn.attr == "createTrackbar"):
            continue
        if len(node.args) < 4:
            continue
        try:
            name = ast.literal_eval(node.args[0])
            default = ast.literal_eval(node.args[2])
            maximum = ast.literal_eval(node.args[3])
        except (ValueError, SyntaxError):
            continue
        found[name] = (default, maximum)
    return found


def check_trackbars():
    print()
    print("[4] README control tables vs createTrackbar()")
    documented_any = False
    for module_dir in sorted(ROOT.glob("module-0*")):
        readme = module_dir / "README.md"
        source = source_for(module_dir.name)
        if not readme.exists() or source is None:
            continue
        documented_any = True
        code = trackbars_in(source)
        text = readme.read_text(encoding="utf-8")

        for name, (default, maximum) in code.items():
            row = re.search(r"^\|\s*" + re.escape(name) + r"\s*\|([^\n]*)$",
                            text, re.M | re.I)
            if not row:
                fail(f"{rel(readme)}: slider '{name}' exists in code but is "
                     f"missing from the control table")
                continue
            # Ranges are written "0-100"; a signed pattern would read the
            # upper bound as -100 and never match.
            blob = row.group(1).replace("–", "-")
            nums = re.findall(r"\d+", blob)
            if str(maximum) not in nums:
                fail(f"{rel(readme)}: '{name}' max is {maximum} in code, "
                     f"not in the table row")
            elif str(default) not in nums:
                fail(f"{rel(readme)}: '{name}' default is {default} in code, "
                     f"not in the table row")
            else:
                ok(f"{module_dir.name}: {name} (default {default}, max {maximum})")

        for row_name in re.findall(
                r"^\|\s*([A-Z][A-Za-z0-9 ]{2,20}?)\s*\|\s*\d+\s*[-–]\s*\d+",
                text, re.M):
            if row_name.strip() not in code:
                fail(f"{rel(readme)}: table lists '{row_name.strip()}' but no "
                     f"such trackbar exists in code")
    if not documented_any:
        warn("no module README has a control table yet")


def check_line_citations():
    print()
    print("[5] Line-number citations land inside their file")
    file_ref = re.compile(r"`?([A-Za-z0-9_]+\.py)`?:(\d+)")
    bare_ref = re.compile(r"\(lines?\s+(\d+)")
    total = 0
    for md in readmes():
        text = md.read_text(encoding="utf-8")
        for match in file_ref.finditer(text):
            fname, lineno = match.group(1), int(match.group(2))
            matches = sorted(ROOT.glob(f"module-0*/code/{fname}"))
            if not matches:
                fail(f"{rel(md)}: cites unknown file '{fname}'")
                continue
            total += 1
            count = len(matches[0].read_text(encoding="utf-8").splitlines())
            if lineno > count:
                fail(f"{rel(md)}: {fname}:{lineno} is past end of file ({count} lines)")

        source = source_for(md.parent.name) if md.parent != ROOT else None
        if source is not None:
            count = len(source.read_text(encoding="utf-8").splitlines())
            for match in bare_ref.finditer(text):
                total += 1
                if int(match.group(1)) > count:
                    fail(f"{rel(md)}: cites line {match.group(1)}, "
                         f"{source.name} has {count} lines")
    ok(f"{total} citation(s) in range")


def check_requirements():
    print()
    print("[6] requirements.txt vs imports")
    declared = set()
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        dist = re.split(r"[=<>!~\[]", line)[0].strip().lower()
        declared.add(DIST_TO_IMPORT.get(dist, dist.replace("-", "_")))

    imported = set()
    for source in sorted(ROOT.glob("module-0*/code/*.py")):
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                imported.add(node.module.split(".")[0])

    third_party = imported - STDLIB
    for name in sorted(third_party):
        if name in declared:
            ok(f"{name} declared")
        else:
            fail(f"module code imports '{name}' but requirements.txt omits it")
    for name in sorted(declared - third_party):
        warn(f"requirements.txt declares '{name}', not imported by any module")


def check_claims():
    print()
    print("[7] Content-verified documentation claims")
    for module, fn_name, expected, label in CLAIMS:
        source = source_for(module)
        if source is None:
            fail(f"{label}: no source found under {module}/code/")
            continue
        text = source.read_text(encoding="utf-8")
        lines = text.splitlines()
        body = None
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == fn_name:
                body = lines[node.lineno - 1:node.end_lineno]
                break
        if body is None:
            fail(f"{label}: {source.name} has no function named {fn_name}()")
        elif not any(expected in line for line in body):
            fail(f"{label}: {fn_name}() in {source.name} no longer contains "
                 f"'{expected}' - update the README")
        else:
            ok(f"{label}")

    for module, expected, label in SUBSTRING_CLAIMS:
        source = source_for(module)
        if source is None or expected not in source.read_text(encoding="utf-8"):
            fail(f"{label}: '{expected}' not found")
        else:
            ok(label)

    for module, absent, label in ABSENT_CLAIMS:
        source = source_for(module)
        if source is not None and absent in source.read_text(encoding="utf-8"):
            fail(f"{label}: '{absent}' has reappeared in {source.name}")
        else:
            ok(label)


def check_camera_config():
    """Every module must configure the camera identically.

    Windows camera drivers keep property state between processes. A module that
    leaves a control unset silently inherits whatever the previous run left
    behind, so running module 3 after module 1 gives different frames than
    running it after a reboot. Divergence here is a reproducibility bug, not a
    style issue.
    """
    print()
    print("[8] Camera configuration consistency")
    props = ["CAP_PROP_FRAME_WIDTH", "CAP_PROP_FRAME_HEIGHT", "CAP_PROP_AUTO_EXPOSURE",
             "CAP_PROP_EXPOSURE", "CAP_PROP_GAIN", "CAP_PROP_AUTO_WB", "CAP_PROP_FPS"]
    table = {}
    for module_dir in sorted(ROOT.glob("module-0*")):
        source = source_for(module_dir.name)
        if source is None:
            continue
        text = source.read_text(encoding="utf-8")
        table[module_dir.name] = {
            prop: (re.search(rf"cv2\.{prop},\s*([-\d.]+)\)", text) or [None, None])[1]
            for prop in props
        }
    if len(table) < 2:
        warn("fewer than two modules found, nothing to compare")
        return
    for prop in props:
        values = {name: cfg[prop] for name, cfg in table.items()}
        distinct = set(values.values())
        if len(distinct) == 1:
            only = distinct.pop()
            if only is None:
                warn(f"{prop} is set by no module")
            else:
                ok(f"{prop} = {only} in all {len(values)} modules")
        else:
            odd = [n for n, v in values.items() if v is None]
            if odd:
                fail(f"{prop} is not set by: {', '.join(sorted(odd))} "
                     f"- those modules inherit stale driver state")
            else:
                fail(f"{prop} differs across modules: "
                     + ", ".join(f"{n}={v}" for n, v in sorted(values.items())))


SHARED_FUNCTIONS = ("nothing", "initialize_camera", "mouse_callback",
                    "create_single_screen")


def check_shared_functions():
    """The scaffolding each module copies must stay byte-identical.

    These five programs are deliberately standalone - a reader can copy one file
    and run it. The cost of that choice is five copies of the same scaffolding,
    and copies drift. Keeping them identical means the duplication is a
    deliberate trade-off rather than an accident waiting to bite.
    """
    print()
    print("[9] Shared scaffolding is identical across modules")
    import hashlib
    seen = {}
    for module_dir in sorted(ROOT.glob("module-0*")):
        source = source_for(module_dir.name)
        if source is None:
            continue
        text = source.read_text(encoding="utf-8")
        lines = text.splitlines()
        for node in ast.parse(text).body:
            if isinstance(node, ast.FunctionDef) and node.name in SHARED_FUNCTIONS:
                body = "\n".join(l.rstrip()
                                 for l in lines[node.lineno - 1:node.end_lineno]
                                 if l.strip())
                digest = hashlib.md5(body.encode()).hexdigest()
                seen.setdefault(node.name, {}).setdefault(digest, []).append(module_dir.name)

    for name in SHARED_FUNCTIONS:
        variants = seen.get(name)
        if not variants:
            fail(f"{name}() is missing from every module")
        elif len(variants) == 1:
            copies = sum(len(v) for v in variants.values())
            ok(f"{name}() identical across {copies} modules")
        else:
            groups = " | ".join(", ".join(sorted(v)) for v in variants.values())
            fail(f"{name}() has {len(variants)} variants: {groups}")


def main():
    print(f"Auditing {ROOT.name}")
    check_sizes()
    check_links()
    check_placeholders()
    check_trackbars()
    check_line_citations()
    check_requirements()
    check_claims()
    check_camera_config()
    check_shared_functions()

    print()
    print("=" * 62)
    if findings:
        print(f"{len(findings)} finding(s), {len(warnings)} warning(s)")
        return 1
    print(f"Clean. {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
