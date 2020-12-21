#!/usr/local/bin/python3 -u

import argparse
import multiprocessing
import jwt
from time import sleep,time
from threading import Thread
from kubernetes import client, config, watch
from mysocketctl.socket import get_sockets, new_socket
from mysocketctl.tunnel import new_tunnel
from mysocketctl.login import get_token
from mysocketctl.ssh import SystemSSH, Paramiko
import logging

def create_socket(svc, token):
  authorization_header, token = get_auth_header(token)
  sockets = get_sockets(authorization_header)
  name = 'k8s {}.{}'.format(svc.metadata.namespace, svc.metadata.name)

  for s in sockets:
    if s['name'] == name:
      logging.debug('existing socket found with id: {}'.format(s['socket_id']))
      return s, token

  s = new_socket(authorization_header, name, False , '', '', 'http')
  logging.debug('new socket created with id: {}'.format(s['socket_id']))
  return s, token


def create_tunnel(socket, token):
  authorization_header, token = get_auth_header(token)
  if 'tunnels' in socket and len(socket['tunnels']) > 0:
    logging.debug('existing tunnel found with id: {}'.format(socket['tunnels'][0]['tunnel_id']))
    return socket['tunnels'][0], token
  else:
    tunnel = new_tunnel(authorization_header, socket['socket_id'])
    logging.debug('new tunnel created with id: {}'.format(tunnel['tunnel_id']))
    return tunnel, token

def mysocket_enabled(svc):
  if svc.metadata.annotations and 'mysocket.io/enabled' in svc.metadata.annotations and svc.metadata.annotations['mysocket.io/enabled'] == 'true':
    return True
  else:
    return False

def setup_tunnel(tunnel, svc, token):
  port = svc.spec.ports[0].port
  name = '{}.{}.svc'.format(svc.metadata.name, svc.metadata.namespace)

  logging.debug('setup new tunnel {} port {}'.format(name, port))

  if args.noop:
    logging.debug('noop run, returning')
    return

  ssh_user = get_user_id_from_token(token).replace('-','')
  ssh_server = "ssh.mysocket.io"
  #client = SystemSSH()
  #client = Paramiko()

  while True:
    logging.debug("Connecting...")
    client = Paramiko()
    client.connect(port, tunnel["local_port"], ssh_server, ssh_user, name)
    sleep(1)

  logging.debug("Done tunneling")

def get_user_id_from_token(token):
  data = jwt.decode(token, verify=False)
  if "user_id" in data:
    return data["user_id"]
  else:
    return False

def token_is_expired(token):
  data = jwt.decode(token, verify=False)
  if data['exp'] - 600 < time():
    return True
  else:
    return False

def get_auth_header(token):
  if token_is_expired(token):
    logging.info('Token expired, get new token...')
    token = get_token(username,password)['token']

  authorization_header = {
      "x-access-token": token,
      "accept": "application/json",
      "Content-Type": "application/json",
  }

  return authorization_header, token


def main():
  logging.info('Starting controller')

  # connect to k8s api
  try:
    config.load_kube_config()
  except:
    config.load_incluster_config()

  tunnels = {}

  # initial login mysocketctl
  token = get_token(username,password)['token']

  v1 = client.CoreV1Api()
  w = watch.Watch()

  resource_version = ""

  # start loop
  while True:
    logging.debug('Start watching for service events at version {}'.format(resource_version))
    try:
      for event in w.stream(v1.list_service_for_all_namespaces, resource_version=resource_version):
        resource_version = event['object'].metadata.resource_version
        s_name = "{}-{}".format(event['object'].metadata.namespace, event['object'].metadata.name)
        logging.debug("Event: %s %s" % (event['type'], event['object'].metadata.name))
        if event['type'] == 'ADDED':
          if mysocket_enabled(event['object']) and s_name not in tunnels:
            socket, token = create_socket(event['object'], token)
            tunnel, token = create_tunnel(socket, token)
            process = multiprocessing.Process(target=setup_tunnel, args=(tunnel,event['object'],token,))
            process.start()
            tunnels[s_name] = process
        elif event['type'] == 'MODIFIED':
          if mysocket_enabled(event['object']) and s_name not in tunnels:
            logging.debug("start tunneling")
            socket, token = create_socket(event['object'], token)
            tunnel, token = create_tunnel(socket, token)
            process = multiprocessing.Process(target=setup_tunnel, args=(tunnel,event['object'],token,))
            process.start()
            tunnels[s_name] = process
          elif not mysocket_enabled(event['object']) and s_name in tunnels:
            logging.debug("stop tunneling")
            a = tunnels[s_name].terminate()
            logging.debug("tunnel stopped")
            del(tunnels[s_name])
          else:
            logging.debug("no action needed")
        elif event['type'] == 'DELETED':
          if mysocket_enabled(event['object']) and s_name in tunnels:
            logging.debug("stop tunneling")
            tunnels[s_name].terminate()
            logging.debug("tunnel stopped")
            del(tunnels[s_name])
    except Exception as e:
      logging.error("watch error, restarting: {}".format(e))
      resource_version = ""
      sleep(10)
    except:
      logging.error("watch error, restarting")
      resource_version = ""
      sleep(10)

    sleep(1)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='mysocket.io controller')
  parser.add_argument('--loglevel', '-l', default='INFO', help='log level')
  parser.add_argument('--noop', '-n', action='store_true', help='do not create tunnels')
  parser.add_argument('--username', '-u', help='mysocket.io User/mail')
  parser.add_argument('--password', '-p', help='password')
  args = parser.parse_args()

  logging.basicConfig(format='%(asctime)s %(message)s',level=getattr(logging, args.loglevel.upper()))


  if args.username:
    username = args.username
  else:
    try:
      with open('/etc/mysocket/email') as f:
        username = f.readline().rstrip()
    except FileNotFoundError:
      logging.critical("no username/email provided")
      exit(1)

  if args.password:
    password = args.password
  else:
    try:
      with open('/etc/mysocket/password') as f:
        password = f.readline().rstrip()
    except FileNotFoundError:
      logging.critical('no password provided')
      exit(1)

  main()
