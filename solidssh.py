#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""ssh 隧道的自动登陆程序。
* 基于 pan.shizhu@gmail.com 的 Python 脚本略有修改。
* 修改者： elias.soong@gmail.com
"""

import pexpect
import time
import sys
import threading

SSH_PARAMS = "-N -C -D %s %s"     # local_port, host
TUNNEL_START = threading.Event()
TUNNEL_CREATED = threading.Event()
TUNNEL_DEAD = threading.Event()
MONITOR_EXIT = threading.Event()
TUNNEL_EXIT = threading.Event()
EVENTS = (TUNNEL_START, TUNNEL_CREATED, TUNNEL_DEAD, MONITOR_EXIT, TUNNEL_EXIT)

def ssh_tunnel(events, ssh_params_template, host, local_port, password=None):
    """自动管理 ssh 隧道的连接状态，断线时自动重连。

    参数说明：
    * events: 全局事件容器
    * ssh_params_template: ssh 连接参数模板
    * host: ssh 服务器连接地址，例如 username@hostname:port
    * local_port: ssh 隧道的本地端口
    * passowrd: ssh 服务器上的帐号，对应的用户名在 host 参数中指明
    """
    tunnel_start, tunnel_created, tunnel_dead, monitor_exit, tunnel_exit = events
    fails = 0
    while True:
        if tunnel_exit.isSet():
            break
        tunnel_start.wait()
        tunnel_start.clear()
        tunnel_dead.clear()
        try:
            print "== creating ssh tunnel =="
            ssh_params = ssh_params_template if fails != 1 else "-v " + ssh_params_template
            child = pexpect.spawn("ssh " + ssh_params % (local_port, host), timeout=5)
            child.logfile_read = sys.stdout
            if password != None:
                child.expect('password:')
                time.sleep(0.5)
                child.sendline(password)
                time.sleep(0.5)
                print '\ntunnel ready'
            child.setecho(True)
            fails = 0     # 登陆成功
            tunnel_created.set()
            
            while True:
                index = child.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=1)        
                if index == 1 and child.isalive() and not tunnel_dead.isSet():
                    continue
                else:
                    break
            
            tunnel_dead.set()
            child.close(force=True)
            print "## detect ssh tunnel dead ##"

        except Exception, e:
            tunnel_dead.set()
            if fails <= 1:
                print str(e)
                print
            fails += 1
            if fails > 1:
                time.sleep(3)

def start_tunnel(events, ssh_params_template, host, local_port, password=None):
    """管理 ssh 隧道的主线程，负责隧道断线重连和状态监控。

    参数说明：
    * events: 全局事件容器
    * ssh_params_template: ssh 连接参数模板
    * host: ssh 服务器连接地址，例如 username@hostname:port
    * local_port: ssh 隧道的本地端口
    * passowrd: ssh 服务器上的帐号，对应的用户名在 host 参数中指明
    """
    tunnel_start, tunnel_created, tunnel_dead, monitor_exit, tunnel_exit = events
    tunnel_thread = threading.Thread(target = ssh_tunnel, args = (events, ssh_params_template, host, local_port, password))
    tunnel_thread.start()
    tunnel_start.set()
    try:
        while True:
            time.sleep(3)
    except KeyboardInterrupt:
        tunnel_start.clear()
        tunnel_dead.set()
        tunnel_exit.set()
        tunnel_thread.join()
        print "## solidssh exited ##"

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print """This script create an ssh tunnel and auto reconnect it when any error occur.
    Usage: solidssh.py %HOST% %LOCAL_PORT% [%PASSWORD%]
    Example: solidssh.py my_username@my_hostname:port 18080 my_password
         """
    else:
        print "== starting solidssh.py =="
        argv = sys.argv[1:] + [None]
        host, local_port, password = argv[0:3]
        start_tunnel(EVENTS, SSH_PARAMS, host, local_port, password)

