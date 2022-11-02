#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2020 RENCI NRIG
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Author Komal Thareja (kthare10@renci.org)
import logging
import os
import time

import chi
import chi.server

from fabfed.model import Node
import fabfed.provider.chi.chi_util as util


class ChiNode(Node):
    def __init__(self, *, label, name: str, image: str, site: str, flavor: str, project_name: str,
                 logger: logging.Logger, key_pair: str, network: str):
        super().__init__(label=label, name=name, image=image, site=site, flavor=flavor)
        self.project_name = project_name
        self.key_pair = key_pair
        self.network = network
        self.logger = logger
        self.private_key_file = os.environ['OS_SLICE_PRIVATE_KEY_FILE']
        self._retry = 10
        self.username = "cc"
        self.state = None
        # self.name = f'{prefix}-{self.name}'
        self.lease_name = f'{self.name}-lease'
        self.addresses = []
        self.reservations = []
        # TODO This should not be hardocded
        # chi.lease.add_node_reservation(self.reservations, count=1, node_type=self.flavor)
        chi.lease.add_node_reservation(self.reservations, count=1, node_type="compute_cascadelake_r")
        self._lease_helper = util.LeaseHelper(lease_name=self.lease_name, logger=self.logger)
        self.id = ''

    def get_reservation_id(self):
        return self._lease_helper.get_reservation_id()

    def get_reservation_state(self) -> str:
        return self.state

    def __populate_state(self, node_info):
        self.logger.debug(f"Node Info for {self.name}: {node_info}")
        self.state = node_info['OS-EXT-STS:vm_state']
        addresses = node_info['addresses'][self.network]
        self.addresses = [a['addr'] for a in addresses]

        if not self.mgmt_ip:
            for a in addresses:
                if a['OS-EXT-IPS:type'] == 'floating':
                    self.mgmt_ip = a['addr']

        self.id = self.get_reservation_id()

    def __create_kvm(self):
        return chi.server.create_server(server_name=self.name, image_name=self.image,
                                        network_name=self.network, key_name=self.key_pair,
                                        flavor_name=self.flavor)

    def __create_baremetal(self):
        return chi.server.create_server(server_name=self.name, image_name=self.image,
                                        network_name=self.network, key_name=self.key_pair,
                                        reservation_id=self._lease_helper.get_reservation_id())

    def create(self):
        chi.set('project_name', self.project_name)
        chi.set('project_domain_name', 'default')

        if self.site != "KVM@TACC":
            chi.use_site(self.site)
            self._lease_helper.create_lease_if_needed(reservations=self.reservations, retry=self._retry)

        try:
            self.logger.info(f"Checking if node {self.name} exists")
            node_id = chi.server.get_server_id(self.name)
        except ValueError as e:
            self.logger.warning(f"Error occurred for {self.name} {e}. Will attempt to create ")
            node = self.__create_kvm() if self.site == "KVM@TACC" else self.__create_baremetal()
            node_id = node.id

        self.logger.info(f"Got node {self.name} with {node_id}")

    def wait_for_active(self):
        chi.set('project_name', self.project_name)
        chi.set('project_domain_name', 'default')

        if self.site != "KVM@TACC":
            chi.use_site(self.site)

        self.logger.info(f"Waiting for node {self.name} to be Active!")
        node_id = chi.server.get_server_id(self.name)
        chi.server.wait_for_active(server_id=node_id)
        node = chi.server.get_server(node_id)
        self.__populate_state(node.to_dict())

        if not self.mgmt_ip:
            self.logger.info(f"Associating the Floating IP to {self.name}!")
            self.mgmt_ip = chi.server.associate_floating_ip(server_id=node.id)

    def delete(self):
        chi.set('project_name', self.project_name)
        chi.set('project_domain_name', 'default')

        if self.site != "KVM@TACC":
            chi.use_site(self.site)

        try:
            node_id = chi.server.get_server_id(f"{self.name}")

            if node_id is not None:
                self.logger.debug(f"Deleting node {self.name}")
                chi.server.delete_server(server_id=node_id)
                self.logger.info(f"Deleted node {self.name}")
        except ValueError as ve:
            self.logger.warning(f"Error deleting node {self.name}: {ve}")

        self._lease_helper.delete_lease()

    def upload_file(self, local_file_path, remote_file_path, retry=3, retry_interval=10):
        self.logger.debug(f"upload node: {self.name}, local_file_path: {local_file_path}")
        key = util.get_paramiko_key(private_key_file=self.private_key_file)
        helper = util.SshHelper(self.mgmt_ip, self.username, key)

        for attempt in range(retry):
            try:
                helper.connect_ftp()
                helper.ftp_client.put(local_file_path, remote_file_path)
            except Exception as e:
                self.logger.info(f"SCP upload fail {e}. Node: {self.name}, tried {attempt + 1}")
                time.sleep(retry_interval)
            finally:
                helper.close_quietly()

    def download_file(self, local_file_path, remote_file_path, retry=3, retry_interval=10):
        self.logger.debug(f"download node: {self.name}, remote_file_path: {remote_file_path}")
        key = util.get_paramiko_key(private_key_file=self.private_key_file)
        helper = util.SshHelper(self.mgmt_ip, self.username, key)

        for attempt in range(retry):
            try:
                helper.connect_ftp()
                helper.ftp_client.get(remote_file_path, local_file_path)
            except Exception as e:
                self.logger.info(f"SCP download fail {e}. Node: {self.name}, tried {attempt + 1}")
                time.sleep(retry_interval)
            finally:
                helper.close_quietly()

    def upload_directory(self, local_directory_path, remote_directory_path, retry=3, retry_interval=10):
        import tarfile
        import os

        self.logger.debug(f"upload node: {self.name}, local_directory_path: {local_directory_path}")

        output_filename = local_directory_path.split('/')[-1]
        root_size = len(local_directory_path) - len(output_filename)
        temp_file = "/tmp/" + output_filename + ".tar.gz"

        with tarfile.open(temp_file, "w:gz") as tar_handle:
            for root, dirs, files in os.walk(local_directory_path):
                for file in files:
                    tar_handle.add(os.path.join(root, file), arcname=os.path.join(root, file)[root_size:])

        self.upload_file(temp_file, temp_file, retry, retry_interval)
        os.remove(temp_file)
        self.execute("mkdir -p "+remote_directory_path + "; tar -xf " + temp_file + " -C " + remote_directory_path +
                     "; rm " + temp_file, retry, retry_interval)

    def download_directory(self, local_directory_path, remote_directory_path, retry=3, retry_interval=10):
        import tarfile
        import os
        self.logger.debug(f"upload node: {self.name}, local_directory_path: {local_directory_path}")

        temp_file = "/tmp/unpackingfile.tar.gz"
        self.execute("tar -czf " + temp_file + " " + remote_directory_path, retry, retry_interval)

        self.download_file(temp_file, temp_file, retry, retry_interval)
        tar_file = tarfile.open(temp_file)
        tar_file.extractall(local_directory_path)

        self.execute("rm " + temp_file, retry, retry_interval)
        os.remove(temp_file)

    def execute(self, command, retry=3, retry_interval=10):
        self.logger.debug(f"execute node: {self.name}, management_ip: {self.mgmt_ip}, command: {command}")
        key = util.get_paramiko_key(private_key_file=self.private_key_file)
        helper = util.SshHelper(self.mgmt_ip, self.username, key)
        script = ' /tmp/chi_execute_script.sh'
        chmod_cmd = f'chmod +x {script}'
        cmd = f'echo "{command}" > {script};{chmod_cmd};{script}'

        for attempt in range(retry):
            try:
                helper.connect()
                _, stdout, stderr = helper.client.exec_command(cmd)
                stdout = str(stdout.read(), 'utf-8').replace('\\n', '\n')
                stderr = str(stderr.read(), 'utf-8').replace('\\n', '\n')
                return stdout, stderr
            except Exception as e:
                self.logger.info(f"SSH execute fail {e}. Node: {self.name}, tried {attempt + 1}")
                time.sleep(retry_interval)
            finally:
                helper.close_quietly()
