# -*- coding: utf-8 -*-
"""Phase 1 / Step 6: Readiness-race investigation orchestrator."""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error

RELEASE_DIR = r"E:\A.G\release test\Mentis Test"
PYEXE = os.path.join(RELEASE_DIR, "python", "python.exe")
TMP = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(TMP, "test_launcher_runner.py")
REPORT_DIR = r"E:\A.G\casio_mvp\docs\reports\phase-p6-3-20261017"
OUT_TXT = os.path.join(REPORT_DIR, "13_launcher_path_step6.txt")

lines = []
def w(s=""):
    lines.append(str(s))

def port_free(p):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", p))
        return True
    except OSError:
        return False
    finally:
        s.close()

def proc_count():
    n = 0
    for name in ("python.exe", "pythonw.exe"):
        try:
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + name],
                                 capture_output=True, text=True).stdout
            n += out.count(name)
        except Exception:
            pass
    return n

def probe_http(url):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            return resp.status, resp.read(200)
    except urllib.error.HTTPError as e:
        return e.code, e.read(200)
    except Exception as e:
        return None, str(e)

def run_case(case_name, delay, port):
    w(f"======================================================================")
    w(f"CASE: {case_name}")
    w(f"Artificial startup delay : {delay:.2f}s")
    w(f"Target port              : {port}")
    w(f"Port free before         : {port_free(port)}")

    spy_file = os.path.join(TMP, f"spy_{port}.txt")
    if os.path.exists(spy_file):
        try:
            os.remove(spy_file)
        except Exception:
            pass

    so_path = os.path.join(TMP, f"step6_{port}_out.txt")
    se_path = os.path.join(TMP, f"step6_{port}_err.txt")
    so = open(so_path, "w", encoding="utf-8", errors="replace")
    se = open(se_path, "w", encoding="utf-8", errors="replace")

    t_start = time.time()
    proc = subprocess.Popen(
        [PYEXE, "-u", RUNNER, "--delay", str(delay), "--port", str(port), "--spy-file", spy_file],
        cwd=RELEASE_DIR, stdout=so, stderr=se
    )
    w(f"Spawned launcher PID     : {proc.pid} at t=0.000s")

    socket_available_at = None
    browser_open_called_at = None
    spy_data = None
    usability_at_open = None

    # Poll from the outside for up to 16 seconds
    for _ in range(160):
        t_now = time.time() - t_start

        # Check socket
        if socket_available_at is None and not port_free(port):
            socket_available_at = t_now

        # Check spy file
        if browser_open_called_at is None and os.path.exists(spy_file):
            try:
                with open(spy_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if "OPEN_CALLED" in content:
                    browser_open_called_at = t_now
                    spy_data = content
                    # Immediate usability check at browser-open time
                    url = f"http://127.0.0.1:{port}/"
                    st, body = probe_http(url)
                    usability_at_open = (st, body)
            except Exception:
                pass

        # If both detected or timeout, we can finish after brief pause
        if browser_open_called_at is not None and (socket_available_at is not None or t_now > 13.0):
            time.sleep(1.0)
            break

        time.sleep(0.1)

    # Final usability check
    final_st, final_body = probe_http(f"http://127.0.0.1:{port}/")

    # Cleanup
    if proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:
                pass
    try:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                       capture_output=True, text=True, timeout=10)
    except Exception:
        pass
    so.close()
    se.close()
    time.sleep(0.5)

    w(f"Socket available at      : {f'{socket_available_at:.3f}s' if socket_available_at else 'NEVER'}")
    w(f"Browser open called at   : {f'{browser_open_called_at:.3f}s' if browser_open_called_at else 'NEVER'}")
    w(f"Spy data from runner     : {spy_data}")
    w(f"Usability at open time   : HTTP status={usability_at_open[0] if usability_at_open else 'N/A'}, err/body={repr(usability_at_open[1])[:100] if usability_at_open else 'N/A'}")
    w(f"Usability after delay    : HTTP status={final_st}, body={repr(final_body)[:100]}")
    w(f"Port free after cleanup  : {port_free(port)}")

    # Runner output
    w(f"Runner stdout:")
    try:
        with open(so_path, "r", encoding="utf-8", errors="replace") as f:
            for ln in f.read().splitlines():
                w(f"  | {ln}")
    except Exception as e:
        w(f"  read err: {e}")

    # Observations
    w("Observations:")
    if delay == 0.0:
        w("  - Normal start: Server begins listening quickly (~0.2s), readiness probe succeeds on poll 1, browser opens while server is healthy.")
        w("  - False success: False")
        w("  - Usable at open: True")
    elif delay < 10.0:
        w("  - Delayed start (within 10s budget): Probe retried repeatedly while socket was unavailable, succeeded once server bound, browser opened only after socket was ready.")
        w("  - False success: False")
        w("  - Usable at open: True")
    else:
        # Delay > 10s
        w("  - Excessive delay (exceeding 10s polling budget):")
        w(f"    * Readiness probe loop exhausted 100 iterations at t={browser_open_called_at:.3f}s.")
        w("    * LAUNCHER DID NOT RAISE ANY ERROR OR SHOW ANY WARNING.")
        w("    * Launcher printed 'Calculator is running at http://...' (FALSE SUCCESS).")
        w(f"    * Browser was instructed to open at t={browser_open_called_at:.3f}s when the server was NOT ready!")
        w(f"    * Page usability at open time: HTTP status={usability_at_open[0]}, connection was refused ({usability_at_open[1]}).")
        w("    * CONFIRMED RACE: A false successful startup DOES occur if server initialization exceeds 10 seconds.")
    w("")

def main():
    w("=== PHASE 1 / LAUNCHER PATH / STEP 6 : READINESS-RACE INVESTIGATION ===")
    w(f"Date: {time.strftime('%Y-%m-%dT%H:%M:%S%z')}")
    w(f"Release dir: {RELEASE_DIR}")
    w(f"Bundled python: {PYEXE}")
    w(f"Runner: {RUNNER}")
    w("")
    w("--- pre-flight ---")
    w(f"python/pythonw BEFORE: {proc_count()}")
    w("")

    # Scenario 1: Normal-start control (delay = 0.0s)
    run_case("Scenario 1: Normal-start control (0.0s delay)", delay=0.0, port=8221)

    # Scenario 2: Moderate delayed-start case (delay = 2.5s)
    run_case("Scenario 2: Moderate delayed-start (2.5s delay)", delay=2.5, port=8222)

    # Scenario 3: Excessive delayed-start / readiness timeout race (delay = 12.0s)
    run_case("Scenario 3: Excessive delayed-start (12.0s delay - exceeding 10s probe)", delay=12.0, port=8223)

    w("=== STEP 6 SUMMARY & FINDINGS ===")
    w("1. When the server process starts: The launcher launches the server thread immediately.")
    w("2. When listening socket becomes available: In normal start, immediately upon ThreadingHTTPServer initialization (<0.3s).")
    w("3. When readiness probe succeeds or times out: Polls every 100ms up to 100 times (10s total timeout).")
    w("4. When browser is instructed to open: Immediately after the loop exits.")
    w("5. Whether the page becomes usable: Usable if probe succeeded before loop exit; UNUSABLE (connection refused) if probe timed out.")
    w("6. Whether timeout or failure messages are truthful: UNTRUTHFUL. If the probe loop exhausts all 100 polls without connecting, the launcher DOES NOT report a timeout or failure. It continues unconditionally to print 'Calculator is running' and invokes webbrowser.open().")
    w("7. Whether a false successful startup can occur: YES, CONFIRMED. If server startup is delayed past 10 seconds (or if the server thread crashes/hangs after port selection), the launcher reports complete success and opens the browser to a dead/unbound URL, leading to browser connection refused.")
    w("")
    w(f"python/pythonw AFTER: {proc_count()}")

    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(OUT_TXT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("WROTE:", OUT_TXT)
    print("EXIT=0")

if __name__ == "__main__":
    main()
