from re import split
from sys import exit
from pathlib import Path
from hashlib import sha1
from requests import Session
from urllib.parse import urljoin

class GitDump:
    def __init__(self, url, headers={}, proxies={}, directory='output'):
        self.BASEURL   = url
        self.DIRECTORY = directory
        self.define_session(
            headers=headers, 
            proxies=proxies
        )
        self.define_static_files()

    def define_session(self, headers={}, proxies={}, session=False):
        if session:
            self.session = session
        else:
            self.session = Session()
            self.session.headers = headers
            self.session.proxies = proxies

    def define_static_files(self):
        self.STATIC_FILES = [
            '.git/config',
            '.git/index',
            '.git/HEAD',
            '.git/packed-refs',
            '.git/description',
            '.git/info/exclude',
            '.git/refs/remotes/origin/HEAD',
            '.git/logs/refs/remotes/origin/HEAD',
            '.git/hooks/post-update.sample'
        ]

    def download_static_files(self):
        for static_file in self.STATIC_FILES:
            target_url = f"{self.BASEURL}/{static_file}"
            response   = self.session.get(target_url)
            self._debug(f"[{response.status_code}] {target_url}")

            if response.status_code != 200: continue
            local_path = Path(f"{self.DIRECTORY}/{static_file}")
            local_path.parent.mkdir(exist_ok=True, parents=True)
            local_path.write_bytes(response.content)

    def read_until(self, file, character):
        return b''.join(iter(lambda: file.read(1), character))

    def parse_tree_extension(self, file):
        path_component   = self.read_until(file, b'\x00')
        entry_count      = self.read_until(file, b' ')
        subtree_count    = self.read_until(file, b'\n')
        tree_object_hash = file.read(20).hex()
        print(path_component, tree_object_hash)
        for _ in range(int(subtree_count)):
            self.parse_tree_extension(file)

    def parse_index(self):
        local_path = Path(f"{self.DIRECTORY}/.git/index")
        if not local_path.exists():
            exit('[-] Failed to locate "index" file')

        with open(local_path, 'rb') as file:
            signature = file.read(4)
            if signature != b'DIRC':
                exit('[-] Index is missing signature')

            version = file.read(4)[-1]
            print(f'[+] Index File Version: {version}')
            if version not in [2, 3, 4]:
                exit('[-] Index contains incorrect version')
            
            entry_count = int.from_bytes(file.read(4))

            for _ in range(entry_count):
                # starting position of cursor
                entry_start_offset = file.tell()

                # epoch of creation and modified time
                ctime_seconds     = file.read(4)
                ctime_nanoseconds = file.read(4)
                mtime_seconds     = file.read(4)
                mtime_nanoseconds = file.read(4)

                # unix metadata
                device = file.read(4)
                inode  = file.read(4)
                mode   = file.read(4)
                uid    = file.read(4)
                gid    = file.read(4)

                # length of file content
                file_size = int.from_bytes(file.read(4))

                # sha1 hash of blob object
                blob_hash = file.read(20)
                
                # flags
                flags = ''.join(f'{byte:08b}' for byte in file.read(2))
                assume_valid    = flags[0]
                extended        = flags[1]
                merge_stage     = flags[2:3]
                filename_length = int(flags[4:], 2)

                # read NULL terminated filename
                filename  = file.read(filename_length)
                null_byte = file.read(1)
                print(filename.decode())
                # ending position of cursor
                entry_end_offset = file.tell()
                entry_size = entry_end_offset - entry_start_offset

                # calculate padding
                padding_remainder = entry_size % 8
                padding_length = (8 - padding_remainder) if padding_remainder else 0
                padding = file.read(padding_length)

            chunk = file.read(4)
            if chunk == b'TREE':
                extension_length = int.from_bytes(file.read(4))
                self.parse_tree_extension(file)
                
    def clone(self):
        self.download_static_files()
        self.parse_index()

    def _debug(self, message):
        print(message)

gitdump = GitDump(url='')
gitdump.clone()