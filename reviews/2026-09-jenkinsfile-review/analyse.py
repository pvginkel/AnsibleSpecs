#!/usr/bin/env python3
"""Per-job Jenkinsfile facts for the review's Appendix A, from the refresh dump and the clones
under /work/scratch. Usage: analyse.py > files.tsv (run after refresh.py and the clones)."""
import os, re, subprocess, sys
import xml.etree.ElementTree as ET

SCR = "/work/scratch"
CFG = os.path.join(SCR, "jenkins-config")


def git_show(repo, branch, path):
    r = subprocess.run(["git", "-C", os.path.join(SCR, repo), "show", f"origin/{branch}:{path}"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


rows = []
for line in open(os.path.join(CFG, "items.tsv")):
    cls, full, _ = line.rstrip("\n").split("\t")
    if not cls.endswith("WorkflowJob"):
        continue
    root = ET.parse(os.path.join(CFG, "xml", full + ".xml")).getroot()
    d = root.find("definition")
    url = d.findtext(".//userRemoteConfigs//url")
    branch = d.findtext(".//branches//name").split("/")[-1]
    script = d.findtext("scriptPath")
    repo = url.rstrip("/").split("/")[-1].removesuffix(".git")
    src = git_show(repo, branch, script)
    if src is None:
        rows.append([full, f"{repo}/{script}@{branch}", "MISSING"])
        continue
    lines = src.split("\n")
    n = len(lines) - (1 if lines and lines[-1] == "" else 0)
    decl = bool(re.search(r"^\s*pipeline\s*\{", src, re.M))
    lib = [i + 1 for i, l in enumerate(lines) if re.match(r"\s*library[\s(]", l)]
    libform = ""
    if lib:
        l = lines[lib[0] - 1].strip()
        libform = "std" if l == "library identifier: 'JenkinsPipelineUtils', changelog: false" else "odd:" + l
    props = [i + 1 for i, l in enumerate(lines) if "properties(" in l and not l.strip().startswith("//")]
    gitclone = [i + 1 for i, l in enumerate(lines) if re.match(r"\s*git\s+(branch|url|credentialsId)", l)]
    imports = [l.strip() for l in lines if l.startswith("import ")]
    feats = []
    for k, pat in [("pins", r"writeVersionPins"), ("helmDeploy", r"helmDeploy"), ("timeout", r"\btimeout\s*\("),
                   ("withVault", r"withVault"), ("githubPush", r"githubPush"), ("cron", r"\bcron\s*\("),
                   ("abortPrevious", r"abortPrevious"), ("kaniko2", r"kaniko2"), ("kaniko(", r"\.kaniko\s*\("),
                   ("aac_tools", r"aac_tools"), ("arch-validate.py", r"arch-validate\.py"),
                   ("toolchain", r"_toolchain\s*\(")]:
        if re.search(pat, src):
            feats.append(k)
    rows.append([full, f"{repo}/{script}@{branch}", str(n), "decl" if decl else "scripted",
                 ",".join(map(str, lib)) + (f" {libform}" if libform else ""),
                 "props@" + ",".join(map(str, props)) if props else "",
                 "git@" + ",".join(map(str, gitclone)) if gitclone else "",
                 "imports:" + ";".join(imports) if imports else "",
                 " ".join(feats)])
for r in rows:
    print("\t".join(r))
