"""Retain the raw audit and fail for any finding outside reviewed applicability scope."""
import argparse
from datetime import date
import json
from pathlib import Path
import subprocess
import sys

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('data/dependency-audit.json'))
    args=parser.parse_args()
    process=subprocess.run([sys.executable,'-m','pip_audit','--format','json'],capture_output=True,text=True)
    if process.returncode not in {0,1}:
        print('Dependency advisory service failed; no clean audit is claimed.',file=sys.stderr)
        return 2
    try:
        report=json.loads(process.stdout)
    except ValueError:
        print('Audit did not return usable JSON.',file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    exception=json.loads(Path('security/advisory-exceptions.json').read_text(encoding='utf-8'))
    exceptions_current=date.today()<=date.fromisoformat(exception['review_before'])
    unreviewed=set(); reviewed=set()
    for dependency in report['dependencies']:
        for vulnerability in dependency.get('vulns',[]):
            finding=(dependency['name'],dependency['version'],vulnerability['id'])
            allowed=exceptions_current and dependency['name']==exception['package'] and dependency['version']==exception['version'] and vulnerability['id'] in exception['ids']
            (reviewed if allowed else unreviewed).add(finding)
    print(json.dumps({'unreviewed_findings':sorted(unreviewed),'reviewed_embedded_only_findings':sorted(reviewed),'raw_report':str(args.output),'exception_review_before':exception['review_before']}))
    return 1 if unreviewed else 0

if __name__=='__main__':
    raise SystemExit(main())
