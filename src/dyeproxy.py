#!/usr/bin/env python
#
# dyeproxy - lightweight Web proxy server
#
# Written for CS 3251 Problem Set 3, Spring 2013
# Professor Nick Feamster, Georgia Institute of Technology
#
# Author: William Dye <williamdye@gatech.edu>
# Last Modified: April 17, 2013


import socket
from sys import argv, exit
from time import time


BACKLOG_SIZE 	= 1							# the size of the backlog to pass to listen()
BUFFER_SIZE 	= 4096						# the size of the buffer to pass to recv()
DEFAULT_TIMEOUT = 15.0						# the default socket timeout (in seconds)
HTTP_PORT		= 80						# the port to connect to on origin servers
HTTP_VERSIONS	= ['HTTP/1.0', 'HTTP/1.1']	# supported HTTP version strings
HTTP_METHODS	= ['OPTIONS', 'HEAD',		# all methods except 'GET' are unsupported
				   'POST', 'PUT', 'DELETE', 'TRACE', 'CONNECT']
ERROR_PHRASES	= {400: 'Bad Request', 403: 'Forbidden',	# phrases for error status codes
                   404: 'Not Found', 501: 'Not Implemented', 505: 'Not Supported'}


def usage(port=0):
	"""Print a usage message and exit the program."""
	if port == 0:
		print 'Usage: %s <port>' % argv[0]
	elif port < 0:
		print 'Port must be an integer! \'%s\' is not a valid port.' % argv[1]
	else:	# 0 < port < 1024
		print 'Port must be greater than 1023!'
	exit(1)


def parse_args():
	"""Parse command line arguments; if they are invalid, print a usage message and exit."""
	if len(argv) < 2: usage()
	try:
		port = int(argv[1])
	except ValueError:
		usage(-1)
	if port < 1024: usage(port)
	return port
	
	
def validate_method_and_version(method, version):
	"""Check that the HTTP method is 'GET' and that the version string is valid."""
	status = 200
	if method in HTTP_METHODS:
		status = 501	# this proxy only supports GET requests
	elif method != 'GET':
		status = 400	# not a valid method, so bad request	
	elif version not in HTTP_VERSIONS:
		status = 505	# HTTP version string must be one of 'HTTP/1.0' or 'HTTP/1.1'
	return status


def validate_uri(uri):
	"""Validate a request URI and split it into hostname and requested resource."""
	if '://' in uri: 
		if uri[:uri.find('://')] != 'http':
			return 403, None, None
		uri = uri[uri.find('://')+3:]
	if '/' in uri:
		hostname = uri[:uri.find('/')]
		uri = uri[uri.find('/'):]
	else:
		hostname = uri
		uri = '/'
	status = 200
	try:
		socket.gethostbyname(hostname)
	except socket.error:
		status = 404
	return status, hostname, uri


def validate_request_line(line):
	"""Validate that the line is of the form 'GET <absolute-uri> HTTP/1.[0|1]'."""
	words = line.rstrip('\r\n').split(' ')
	if len(words) != 3: return 400, None, None		# < 3 words is a bad request
	status = validate_method_and_version(words[0], words[2])
	if status != 200: return status, None, None		# either not a GET or invalid version
	status, hostname, uri = validate_uri(words[1])
	if status != 200: return status, None, None		# invalid or nonexistent URI
	return 200, hostname, 'GET %s %s\r\n' % (uri, words[2])		# success


def rewrite_request(req, origin):
	"""Rewrite an HTTP request to be forwarded to a Web host."""
	lines = req.splitlines(True)
	status, hostname, new_req_line = validate_request_line(lines[0])
	if status != 200: return (status, req, None)
	lines[0] = new_req_line
	rewrote_host = False
	rewrote_x = False
	for line in lines[1:]:
		if line.startswith('Host:'):
			line = 'Host: %s\r\n' % hostname
			rewrote_host = True
		elif line.startswith('X-Forwarded-For:'):
			line = line.rstrip('\r\n') + ', %s\r\n' % origin
			rewrote_x = True
	if not rewrote_host:
		lines.insert(1, 'Host: %s\r\n' % hostname)
	if not rewrote_x:
		lines.insert(len(lines) - int(rewrote_host), 'X-Forwarded-For: %s\r\n' % origin)
	if lines[-1] != '\r\n':
		lines.append('\r\n')
	return (200, ''.join(lines), hostname)


def get_response(req, hostname):
	"""Connect to a remote host, issue a request, and return the response."""
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.connect((hostname, HTTP_PORT))
	sock.sendall(req)
	sock.settimeout(DEFAULT_TIMEOUT)
	resp = []
	while True:		# receive from the socket until the transmission is complete
		try:
			data = sock.recv(BUFFER_SIZE)
		except socket.timeout:
			break
		if not data: break
		resp.append(data)
	sock.close()
	return ''.join(resp)


def get_error_response(status, usehttp10):
	"""Return an HTTP response based on the status code."""
	version = 'HTTP/1.0' if usehttp10 else 'HTTP/1.1'
	error = ERROR_PHRASES[status]
	resp = []
	resp.append('%s %d %s\r\n\r\n' % (version, status, error))
	resp.append('<!doctype html><html><head><title>%d %s</title>' % (status, error))
	resp.append('</head><body><h1>%d %s</h1></body></html>\r\n' % (status, error))
	return ''.join(resp)


def handle_request(req, origin):
	"""Parse/rewrite an HTTP request and, if valid, forward it to the intended host."""
	first = req[:req.find('\r\n')]
	print '[[[', first, ']]]'
	status, req, hostname = rewrite_request(req, origin)
	if status == 200:
		for line in req.splitlines():
			print '>>>', line
		resp = get_response(req, hostname)
	else:
		resp = get_error_response(status, ('HTTP/1.0' in first))
	for line in resp.splitlines():
		if not line:
			break
		print '<<<', line
	print	
	return status, resp


def run_server(port):
	"""Open a socket on the specified port and accept connections on the socket."""
	num_reqs = 0
	responses = {200: 0, 400: 0, 403: 0, 404: 0, 501: 0, 505: 0}
	localhost = socket.gethostbyname(socket.gethostname())
	# create the socket and bind it to the specified port
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.bind(('', port))	# '' is a 'symbolic hostname meaning all available interfaces'
	sock.listen(BACKLOG_SIZE)
	print 'dyeproxy running on port %d ...\n' % port
	start = time()
	while True:		# main loop: wait for connections/requests, then parse and respond
		conn = None
		try:
			conn, addr = sock.accept()		# accept a connection (blocking)
			req = conn.recv(BUFFER_SIZE)	# receive a message (blocking)
		except KeyboardInterrupt:
			break
		if req:
			num_reqs += 1
			status, resp = handle_request(req, (localhost if addr[0] == '127.0.0.1' else addr[0]))
			responses[status] += 1
			conn.sendall(resp)
		conn.close()
	if conn is not None:
		conn.close()
	sock.close()	# close the socket before exiting
	stop = time()
	print '\n------- dyeproxy statistics -------'
	print 'Elapsed time\t\t%d seconds' % (stop - start)
	print '# of requests received\t\t%d' % num_reqs
	print '# of 200 (OK) responses\t\t%d' % responses[200]
	for status, message in ERROR_PHRASES.iteritems():
		print '# %d (%s) errors\t%d' % (status, message, responses[status])


if __name__ == '__main__':
	port = parse_args()
	run_server(port)
