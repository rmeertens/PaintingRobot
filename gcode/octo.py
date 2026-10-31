#!/usr/bin/env python3
"""Drive OctoPrint for the painting rig, using your own API key.

Key: paste it into ../.secrets.env (OCTOPRINT_KEY=...), or export OCTOPRINT_KEY in your shell.

Commands (run from this folder):
    python3 octo.py status              printer state + job progress
    python3 octo.py home                home X, Y and Z, then drop the bed 20 mm (cartridge OFF!)
    python3 octo.py home -no-brush      same, without asking whether the cartridge is off
    python3 octo.py home-xy             home X/Y only (cartridge OFF!)
    python3 octo.py z 50                move bed to absolute Z (Z up = bed down)
    python3 octo.py xy 12.6 23          move the head to printer X/Y (keep the bed low first!)
    python3 octo.py jog -0.1            relative Z move (negative = bed up toward brush)
    python3 octo.py upload FILE.gcode   upload to OctoPrint
    python3 octo.py send FILE.gcode     upload, show a summary, ask to confirm, then start it
    python3 octo.py start FILE.gcode    select and start a job (no checks)
    python3 octo.py pause | resume | cancel
    python3 octo.py snap [N] [SEC]      save N webcam snapshots, SEC apart, to ./snapshots/
    python3 octo.py watch FILE.gcode    start the job and snapshot every 10 s until it ends
"""
import json, os, sys, time, uuid, urllib.request, urllib.error

def _load_secrets():
    """Read KEY=value lines from ../.secrets.env; real environment variables win."""
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".secrets.env")
    vals = {}
    if os.path.exists(f):
        for line in open(f):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
    return vals


_SECRETS = _load_secrets()
URL = (os.environ.get("OCTOPRINT_URL") or _SECRETS.get("OCTOPRINT_URL") or "http://octopi.local").rstrip("/")
KEY = os.environ.get("OCTOPRINT_KEY") or _SECRETS.get("OCTOPRINT_KEY")
HOME_DROP = 20   # mm the bed drops after homing (Z up = bed down)
SNAP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")


def req(method, path, body=None, ctype="application/json", raw=False):
    if not KEY:
        sys.exit("No API key: paste it into .secrets.env (OCTOPRINT_KEY=...) in the project folder")
    data = json.dumps(body).encode() if isinstance(body, dict) else body
    r = urllib.request.Request(URL + path, data=data, method=method,
                               headers={"X-Api-Key": KEY, "Content-Type": ctype})
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            out = resp.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
    if raw:
        return out
    return json.loads(out) if out else None


def gcode(*cmds):
    req("POST", "/api/printer/command", {"commands": list(cmds)})
    print("sent:", "; ".join(cmds))


def upload(path):
    b = uuid.uuid4().hex
    name = os.path.basename(path)
    parts = [f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
             f'Content-Type: application/octet-stream\r\n\r\n'.encode(), open(path, "rb").read(), b"\r\n"]
    for k, v in (("select", "false"), ("print", "false")):
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f"--{b}--\r\n".encode())
    req("POST", "/api/files/local", b"".join(parts), f"multipart/form-data; boundary={b}")
    print("uploaded", name)
    return name


def status():
    p = req("GET", "/api/printer?exclude=temperature,sd")
    j = req("GET", "/api/job")
    prog = j.get("progress") or {}
    print("state:", p["state"]["text"], "| file:", (j.get("job") or {}).get("file", {}).get("name"),
          "| done:", f'{(prog.get("completion") or 0):.0f}%')
    return p["state"]["text"]


def snap(n=1, every=0):
    os.makedirs(SNAP_DIR, exist_ok=True)
    for i in range(n):
        img = urllib.request.urlopen(URL + "/webcam/?action=snapshot", timeout=20).read()
        f = os.path.join(SNAP_DIR, time.strftime("snap_%H%M%S.jpg"))
        open(f, "wb").write(img)
        print("saved", f)
        if i < n - 1:
            time.sleep(every)


def start(path):
    name = upload(path) if os.path.exists(path) else os.path.basename(path)
    req("POST", f"/api/files/local/{name}", {"command": "select", "print": True})
    print("started", name)


def confirm(question):
    return input(question + " [y/N] ").strip().lower() in ("y", "yes")


def home(no_brush=False):
    if no_brush:
        print("-no-brush: skipping the cartridge check.")
    elif not confirm("Cartridge OFF? Homing Z raises the bed to nozzle height."):
        sys.exit("Not homed.")
    gcode("G90", "G28", f"G1 Z{HOME_DROP} F600")
    print(f"Homed. Bed is {HOME_DROP} mm down: attach the cartridge now.")


def send(path):
    if not os.path.exists(path):
        sys.exit(f"No such file: {path}")
    state = status()
    if state != "Operational":
        sys.exit(f"Printer is '{state}', not idle: not sending.")
    lines = [l.strip() for l in open(path) if l.strip()]
    moves = sum(1 for l in lines if l[:2] in ("G0", "G1"))
    print(f"\n{os.path.basename(path)}: {len(lines)} lines, {moves} moves")
    for l in lines[:6]:
        if l.startswith(";"):
            print("  " + l)
    if not confirm("Upload and start this job now?"):
        sys.exit("Not started.")
    start(path)
    print("Running. Stop it any time with: python3 octo.py cancel")


def main(a):
    if not a:
        sys.exit(__doc__)
    c = a[0]
    if c == "status": status()
    elif c == "home": home(no_brush="-no-brush" in a[1:] or "--no-brush" in a[1:])
    elif c == "home-xy": gcode("G28 X Y")
    elif c == "z": gcode("G90", f"G1 Z{float(a[1])} F600")
    elif c == "xy": gcode("G90", f"G1 X{float(a[1])} Y{float(a[2])} F3000")
    elif c == "jog": gcode("G91", f"G1 Z{float(a[1])} F300", "G90")
    elif c == "upload": upload(a[1])
    elif c == "send": send(a[1])
    elif c == "start": start(a[1])
    elif c in ("pause", "resume"): req("POST", "/api/job", {"command": "pause", "action": c})
    elif c == "cancel": req("POST", "/api/job", {"command": "cancel"}); print("cancelled")
    elif c == "snap": snap(int(a[1]) if len(a) > 1 else 1, float(a[2]) if len(a) > 2 else 5)
    elif c == "watch":
        start(a[1])
        time.sleep(3)
        while status() in ("Printing", "Pausing", "Paused", "Starting"):
            snap()
            time.sleep(10)
        snap()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
