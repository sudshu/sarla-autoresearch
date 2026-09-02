"""Notify the user: email (local sendmail) for breakthroughs.

    notify.py "subject" "body text or - for stdin"

Breakthrough per autoresearch.md: a candidate accepted as the new default
whose dev-set gap G improves on the previous default by >= 0.20, or one that
passes the speed path (<= 0.5x wall-clock at equal quality), or a holdout
confirmation of either. Recipient is fixed in RECIPIENT; nothing else is
ever emailed.
"""
import subprocess
import sys

RECIPIENT = "pandeysu@caltech.edu"
FROM = "SARLA autoresearch <spandey@caltech.edu>"


def send(subject, body):
    msg = (f"From: {FROM}\nTo: {RECIPIENT}\nSubject: {subject}\n"
           f"Content-Type: text/plain; charset=utf-8\n\n{body}\n")
    r = subprocess.run(["/usr/sbin/sendmail", "-t", "-oi"], input=msg.encode(),
                       capture_output=True)
    return r.returncode == 0, r.stderr.decode()


if __name__ == "__main__":
    subj = sys.argv[1]
    body = sys.stdin.read() if sys.argv[2] == "-" else sys.argv[2]
    ok, err = send(subj, body)
    print("sent" if ok else f"FAILED {err}")
