#!/usr/bin/env python3
import hashlib, json, os, pathlib, platform, subprocess, sys, urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path.cwd().resolve()
H = pathlib.Path(__file__).resolve().parent
R = H / "reports"; S = H / ".state"
R.mkdir(parents=True, exist_ok=True); S.mkdir(parents=True, exist_ok=True)
REPORT = {"started_at": datetime.now(timezone.utc).isoformat(), "repo_root": str(ROOT), "checks": [], "status": "IN_PROGRESS"}

def add(n, s, d):
    REPORT["checks"].append({"name": n, "status": s, "detail": str(d)})
    print(f"[{s}] {n}: {d}")

def cmd(argv, cwd=ROOT, timeout=900, allow_fail=False):
    try:
        p = subprocess.run(argv, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        if p.returncode and not allow_fail: add("command " + " ".join(argv), "FAIL", p.stdout[-1200:])
        return p.returncode, p.stdout
    except Exception as e: return 1, f"{type(e).__name__}: {e}"

def git(*args): return cmd(["git", *args], timeout=30, allow_fail=True)
def git_status():
    rc, out = git("status", "--porcelain=v1")
    return out.strip() if rc == 0 else "Git unavailable"

def inventory():
    rc, out = git("ls-files", "-z")
    tracked = out.split("\0") if rc == 0 else []
    keywords = ("model", "cox", "survival", "calibrat", "artifact", "feature_manifest")
    hashes = {}
    for rel in tracked:
        if not rel: continue
        p = ROOT / rel
        if p.is_file() and any(k in rel.lower() for k in keywords):
            try:
                h = hashlib.sha256()
                with p.open("rb") as f:
                    for b in iter(lambda: f.read(1024*1024), b""): h.update(b)
                hashes[rel] = h.hexdigest()
            except OSError: hashes[rel] = "UNREADABLE"
    (S / "ml_hashes.json").write_text(json.dumps(hashes, indent=2))
    app_pkgs = list(ROOT.glob("apps/*/package.json")) + list(ROOT.glob("*/apps/*/package.json"))
    compose_files = list(ROOT.glob("*compose*.y*ml")) + list(ROOT.glob("*/*compose*.y*ml"))
    inv = {
        "package_json": (ROOT/"package.json").exists(),
        "app_package_json": [str(p.relative_to(ROOT)) for p in app_pkgs if "node_modules" not in str(p)],
        "requirements": [str(p.relative_to(ROOT)) for p in ROOT.rglob("requirements*.txt") if ".venv" not in str(p) and "node_modules" not in str(p)],
        "dockerfiles": [str(p.relative_to(ROOT)) for p in ROOT.rglob("Dockerfile") if ".venv" not in str(p) and "node_modules" not in str(p)],
        "compose": [str(p.relative_to(ROOT)) for p in compose_files],
        "env_examples": [str(p.relative_to(ROOT)) for p in ROOT.rglob(".env.example") if ".venv" not in str(p) and "node_modules" not in str(p)]
    }
    (R/"repository_inventory.json").write_text(json.dumps(inv, indent=2))
    add("ML artifact hash baseline", "PASS" if hashes else "WARN", f"{len(hashes)} tracked candidate files hashed; contents not printed")
    add("repository inventory", "PASS", json.dumps(inv))
    return hashes, inv

def check_hashes():
    baseline = json.loads((S/"ml_hashes.json").read_text()) if (S/"ml_hashes.json").exists() else {}
    current = {}
    rc, out = git("ls-files", "-z")
    for rel in (out.split("\0") if rc == 0 else []):
        if not rel: continue
        p = ROOT / rel
        if p.is_file() and any(k in rel.lower() for k in ("model","cox","survival","calibrat","artifact","feature_manifest")):
            try: current[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
            except OSError: current[rel] = "UNREADABLE"
    changes = [p for p in set(baseline)|set(current) if baseline.get(p) != current.get(p)]
    add("ML artifact integrity", "FAIL" if changes else "PASS", "Changed: "+", ".join(sorted(changes)) if changes else f"{len(current)} candidate hashes unchanged")

def load_env():
    p = H/".env.harness"
    if p.exists():
        for line in p.read_text(errors="replace").splitlines():
            line=line.strip()
            if line and not line.startswith("#") and "=" in line:
                k,v=line.split("=",1); os.environ.setdefault(k.strip(),v.strip().strip("'").strip('"'))

def preflight():
    add("repository root", "PASS", ROOT)
    rc, branch = git("branch","--show-current")
    add("Git", "PASS" if rc==0 else "WARN", branch.strip() if rc==0 else branch)
    dirty=git_status(); add("working tree", "WARN" if dirty else "PASS", "Existing changes preserved" if dirty else "clean")
    add("runtime", "INFO", f"Python {platform.python_version()} / {platform.platform()}")
    inventory()
    for x in ("git","python3","node","npm","pnpm","yarn","docker","curl"):
        rc,out=cmd(["bash","-lc",f"command -v {x}"],timeout=10,allow_fail=True)
        add("tool "+x,"PASS" if rc==0 else "INFO",out.strip() or "not installed")

def agent():
    adapter=pathlib.Path(os.environ.get("ANTIGRAVITY_ADAPTER",str(H/"adapters/antigravity_adapter.sh")))
    if not adapter.is_absolute(): adapter=ROOT/adapter
    if not adapter.exists(): add("Antigravity adapter","FAIL",f"Missing {adapter}"); return
    try:
        with (H/"agent_task.md").open("rb") as f:
            p=subprocess.run(["bash",str(adapter)],cwd=ROOT,stdin=f,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=int(os.environ.get("AGENT_TIMEOUT_SECONDS","7200")))
        log=R/"antigravity_agent.log"; log.write_bytes(p.stdout)
        add("Antigravity agent", "PASS" if p.returncode==0 else "FAIL", f"exit={p.returncode}; log={log}")
    except Exception as e: add("Antigravity agent","FAIL",e)
    check_hashes()

def validate():
    inv=json.loads((R/"repository_inventory.json").read_text()) if (R/"repository_inventory.json").exists() else inventory()[1]
    run_build=os.environ.get("RUN_FRONTEND_BUILD","auto")
    roots=[]
    if inv["package_json"]: roots.append(ROOT)
    roots += [ROOT/pathlib.Path(x).parent for x in inv["app_package_json"]]
    for d in sorted(set(roots)):
        try: pkg=json.loads((d/"package.json").read_text()); scripts=pkg.get("scripts",{})
        except Exception as e: add("frontend manifest","FAIL",e); continue
        if run_build=="0": add("frontend build","SKIP","Disabled"); continue
        if "build" not in scripts:
            add("frontend build","FAIL" if run_build=="1" else "SKIP","No build script"); continue
        if (d/"pnpm-lock.yaml").exists() or (ROOT/"pnpm-lock.yaml").exists(): argv=["pnpm","run","build"]
        elif (d/"yarn.lock").exists() or (ROOT/"yarn.lock").exists(): argv=["yarn","build"]
        else: argv=["npm","run","build"]
        rc,out=cmd(argv,cwd=d,timeout=1800,allow_fail=True)
        add("frontend build "+str(d.relative_to(ROOT) or "."),"PASS" if rc==0 else "FAIL",out[-1400:])
    test=os.environ.get("BACKEND_TEST_CMD","").strip()
    if test:
        rc,out=cmd(["bash","-lc",test],timeout=3600,allow_fail=True); add("backend tests","PASS" if rc==0 else "FAIL",out[-1800:])
    elif os.environ.get("RUN_BACKEND_TESTS","auto")=="1":
        path=ROOT/"apps/api"
        rc,out=cmd(["python3","-m","pytest","-q"],cwd=path if path.exists() else ROOT,timeout=3600,allow_fail=True)
        add("backend tests","PASS" if rc==0 else "FAIL",out[-1800:])
    else: add("backend tests","SKIP","Set BACKEND_TEST_CMD after confirming repo test command, or RUN_BACKEND_TESTS=1")
    check_hashes()

def deploy():
    if os.environ.get("ALLOW_INFRA_CHANGES","0")!="1":
        add("deployment gate","BLOCKED","Set ALLOW_INFRA_CHANGES=1 only after reviewing commands, costs, and provider account.")
        return
    configured=[("frontend",os.environ.get("DEPLOY_FRONTEND_CMD","")),("backend",os.environ.get("DEPLOY_BACKEND_CMD","")),("workers",os.environ.get("DEPLOY_WORKERS_CMD",""))]
    if not any(x.strip() for _,x in configured):
        add("deployment commands","BLOCKED","No provider commands configured; have agent prepare provider config and set exact commands.")
        return
    for name,command in configured:
        if not command.strip(): add(name+" deploy","SKIP","No command configured"); continue
        rc,out=cmd(["bash","-lc",command],timeout=3600,allow_fail=True)
        add(name+" deploy","PASS" if rc==0 else "FAIL",out[-1800:])

def smoke():
    pairs=[("frontend",os.environ.get("FRONTEND_URL","").strip()),
           ("backend health",os.environ.get("BACKEND_URL","").rstrip("/") + os.environ.get("HEALTH_PATH","/health") if os.environ.get("BACKEND_URL","").strip() else "")]
    for name,url in pairs:
        if not url: add(name+" smoke","SKIP","URL not configured"); continue
        if not url.startswith("https://"): add(name+" HTTPS","WARN","URL is not HTTPS")
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"BHUMISETU-deployment-harness/1.0"})
            with urllib.request.urlopen(req,timeout=20) as r: add(name+" smoke","PASS" if r.status<400 else "FAIL",f"HTTP {r.status} {url}")
        except Exception as e: add(name+" smoke","FAIL",f"{url}: {type(e).__name__}: {e}")

def finish():
    bad=any(x["status"] in ("FAIL","BLOCKED") for x in REPORT["checks"])
    warn=any(x["status"] in ("WARN","INFO","SKIP") for x in REPORT["checks"])
    REPORT["finished_at"]=datetime.now(timezone.utc).isoformat()
    REPORT["status"]="FAIL_OR_BLOCKED" if bad else ("PASS_WITH_WARNINGS" if warn else "PASS")
    (R/"deployment_harness_report.json").write_text(json.dumps(REPORT,indent=2)+"\\n")
    lines=["# BHUMISETU Deployment Harness Report","",f"Status: **{REPORT['status']}**","",f"Repository: `{ROOT}`","","## Checks",""]
    lines += [f"- **{c['status']} — {c['name']}**: {c['detail']}" for c in REPORT["checks"]]
    lines += ["","Only checks actually executed are reported. A successful build does not by itself prove a production deployment.",""]
    (R/"deployment_harness_report.md").write_text("\\n".join(lines))
    print("Report:",R/"deployment_harness_report.md")

def main():
    load_env(); action=sys.argv[1] if len(sys.argv)>1 else "preflight"
    actions={"preflight":preflight,"agent":agent,"validate":validate,"deploy":deploy,"smoke":smoke,
             "all-safe":lambda:(preflight(),agent(),validate(),smoke()),
             "report":lambda:print(R/"deployment_harness_report.md" if (R/"deployment_harness_report.md").exists() else "No report yet")}
    if action not in actions:
        print("Usage: run.sh {preflight|agent|validate|deploy|smoke|all-safe|report}"); sys.exit(2)
    try: actions[action]()
    finally: finish()
    if any(c["status"] in ("FAIL","BLOCKED") for c in REPORT["checks"]): sys.exit(1)
if __name__=="__main__": main()
