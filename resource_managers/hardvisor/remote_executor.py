import asyncio
import logging


class RemoteExecutor:
    def __init__(self, connection_details):
        '''
        connection_details = {'ip': '1.2.3.4', 'user': 'user',
        'password': 'password1!' OR 'key_file_path': '/path/to/id_rsa.pub'}
        '''
        assert ('password' in connection_details) != ('key_file_path' in connection_details), \
            f"Must have password or key_file_path in connection_details. received: {connection_details}"
        self.connection_details = connection_details

    async def run(self, cmd):
        remote_cmd = f"{await self.ssh_string()} '{cmd}'"
        logging.error(remote_cmd)
        proc = await asyncio.create_subprocess_shell(
            remote_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        # todo: fix problem here that if there is a prompt or something this hangs...
        stdout, stderr = await proc.communicate()
        return proc.returncode, stdout.decode(), stderr.decode()

    async def ssh_string(self):
        if 'key_file_path' in self.connection_details:
            return f'ssh -i {self.connection_details["key_file_path"]} {self.connection_details["user"]}@{self.connection_details["ip"]}'
        return f'sshpass -p {self.connection_details["password"]} ssh {self.connection_details["user"]}@{self.connection_details["ip"]}'

    async def reboot(self):
        self.run("sudo reboot -f")

