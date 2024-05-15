import os
import sys
import time
import logging
import subprocess
import selectors
import threading
import shlex
from IPython.display import display
import ipywidgets as widgets
from subprocess import PIPE, STDOUT
from ipaddress import IPv4Network, IPv4Address


logging.basicConfig(stream=sys.stdout,
                    format='[%(asctime)s] %(levelname)s: %(msg)s',
                    level=logging.INFO)
log = logging.getLogger("FABFED")

class Session:
    def __init__(self, cmd, path=os.getcwd()):
        self.stop = False
        self.thr = None
        self.cmd = cmd
        self.path = path

def run_host_cmd(host, path, cmd, ofname=None, stop=None, interactive=False, out=None):
    log.debug(f"Running \"{cmd}\" on \"{host}\", with output to file \"{ofname}\"")
    if not host:
        initcmd = []
    else:
        parts = host.split(":")
        if len(parts) > 1:
            initcmd = ["ssh", "-t", "-o", "StrictHostKeyChecking=no", "-p", parts[1], parts[0]]
        else:
            initcmd = ["ssh", "-t", "-o", "StrictHostKeyChecking=no", host]
    rcmd = initcmd + shlex.split(cmd)
    log.debug(rcmd)

    try:
        proc = subprocess.Popen(rcmd, cwd=path, stdout=PIPE, stderr=PIPE)
        #term = subprocess.Popen(['xterm'])
    except Exception as e:
        log.info(f"Error running {rcmd}: {e}")
        return
    if interactive:
        # Read both stdout and stderr simultaneously
        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ)
        sel.register(proc.stderr, selectors.EVENT_READ)
        ok = True
        cnt = 0
        lines = ""
        while ok:
            for key, val in sel.select():
                line = key.fileobj.readline()
                if not line and key.fileobj is proc.stdout:
                    ok = False
                    if len(lines):
                        out.append_stdout(lines)
                    break
                cnt += 1
                lines += line.decode('utf-8')
            if out:
                if cnt > 25:
                    out.append_stdout(lines)
                    cnt = 0
                    lines = ""
            else:
                print (lines)
            time.sleep(.01)
            if stop and stop():
                if out and len(lines):
                    out.append_stdout(lines)
                proc.kill()
                return
    
    outs = None
    errs = None
    if stop:
        while not stop():
            time.sleep(1)
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except TimeoutExpired:
            proc.kill()
    else:
        outs, errs = proc.communicate()
        proc.terminate()

    if not ofname:
        return
    try:
        f = open(ofname, 'wb')
        if not outs:
            outs = proc.stdout.read()
        f.write(outs)
        f.close()
    except Exception as e:
        log.error(f"Could not write output for \"{ofname}\": {e}")
        return

def run_job(sess):
    sess.stop = False
    style = {'overflow': 'scroll hidden' ,'white-space': 'nowrap'}
    out = widgets.Output(layout=style)
    display(out)
    out.append_stdout(f"Executing command {sess.cmd}\n")
    sess.thr = threading.Thread(target=run_host_cmd, args=(None, sess.path, sess.cmd, None, lambda: sess.stop, True, out))
    sess.thr.start()
    return sess.thr

def stop_job(sess, th):
    sess.stop = True
    th.join()
    log.info("Stopped job")
