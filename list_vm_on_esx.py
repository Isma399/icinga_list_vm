#!/usr/bin/env python
# coding: utf8
# ICINGA API


"""
Python program for updating the vms list on an ESX / vCenter host declared in Icinga
Modify custom variable vmware_vmname
Could be use then to check services like that :
    
    apply Service "soap-vm-cpu" for (vmname in host.vars.vmware_vmname){
        name = vmname + ".cpu"
        check_command = "vmware-esx-soap-vm-cpu"
        vars.vwmare_vmname = vmname
        assign where host.vars.vmware_vmname
        vars.vmware_sessionfile = host.name
    }

Authentification file for ESX like that:
    username=...@..
    password=..

"""

import atexit
from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim
import argparse
import requests, json

parser = argparse.ArgumentParser(description=' List VM on Vcenter or ESX',add_help=False)
parser.add_argument('--file','-f', dest='file', help = 'Authentification file',required=True)
parser.add_argument('--server','-s', dest='host', help='ESX or Vcenter name as declared in Icinga hosts',required=True)
parser.add_argument('--icinga_api_user','-u',dest='icinga_api_user',required=True)
parser.add_argument('--icinga_api_password','-p',dest='icinga_api_password',required=True)
parser.add_argument('--verbose','-v',dest='verbose',action='store_true')
arguments = parser.parse_args()
with open(arguments.file,"r") as infos:
    info = infos.readlines()
    user = info[0].split('=')[1].strip()
    pwd =  info[1].split('=')[1].strip()
host = arguments.host

def list_vm(host):
    '''
    Connecte to Vcenter and returns VMs 
    '''
    service_instance = connect.SmartConnect(host=host,user=user,pwd=pwd)
    atexit.register(connect.Disconnect, service_instance)
    content = service_instance.RetrieveContent()
    container = content.rootFolder  # starting point to look into
    viewType = [vim.VirtualMachine]  # object types to look for
    recursive = True  # whether we should look into it recursively
    containerView = content.viewManager.CreateContainerView(
        container, viewType, recursive)
    l_vm = []
    children = containerView.view
    for child in children:
        l_vm.append(child.config.name.lower()) 
    if arguments.verbose:
        print 'List VM on '+host+': \n'+'\n'.join(l_vm)        
    return l_vm

def add_vm(host, list_vm):
    '''
    Ajoute la liste des VMs au Vcenter (host)
    '''
    requests.packages.urllib3.disable_warnings() 
    request_url = "https://nagios.univ-brest.fr:5665/v1/objects/hosts"
    headers = {
            'Accept': 'application/json',
            'X-HTTP-Method-Override': 'POST'
            }
    data = {
            "filter": 'match("'+ host +'",host.name)',
            "attrs" : { "vars.vmware_vmname" : list_vm }
    }
    r = requests.post(request_url,
        headers=headers,
        auth=(arguments.icinga_api_user,arguments.icinga_api_password),
        data=json.dumps(data),
        verify="/etc/icinga2/pki/ca.crt")
    if (r.status_code == 200):
        if arguments.verbose:
            print "Result: " + json.dumps(r.json())
        request_url = "https://nagios.univ-brest.fr:5665/v1/actions/restart-process"
        r = requests.post(request_url, headers=headers,
            auth=('root', 'icinga'), verify="/etc/icinga2/pki/ca.crt")
        if arguments.verbose:
            print "-------------------\nResult: " + json.dumps(r.json())
    else:
        print r.text
        r.raise_for_status()

list_vm = list_vm(host)
add_vm(host, list_vm)
