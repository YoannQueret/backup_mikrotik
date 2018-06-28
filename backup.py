#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Yoann QUERET <yoann@queret.net>
2016-06
"""

import os
import argparse
import paramiko
import pysftp
import sys
import json
import time

class Config():
    def __init__(self, config_file):
        self.config_file = config_file
        self.load(config_file)
        
    def __getitem__(self, item):
        return getattr(self, item)
            
    def load(self, config_file):
        with open(self.config_file) as data_file:    
            self.config = json.load(data_file)

    def write(self, config):
        try:
            with open(self.config_file, 'w') as outfile:
                data = json.dumps(config, indent=4, separators=(',', ': '))
                outfile.write(data)
        except Exception as e:
            raise ValueError( str(e) )

if __name__ == '__main__':
    # Get configuration file in argument
    parser = argparse.ArgumentParser(description='backup Mikrotik')
    parser.add_argument('-c','--config', help='configuration filename',required=True)
    cli_args = parser.parse_args()
    
    # Check if configuration exist and is readable
    if os.path.isfile(cli_args.config) and os.access(cli_args.config, os.R_OK):
        print ("Use configuration file %s") % (cli_args.config)
    else:
        print ("Configuration file is missing or is not readable - %s") % (cli_args.config)
        sys.exit(1)
        
    # Load configuration
    conf = Config(cli_args.config)
    
    # Check if backup_base_directory is writable
    if os.path.isdir(conf.config['global']['backup_base_directory']) and os.access(conf.config['global']['backup_base_directory'], os.W_OK):
        print ("Use backup base directory %s") % (conf.config['global']['backup_base_directory'])
    else:
        print ("Backup base directory is missing or is not writable - %s") % (conf.config['global']['backup_base_directory'])
        sys.exit(1)
        
    # Loop on host
    if conf.config['devices']:
        for device in conf.config['devices']:
            print ("Start backup device : %s") % (device['host'])
            
            backup_dir = '%s/%s' % (conf.config['global']['backup_base_directory'], device['host'])
            backup_file = 'configuration.export'
            
            # Check if backup directory exist and create it if necessary
            if not os.path.isdir(backup_dir):
                os.makedirs(backup_dir)
                
            # Check if backup directory is writeable
            if not os.access(backup_dir, os.W_OK):
                print ("Backup directory is not writeable - %s") % (backup_dir)
            
            
            # Create configuration file on device
            
            # -- Use device private key if available or global private key
            if 'pkey_file' in device:
                pkey = paramiko.RSAKey.from_private_key_file(device['pkey_file'])
            else:
                pkey = paramiko.RSAKey.from_private_key_file(conf.config['global']['pkey_file'])
            
            # -- Set ssh client
            ssh_client = paramiko.SSHClient()
            ssh_client.load_system_host_keys()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            #ssh_client.set_missing_host_key_policy(paramiko.WarningPolicy)
            
            # -- ssh connect
            try:    
                ssh_client.connect(device['host'], port=device['port'], username=device['user'], pkey=pkey)
            except:
                print ('- Error during ssh connection')
            
            # -- ssh command
            try:
                cmd = '/export file=%s' % (backup_file)
                ssh_client.exec_command(cmd)
            except:
                print ('- Error during export command')
            
            # -- close ssh connection
            try:
                ssh_client.close()
            except:
                pass
            
            # Wait to leave time to write configuration file
            time.sleep(2)
            
            # Get configuration file
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None  
            
            try:
                sftp = pysftp.Connection(device['host'], port=device['port'], username=device['user'], private_key=pkey, cnopts=cnopts)
            except:
                print ('- Error during sftp connection')
                
            try:
                rsc_backup_file = '%s.rsc' % (backup_file)
                curr_path = os.getcwd()
                os.chdir(backup_dir)
                sftp.get(rsc_backup_file)
                os.chdir(curr_path)
            except:
                print ('- Error during sftp get file : %s.rsc') % (backup_file)
                    
    else:
        print ("No devices to backup")