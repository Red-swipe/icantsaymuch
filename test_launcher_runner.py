# -*- coding: utf-8 -*-
"""
Disposable test launcher runner that mirrors E:\A.G\release test\Mentis Test\launcher.py
with an optional startup delay parameter and spy recording for browser launch.
Isolated completely in Temp. Never touches repo or release files.
"""
import argparse
import os
from pathlib import Path
import socket
import sys
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer

APP_DIR = Path(r"E:\A.G\release test\Mentis Test").resolve()
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR))

import mvp_server

def free_port(start=8200, tries=50):
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--spy-file", type=str, default="")
    args = parser.parse_args()

    port = args.port if args.port else free_port()
    url = f"http://127.0.0.1:{port}/"

    t_start = time.time()
    print(f"[RUNNER] Startup delay config: {args.delay:.2f}s")
    print(f"[RUNNER] Target port: {port}")
    print(f"[RUNNER] t0 = {t_start:.4f}")

    def start_server():
        if args.delay > 0:
            print(f"[RUNNER] Injecting artificial startup delay: sleeping {args.delay:.2f}s at t={time.time()-t_start:.3f}s")
            time.sleep(args.delay)
        print(f"[RUNNER] Binding and starting ThreadingHTTPServer at t={time.time()-t_start:.3f}s")
        srv = ThreadingHTTPServer(("127.0.0.1", port), mvp_server.MvpHandler)
        srv.serve_forever()

    threading.Thread(target=start_server, daemon=True).start()

    probe_succeeded = False
    probe_polls = 0
    # Exact polling loop from launcher.py: lines 87-92
    for _ in range(100):
        probe_polls += 1
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                resp.read(1)
                probe_succeeded = True
                print(f"[RUNNER] Probe SUCCEEDED at poll {probe_polls} (t={time.time() - t_start:.3f}s)")
                break
        except Exception:
            time.sleep(0.1)

    t_probe_end = time.time() - t_start
    if not probe_succeeded:
        print(f"[RUNNER] Probe LOOP EXHAUSTED after {probe_polls} polls (t={t_probe_end:.3f}s) - NO ERROR RAISED BY LAUNCHER")

    # Exact launcher.py output: lines 93-98
    print("")
    print("  Calculator is running at " + url)
    print("  Your browser should open by itself.")
    print("  If it does not, copy the address above into Chrome or Edge.")
    print("  CLOSE THIS WINDOW to stop the calculator.")
    print("")

    # Browser open simulation
    t_open = time.time() - t_start
    print(f"[RUNNER] webbrowser.open({url}) called at t={t_open:.3f}s")

    if args.spy_file:
        try:
            with open(args.spy_file, "w", encoding="utf-8") as f:
                f.write(f"OPEN_CALLED|url={url}|t_open={t_open:.4f}|probe_succeeded={probe_succeeded}|polls={probe_polls}")
        except Exception as e:
            print(f"[RUNNER] spy file write error: {e}")

    # Keep process alive until killed by orchestrator
    while True:
        time.sleep(0.5)

if __name__ == "__main__":
    main()
