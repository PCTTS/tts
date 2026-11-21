"""Talk to a running Tabletop Simulator through its External Editor API (localhost only).

  python -I tools/tts.py exec "<lua>"     run Lua in Global; prints its return value and any prints/errors
  python -I tools/tts.py get              copy the open game's scripts into .local/scripts/ (backup)
  python -I tools/tts.py push             load lua/Global.lua into the open game and reload it
  python -I tools/tts.py install "<save>" write lua/Global.lua into a save file on disk (game not open)

push refuses unless the open game's Global script is TTS's empty default or one of ours (contains PCTTS_MOD),
so it can never overwrite another mod's scripts. TTS only keeps the change in memory: save the game afterwards.
"""
import json, re, socket, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TTS_PORT, LISTEN_PORT = 39999, 39998
MARKER = "PCTTS_MOD"
NAMES = {0: "new object", 1: "game loaded", 2: "print", 3: "error", 4: "custom", 5: "return", 6: "game saved", 7: "object created"}


class Listener:
    """TTS opens a new connection to localhost:39998 for every message it sends."""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", LISTEN_PORT))
        self.sock.listen(16)
        self.sock.settimeout(0.25)

    def collect(self, seconds, until=None):
        msgs, end = [], time.time() + seconds
        while time.time() < end:
            try:
                conn, _ = self.sock.accept()
            except socket.timeout:
                continue
            with conn:
                conn.settimeout(5)
                data = b""
                while chunk := conn.recv(65536):
                    data += chunk
            for part in re.split(rb"(?<=\})\s*(?=\{\s*\"messageID\")", data.strip()):
                if part:
                    m = json.loads(part.decode("utf-8"))
                    msgs.append(m)
                    if until and until(m):
                        return msgs
        return msgs

    def close(self):
        self.sock.close()


def send(msg):
    with socket.create_connection(("127.0.0.1", TTS_PORT), timeout=5) as s:
        s.sendall(json.dumps(msg).encode("utf-8"))


def report(msgs):
    for m in msgs:
        kind = NAMES.get(m.get("messageID"), m.get("messageID"))
        if kind == "print":
            print("[print]", m.get("message"))
        elif kind == "error":
            print("[ERROR]", m.get("errorMessagePrefix", ""), m.get("error"))
        elif kind == "return":
            print("[return]", m.get("returnValue"))
        elif kind == "game loaded":
            print("[game loaded]", len(m.get("scriptStates", [])), "scripts")
        else:
            print(f"[{kind}]")


def exec_lua(code, wait=5):
    lis = Listener()
    try:
        send({"messageID": 3, "returnID": 1, "guid": "-1", "script": code})
        msgs = lis.collect(wait, until=lambda m: m.get("messageID") in (3, 5))
        msgs += lis.collect(0.5)
    finally:
        lis.close()
    return msgs


def get_scripts():
    lis = Listener()
    try:
        send({"messageID": 0})
        msgs = lis.collect(10, until=lambda m: m.get("messageID") in (0, 1))
    finally:
        lis.close()
    states = next((m["scriptStates"] for m in msgs if m.get("messageID") in (0, 1)), None)
    if states is None:
        sys.exit("TTS did not send its scripts back (is a game loaded?)")
    return states


def is_default(script):
    code = re.sub(r"--\[\[.*?\]\]|--[^\n]*", "", script or "", flags=re.S)
    code = re.sub(r"function\s+onLoad\s*\(\s*\)\s*end|function\s+onUpdate\s*\(\s*\)\s*end", "", code)
    return not code.strip()


def main(argv):
    cmd = argv[0] if argv else ""
    if cmd == "exec" and len(argv) > 1:
        report(exec_lua(argv[1]))
    elif cmd == "get":
        out = REPO / ".local" / "scripts" / time.strftime("%Y%m%d-%H%M%S")
        out.mkdir(parents=True)
        for st in get_scripts():
            stem = re.sub(r"[^\w-]+", "_", f"{st.get('name', '')}-{st.get('guid')}")
            (out / f"{stem}.lua").write_text(st.get("script") or "", encoding="utf-8")
            if st.get("ui"):
                (out / f"{stem}.xml").write_text(st["ui"], encoding="utf-8")
        print("saved scripts to", out.relative_to(REPO))
    elif cmd == "push":
        states = get_scripts()
        glob = next((s for s in states if s.get("guid") == "-1"), {})
        if not (is_default(glob.get("script")) or MARKER in (glob.get("script") or "")):
            sys.exit("Refusing to push: the open game's Global script isn't empty or ours. Is the right game loaded?")
        script = (REPO / "lua" / "Global.lua").read_text(encoding="utf-8")
        ui_file = REPO / "ui" / "Global.xml"
        ui = ui_file.read_text(encoding="utf-8") if ui_file.exists() else (glob.get("ui") or "")
        lis = Listener()
        try:
            send({"messageID": 1, "scriptStates": [{"name": "Global", "guid": "-1", "script": script, "ui": ui}]})
            report(lis.collect(12))
        finally:
            lis.close()
        print("Pushed. Save the game in TTS to keep it.")
    elif cmd == "install" and len(argv) > 1:
        # Write lua/Global.lua into a save file on disk (the game must not be open in TTS, or TTS will overwrite it).
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from stage_assets import resolve_save
        save = resolve_save(argv[1])
        data = json.loads(save.read_text(encoding="utf-8"))
        if not (is_default(data.get("LuaScript")) or MARKER in (data.get("LuaScript") or "")):
            sys.exit(f"Refusing: {save.name} already has a Global script that isn't ours.")
        data["LuaScript"] = (REPO / "lua" / "Global.lua").read_text(encoding="utf-8")
        data["XmlUI"] = ""  # the script builds its UI when the game loads
        save.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print("installed the spawner into", save.name)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
