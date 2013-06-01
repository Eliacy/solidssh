# Solidssh: manage solid ssh tunnel for you #

Solidssh is a Python clone of autossh, basing on pexpect. It create 'ssh -D' tunnel, and try the best to make sure the validity of this tunnel. It carefully monitor the tunnel, and recreate when it died.

If what you want is GUI of ssh tunnel management, I suggest the following implementations:

* [Bitvise SSH Client](http://www.bitvise.com/ssh-client) for Windows;
* [GoAgentX](https://github.com/ohdarling/GoAgentX/wiki) for Mac OS X;

# Installation #

Solidssh depends on pexpect and socks.py. For convenience, solidssh include latest version of pexpect.py and socks.py with its source.

1. Download solidssh package from [zip package of latest solidssh](https://github.com/Eliacy/solidssh/archive/master.zip) .
2. Unzip solidssh.zip, and solidssh.py is ready to use.

If you want to fetch the whole source code repo, please use git:

    git clone https://github.com/Eliacy/solidssh.git

# Usage #

    solidssh.py %HOST% %LOCAL_PORT% [%PASSWORD%] [nomonitor]

E.g,

    solidssh.py ssh_username@vps.somehost.com 18080 some_password

will create an ssh -D tunnel through 'vps.somehost.com', with ssh account 'ssh_username:some_password', and the local port of this tunnel will be 18080. In addition, this tunnel can be used as a socks5 proxy, you can set up this socks5 proxy in browser.

If you think your network status is stable enough, you can disable the tunnel monitoring feature of solidssh. E.g, 

    solidssh.py ssh_username@vps.somehost.com 18080 some_password nomonitor

# Known issues #

1. In rare possibility, pexpect can not kill ssh sub-process properly. You may find redundant ssh tunnel process even if the tunnel of it already dead. The good news is, such redundant ssh processes will be closed automatically when solidssh exit.
2. In rare possibility, you may get things like 'Warning: remote port forwarding failed for listen port 18081'. Because sometimes ssh process for tunnel monitoring is killed, but ssh server have no hurry release the server port of ssh tunnel. I don't know how to fix this. I simply open another port for use, and wait the original port get released naturally.

# 简介 #

solidssh 是 autossh 的一个复制品，用 Python 语言编写的，其实现原理是利用 pexpect 类库调用系统中原生的 ssh 命令行程序。solidssh 能创建并监控 'ssh -D' 隧道的状态，在隧道失效时自动重启它，从而得到一个更为健壮、具有更高可用性的隧道代理。

solidssh 是命令行应用，如果您需要的是图形化的 ssh 隧道管理客户端，建议使用以下两个：

* [Bitvise SSH Client](http://www.bitvise.com/ssh-client) for Windows;
* [GoAgentX](https://github.com/ohdarling/GoAgentX/wiki) for Mac OS X;

# 安装 #

solidssh 依赖 pexpect 和 socks.py 。为了使用方便，solidssh 的压缩包中已经包含了 pexpect.py 和 socks.py 的最新版本。具体可按以下步骤完成安装：

1. 点 [这里](https://github.com/Eliacy/solidssh/archive/master.zip) 下载最新版本代码压缩包。
2. 解压 solidssh.zip 即可。

如果希望获得完整的代码版本历史记录用于修改，执行以下指令：

    git clone https://github.com/Eliacy/solidssh.git

# 使用说明 #

    solidssh.py %HOST% %LOCAL_PORT% [%PASSWORD%] [nomonitor]

例如，

    solidssh.py ssh_username@vps.somehost.com 18080 some_password

意思是让 solidssh 使用用户名 ssh_username 、密码 some_password 连接 ssh 服务器 vps.somehost.com ，建立的隧道在本机的端口是 18080 。由于 'ssh -D' 指令建立的隧道具有 socks5 代理的功能，因此可以在浏览器设置中，把 18080 端口当作 socks5 代理的设置参数。

有时候，网络环境可能很稳定，ssh 隧道不容易断线，那么可以让 solidssh 只负责自动输入用户名密码建立隧道，而不用额外建立测试主隧道状态的监控用隧道。那么可以这样调整指令参数：

    solidssh.py ssh_username@vps.somehost.com 18080 some_password nomonitor

