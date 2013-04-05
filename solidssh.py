#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""ssh 隧道的自动登陆程序。
* 基于 pan.shizhu@gmail.com 的 Python 脚本略有修改。
* 修改者： elias.soong@gmail.com
"""

import pexpect
import time
import sys

def ssh_tunnel(host, local_port, password=None):
    """自动管理 ssh 隧道的连接状态，断线时自动重连。

    参数说明：
    * host: ssh 服务器连接地址，例如 username@hostname:port
    * local_port: ssh 隧道的本地端口
    * passowrd: ssh 服务器上的帐号，对应的用户名在 host 参数中指明
    """
    while True:
       try:
           print "creating ssh tunnel"
           child = pexpect.spawn("ssh -v -N -g -C -D %s %s" % (local_port, host), timeout=5)
           child.logfile_read = sys.stdout
           if password != None:
               child.expect('password:')
               time.sleep(0.5)
               child.sendline(password)
               time.sleep(0.5)
               print '\ntunnel ready'
           child.setecho(True)
           
           try:
               while True:
                   index = child.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=5)        
                   if index == 1 and child.isalive():
                       continue
                   else:
                       break
           except KeyboardInterrupt:
               child.close(force=True)
               break
           
           child.close(force=True)
           print "detect ssh tunnel dead"

       except Exception, e:
           print str(e)
    
    print "autossh.py exited"

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print """This script create an ssh tunnel and auto reconnect it when any error occur.
    Usage: autossh.py %HOST% %LOCAL_PORT% [%PASSWORD%]
    Example: autossh.py my_username@my_hostname:port 18080 my_password
         """
    else:
        print "starting autossh.py"
        argv = sys.argv[1:] + [None]
        host, local_port, password = argv[0:3]
        ssh_tunnel(host, local_port, password)

