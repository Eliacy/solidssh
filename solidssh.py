#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""ssh 隧道的自动登陆程序，能自动建立额外的心跳信号隧道监控网络状态，适应系统休眠等更多网络场景。
* 基于 pan.shizhu@gmail.com 的 Python 脚本修改。
* 修改者： elias.soong@gmail.com
"""

import time
import socket, SocketServer
import sys
import threading

import pexpect
import socks

SSH_PARAMS = "-N -C -D %s %s"     # local_port, host
REVERSE_SSH_PARMAS = "-g -N -R %s:127.0.0.1:%s %s"       # remote_port, local_port, host
TUNNEL_START = threading.Event()
TUNNEL_CREATED = threading.Event()
TUNNEL_MONITORED = threading.Event()
TUNNEL_DEAD = threading.Event()
TUNNEL_EXIT = threading.Event()
TUNNEL_ALIVE = threading.Event()
EVENTS = (TUNNEL_START, TUNNEL_CREATED, TUNNEL_MONITORED, TUNNEL_DEAD, TUNNEL_EXIT, TUNNEL_ALIVE)

def _connect_ssh(ssh_str, password=None):
    """调用 ssh 指令建立隧道的封装函数。

    参数说明：
    * ssh_str: 拼接好的完整 ssh 指令（含配置参数）

    返回值：
    * child: pexpect.spawn 函数的对应返回值，也即启动的 ssh 进程的命令行界面操控句柄
    """
    child = pexpect.spawn(ssh_str, timeout=3)
    child.logfile_read = sys.stdout
    if password != None:
        child.expect('password:', timeout=8)
        time.sleep(0.5)
        child.sendline(password)
        time.sleep(0.5)
    child.setecho(True)
    return child

def ssh_tunnel(events, ssh_params_template, host, local_port, password=None):
    """自动管理 ssh 隧道的连接状态，断线时自动重连。

    参数说明：
    * events: 全局事件容器
    * ssh_params_template: ssh 连接参数模板
    * host: ssh 服务器连接地址，例如 username@hostname:port
    * local_port: ssh 隧道的本地端口
    * passowrd: ssh 服务器上的帐号，对应的用户名在 host 参数中指明
    """
    tunnel_start, tunnel_created, tunnel_monitored, tunnel_dead, tunnel_exit, tunnel_alive = events

    fails = 0
    child = None
    while True:
        if tunnel_exit.isSet():
            break
        tunnel_start.wait()
        try:
            print "== creating ssh tunnel =="
            ssh_params = ssh_params_template if fails != 1 else "-v " + ssh_params_template
            ssh_str = "ssh " + ssh_params % (local_port, host)
            child = _connect_ssh(ssh_str, password)
            fails = 0     # 登陆成功
            tunnel_created.set()
            print '\ntunnel ready\n',
            while True:
                index = child.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=1)        
                if index == 1 and child.isalive():
                    pass
                else:
                    tunnel_dead.set()
                if tunnel_dead.isSet() or tunnel_exit.isSet():
                    break
            print "## detect ssh tunnel dead ##"
        except Exception, e:
            tunnel_dead.set()
            if fails <= 1:
                print 'tunnel:', str(e)
                print
            fails += 1
            if fails > 1:
                time.sleep(3)
        finally:
            if child != None:
                while child.isalive():  # 确保 ssh 进程确实退出了，测试发现有小概率仅通过 close() 函数无法正常关闭。
                    child.close(force=True)
                    time.sleep(1)

def monitor_tunnel(events, ssh_params_template, host, local_port, remote_port, password=None):
    """管理监控用 ssh 隧道的连接状态，断线时发出报警事件。

    参数说明：
    * events: 全局事件容器
    * ssh_params_template: ssh 连接参数模板
    * host: ssh 服务器连接地址，例如 username@hostname:port
    * local_port: ssh 隧道的本地端口
    * remote_port: ssh 隧道的远程端口
    * passowrd: ssh 服务器上的帐号，对应的用户名在 host 参数中指明
    """
    tunnel_start, tunnel_created, tunnel_monitored, tunnel_dead, tunnel_exit, tunnel_alive = events

    fails = 0
    child = None
    while True:
        if tunnel_exit.isSet():
            break
        tunnel_created.wait()
        try:
            print "== creating monitor tunnel =="
            ssh_params = ssh_params_template if fails != 1 else "-v " + ssh_params_template
            ssh_str = "ssh " + ssh_params % (remote_port, local_port, host)
            child = _connect_ssh(ssh_str, password)
            fails = 0     # 登陆成功
            tunnel_monitored.set()
            print '\nmonitor ready'
            while True:
                index = child.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=1)        
                if index == 1 and child.isalive():
                    pass
                else:
                    tunnel_dead.set()
                if tunnel_dead.isSet() or tunnel_exit.isSet():
                    break
            print "## detect monitor tunnel dead ##"
        except Exception, e:
            if fails >= 2:      # 也即第三次重试，仍然连接失败：
                tunnel_dead.set()
            if fails <= 1:
                print 'monitor:', str(e)
                print
            fails += 1
            if fails > 1 and not tunnel_dead.isSet():
                time.sleep(3)
        finally:
            if child != None:
                while child.isalive():  # 确保 ssh 进程确实退出了，测试发现有小概率仅通过 close() 函数无法正常关闭。
                    child.close(force=True)
                    time.sleep(1)
        if tunnel_dead.isSet():
            time.sleep(3)

def control_events(events):
    """管理事件状态变迁的线程。

    参数说明：
    * events: 全局事件容器
    """
    tunnel_start, tunnel_created, tunnel_monitored, tunnel_dead, tunnel_exit, tunnel_alive = events

    while True:
        tunnel_created.wait()
        tunnel_dead.clear()

        tunnel_dead.wait()
        tunnel_created.clear()
        tunnel_monitored.clear()

class MyTCPHandler(SocketServer.StreamRequestHandler):
    """用于接收监控隧道心跳服务的处理器。
    """

    def handle(self):
        """继承自 StreamRequestHandler 的网络请求处理函数。
        """
        try:
            self.data = self.rfile.readline().strip()
            if time.time() - float(self.data) <= 60:
                self.server.event_alive.set()
        except Exception, e:
            print 'handler:', str(e)
            pass

def monitor_server(events, monitor_port):
    """用于测试隧道状态的服务端。

    参数说明：
    * events: 全局事件容器
    * monitor_port: 用于监听的端口
    """
    tunnel_start, tunnel_created, tunnel_monitored, tunnel_dead, tunnel_exit, tunnel_alive = events

    SocketServer.ThreadingTCPServer.allow_reuse_address = True
    server = SocketServer.ThreadingTCPServer(("127.0.0.1", monitor_port), MyTCPHandler)
    server.event_alive = tunnel_alive
    socket_server_thread = threading.Thread(target=server.serve_forever)
    socket_server_thread.daemon = False
    socket_server_thread.start()

    tunnel_exit.wait()
    server.shutdown()

def monitor_client(events, proxy_port, remote_port):
    """用于测试隧道状态的客户端，在隧道就位的状态下，每3秒发出一个心跳请求（但容忍更长网络超时）。

    参数说明：
    * events: 全局事件容器
    * proxy_port: 本地 socks 代理的端口
    * remote_port: 隧道端用于监听的端口
    """
    tunnel_start, tunnel_created, tunnel_monitored, tunnel_dead, tunnel_exit, tunnel_alive = events

    socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", proxy_port)
    socket.socket = socks.socksocket

    previous_success = None
    while True:
        if tunnel_monitored.isSet():
            if previous_success == None:
                previous_success = time.time()

            try:
                sent_time = time.time()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(30.0)
                sock.connect(("127.0.0.1", remote_port))
                sock.sendall(str(time.time()) + "\n")
            except Exception, e:
                print 'client:', str(e)
            finally:
                sock.close()
            time_diff = 3 + sent_time - time.time()
            time.sleep(time_diff if time_diff > 0 else 0)

            if tunnel_alive.isSet():
                tunnel_alive.clear()
                previous_success = time.time()
            if time.time() - previous_success > 65:
                tunnel_dead.set()
            if tunnel_dead.isSet():
                previous_success = None
                time.sleep(3)
        else:
            time.sleep(3)

def start_tunnel(events, host, local_port, password=None, monitor_flag=True):
    """管理 ssh 隧道的主线程，负责隧道断线重连和状态监控。

    参数说明：
    * events: 全局事件容器
    * host: ssh 服务器连接地址，例如 username@hostname:port
    * local_port: ssh 隧道的本地端口
    * passowrd: ssh 服务器上的帐号，对应的用户名在 host 参数中指明
    * monitor_flag: 是否监控隧道状态
    """
    tunnel_start, tunnel_created, tunnel_monitored, tunnel_dead, tunnel_exit, tunnel_alive = events
    remote_port = str(int(local_port) + 1)

    control_thread = threading.Thread(target = control_events, args = (events,))
    control_thread.daemon = True
    control_thread.start()

    tunnel_thread = threading.Thread(target = ssh_tunnel, args = (events, SSH_PARAMS, host, local_port, password))
    tunnel_thread.daemon = False
    tunnel_thread.start()
    tunnel_start.set()

    if monitor_flag:
        monitor_thread = threading.Thread(target = monitor_tunnel, args = (events, REVERSE_SSH_PARMAS, host, remote_port, remote_port, password))
        monitor_thread.daemon = True        # 因为存在对事件的 wait() 死锁。
        monitor_thread.start()

        server_thread = threading.Thread(target = monitor_server, args = (events, int(remote_port)))
        server_thread.daemon = False
        server_thread.start()

        client_thread = threading.Thread(target = monitor_client, args = (events, int(local_port), int(remote_port)))
        client_thread.daemon = True         # 没有需要特别进行释放的资源。
        client_thread.start()

    try:
        while True:
            time.sleep(3)
    except KeyboardInterrupt:
        tunnel_exit.set()
        tunnel_start.clear()
        tunnel_dead.set()
        if monitor_flag and tunnel_created.isSet():
            monitor_thread.join()
        tunnel_thread.join()
        print "## solidssh exited ##"

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print """This script create an ssh tunnel and auto reconnect it when any error occur.
    Usage: solidssh.py %HOST% %LOCAL_PORT% [%PASSWORD%] [nomonitor]
    Example: solidssh.py my_username@my_hostname:port 18080 my_password nomonitor
         """
    else:
        print "== starting solidssh.py =="
        argv = sys.argv[1:]
        if argv[-1] == 'nomonitor':
            monitor_flag = False
            argv.pop(-1)
        else:
            monitor_flag = True
        argv = argv + [None]
        host, local_port, password = argv[0:3]
        start_tunnel(EVENTS, host, local_port, password, monitor_flag)

