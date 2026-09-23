#!/usr/bin/env python3
"""Re-dump Jenkins job config into a directory: tree.json, items.tsv, xml/, plugins.txt,
jobs-ui-config.md, repos.txt. Usage: refresh.py <outdir>. Needs JENKINS_TOKEN (admin)."""
import base64, datetime, json, os, sys, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

BASE = "https://jenkins.webathome.org"
AUTH = "Basic " + base64.b64encode(f"admin:{os.environ['JENKINS_TOKEN']}".encode()).decode()
out = sys.argv[1]


def get(url):
    req = urllib.request.Request(url, headers={"Authorization": AUTH})
    with urllib.request.urlopen(req) as r:
        return r.read()


def job_url(full):
    return BASE + "".join("/job/" + urllib.parse.quote(p) for p in full.split("/")) + "/"


leaf = "_class,fullName,url"
tree = leaf
for _ in range(5):
    tree = f"{leaf},jobs[{tree}]"
raw = get(f"{BASE}/api/json?tree=jobs[{tree}]")
os.makedirs(os.path.join(out, "xml"), exist_ok=True)
open(os.path.join(out, "tree.json"), "wb").write(raw)

items = []
def walk(jobs):
    for j in jobs:
        items.append(j)
        walk(j.get("jobs") or [])
walk(json.loads(raw)["jobs"])
items.sort(key=lambda j: j["fullName"].lower())
with open(os.path.join(out, "items.tsv"), "w") as f:
    for j in items:
        f.write(f"{j['_class']}\t{j['fullName']}\t{j['url']}\n")

plugins = json.loads(get(f"{BASE}/pluginManager/api/json?tree=plugins[shortName,version]"))
with open(os.path.join(out, "plugins.txt"), "w") as f:
    for p in sorted(plugins["plugins"], key=lambda p: p["shortName"]):
        f.write(f"{p['shortName']} {p['version']}\n")


def txt(el, path, default=None):
    x = el.find(path)
    return x.text if x is not None and x.text is not None else default


md = [f"# Jenkins UI-side job configuration (dumped from config.xml, {datetime.date.today()})", "",
      "Every job is `CpsScmFlowDefinition` (pipeline script from SCM). Columns: repo, branch spec, "
      "script path, lightweight checkout, then every UI-side property/trigger with its settings.", ""]
repos = set()
for j in items:
    x = get(job_url(j["fullName"]) + "config.xml")
    path = os.path.join(out, "xml", j["fullName"] + ".xml")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(x)
    if not j["_class"].endswith("WorkflowJob"):
        continue
    root = ET.fromstring(x)
    lines = []
    if txt(root, "disabled") == "true":
        lines.append("- **DISABLED**")
    d = root.find("definition")
    cls = d.get("class", "").split(".")[-1] if d is not None else "none"
    if cls == "CpsScmFlowDefinition":
        url = txt(d, ".//userRemoteConfigs//url")
        repos.add(url)
        branch = txt(d, ".//branches//name")
        lines.append(f"- SCM: {url} @ {branch} → `{txt(d, 'scriptPath')}` "
                     f"(lightweight={txt(d, 'lightweight')})")
    else:
        lines.append(f"- definition: {cls}")
    for p in list(root.find("properties")):
        tag = p.tag.split(".")[-1]
        if tag == "DisableConcurrentBuildsJobProperty":
            lines.append(f"- disableConcurrentBuilds (abortPrevious={txt(p, 'abortPrevious', 'false')})")
        elif tag == "BuildDiscarderProperty":
            s = p.find("strategy")
            lines.append("- buildDiscarder: " + ", ".join(f"{c.tag}={c.text}" for c in s))
        elif tag == "CopyArtifactPermissionProperty":
            lines.append(f"- copyArtifactPermission: {txt(p, 'projectNameList/string')}")
        elif tag == "ParametersDefinitionProperty":
            for pd in p.find("parameterDefinitions"):
                desc = txt(pd, "description")
                s = f"- parameter {pd.tag.split('.')[-1]} `{txt(pd, 'name')}` default={txt(pd, 'defaultValue')!r}"
                s = s.replace("default='None'", "default=None").replace("default=None", "default=None")
                if desc:
                    s += f" desc={desc[:120]!r}"
                lines.append(s)
        elif tag == "PipelineTriggersJobProperty":
            for t in list(p.find("triggers")):
                tt = t.tag.split(".")[-1]
                if tt == "GitHubPushTrigger":
                    lines.append("- trigger: GitHub push (githubPush)")
                elif tt == "TimerTrigger":
                    lines.append(f"- trigger cron: `{txt(t, 'spec')}`")
                elif tt == "ReverseBuildTrigger":
                    lines.append(f"- trigger upstream: projects={txt(t, 'upstreamProjects')} "
                                 f"threshold={txt(t, 'threshold/name')}")
                else:
                    lines.append(f"- trigger {tt}")
        else:
            lines.append(f"- property {tag}")
    md += [f"## {j['fullName']}", ""] + lines + [""]
open(os.path.join(out, "jobs-ui-config.md"), "w").write("\n".join(md))
open(os.path.join(out, "repos.txt"), "w").write("".join(f"{r}\n" for r in sorted(repos, key=str.lower)))
print(f"{len(items)} items, {len(repos)} repos")
