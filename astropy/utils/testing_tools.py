from __future__ import print_function
import socket

# save original socket method for restoration
socket_original = socket.socket
socket_create_connection = socket.create_connection
socket_bind = socket.socket.bind
socket_connect = socket.socket.connect

def turn_off_internet(verbose=False):
    """
    Disable internet access via python by preventing connections from being
    created using the socket module.  Presumably this could be worked around by
    using some other means of accessing the internet, but all default python
    modules (urllib, requests, etc.) use socket [citation needed].
    """
    __tracebackhide__ = True
    if verbose:
        print("Internet access disabled")

    # ::1 is apparently another valid name for localhost?
    # it is returned by getaddrinfo when that function is given localhost

    def no_bind(self, address, *args, **kwargs):
        host,port = address[:2]
        if not ('127.0.0.1' in host or 'localhost' in host or '::1' in host): 
            raise IOError("An attempt was made to connect to the internet")
        else:
            return socket_bind(self, address, *args, **kwargs)

    def no_connect(self, address, *args, **kwargs):
        host,port = address[:2]
        if not ('127.0.0.1' in host or 'localhost' in host or '::1' in host): 
            raise IOError("An attempt was made to connect to the internet")
        else:
            return socket_connect(self, address, *args, **kwargs)

    def no_create_connection(address, *args, **kwargs):
        host,port = address[:2]
        if not ('127.0.0.1' in host or 'localhost' in host): 
            raise IOError("An attempt was made to connect to the internet")
        else:
            return socket_create_connection(address, *args, **kwargs)

    # super hardcore: setattr(socket, 'socket', guard)
    # a little more forgiving?
    setattr(socket, 'create_connection', no_create_connection)
    setattr(socket.socket, 'bind', no_bind)
    setattr(socket.socket, 'connect', no_connect)

    return socket

def turn_on_internet(verbose=False):
    """
    Restore internet access.  Not used, but kept in case it is needed.
    """
    if verbose:
        print("Internet access enabled")
    setattr(socket, 'socket', socket_original)
    return socket
