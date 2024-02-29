import time

import pyvisa as visa

global rm
rm = visa.ResourceManager()


def sweep_resources(searchString: str = '?*'):
    print(f'Available resources based on the search string "{searchString}":')
    devices = rm.list_resources(searchString)
    if len(devices) > 0:
        for i, device in enumerate(devices):
            print(f'\t[{i}].{device}')
    else:
        print("Didn't find anything!")
    return devices


class VISA_Communicator_Wrapper:
    """" This class wrapped most common methods from PyVISA to control devices and
    implement context managers allow you to allocate and release resources precisely when you want to """

    def __init__(self, address: str = ''):
        if not address:
            print('Address is not given.')
            devices = sweep_resources()
            idx = int(input("Please select an address: ").strip())
            address = devices[idx]

        self.address = address

    def __repr__(self):
        return f"Basic_Communicator::{self.address}"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, address):
        try:
            self.communicator = rm.open_resource(f'{address}')
            print(f'Successfully connected to: "{address}"')
            self._address = address
        except Exception as err:
            print(f'Cannot make a connection to "{address}" because of {err}')
            print('Please verify the address string')
            # sweep_resources()
            raise ConnectionError

    def write(self, cmd: str):
        return self.communicator.write(cmd)

    def read(self):
        msg = self.communicator.read().strip()
        return msg

    def query(self, cmd: str):
        msg = self.communicator.query(cmd).strip()
        return msg

    def close(self):
        print(f'Connection to {self._address} is close')
        self.communicator.close()

    def siesta(self, sec):
        time.sleep(sec)

    def clear(self):
        self.communicator.clear()
