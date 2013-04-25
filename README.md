This document explains how to use **dyeproxy**, a simple HTTP proxy.

If you have any questions or comments about this program, please send them to the author,
William Dye, at <williamdye@gatech.edu>. Note that this program was written for an 
introductory networking course and as such does not currently include functionality more 
advanced than serving a single HTTP GET request from a single host (or process) at a time. 
As time permits, I plan to expand the functionality of the proxy to serving multiple 
concurrent requests and all of the standard HTTP methods.

The program can easily be tested using the provided Makefile. The port number on which the
proxy runs is passed as a command-line argument to the program, and it should likewise be
passed as an argument to `make`. For example, to run dyeproxy on port 4040, run:

`make PORT=4040`

The program can be invoked just as easily using the executable in the bin/ directory with
a command such as:

`bin/dyeproxy 4040`

Once running, the program will provide various output at the console. When the proxy is 
ready to receive connections, the message '`dyeproxy running on port XXXX ...`' is printed.
When a client issues a request, the first line of the request is printed inside triple square
brackets. The program then tries to parse the request. The request must use HTTP version
1.0 or 1.1 to be parsed successfully, and the requested resource must use the HTTP protocol.
The request method must be '`GET`', and the hostname in the request must be valid. If all of
these conditions are met, the request is rewritten and the new request is printed to the 
console, with each line prefaced by '`>>>`'. Regardless of whether the request was parsed 
successfully, a response is returned to the client, and the response's headers are printed
to the console, with each line prefaced by '`<<<`'. If the request was valid, the response 
will be exactly the same as the response from the origin server; otherwise, the response 
will include a simple HTML page including the status code and reason phrase.

In addition to the status codes mentioned in the assignment (400, 404, and 501), **dyeproxy** 
may return two additional status codes. If a request is issued using any HTTP version other
than 1.0 or 1.1, **dyeproxy** responds with status code 505 (Not Supported). If a request is 
issued for a resource using any protocol besides HTTP, **dyeproxy** responds with status code
403 (Forbidden). For example, a request such as '`GET http://www.google.com HTTP/2.0`' would
receive a response with status code 505 (because HTTP 2.0 is unsupported), and a request 
such as '`GET ftp://www.google.com HTTP/1.1`' would receive a response with status code 403
(because FTP is unsupported).

Note that **dyeproxy** assumes that the request should be made on port 80, and including a 
port number after the hostname in the request is not (currently) supported. When receiving 
a response from an origin server, the socket timeout it set to 15 seconds to prevent one 
slow connection from tying up the whole proxy. (More motivation for allowing parallel 
connections?)

To terminate the program, enter `^C` (Ctrl-C) while the program is running. A series of 
statistics will be printed, and **dyeproxy** will exit.

The following is sample console output for a simple usage of the program in which three
requests are issued before the program is terminated (one valid, two invalid). Note that
the full responses, which are returned to the client, are not shown.


	$ make PORT=4040
	dyeproxy running on port 4040 ...
	
	[[[ GET foo HTTP/1.1 ]]]
	<<< HTTP/1.1 404 Not Found
	
	[[[ HEAD http://www.google.com HTTP/1.1 ]]]
	<<< HTTP/1.1 501 Not Implemented
	
	[[[ GET http://gtphipsi.org HTTP/1.1 ]]]
	>>> GET / HTTP/1.1
	>>> Host: gtphipsi.org
	>>> X-Forwarded-For: 128.61.113.40
	>>>
	<<< HTTP/1.1 301 Moved Permanently
	<<< Server: nginx
	<<< Date: Wed, 17 Apr 2013 03:44:13 GMT
	<<< Content-Type: text/html; charset=iso-8859-1
	<<< Content-Length: 229
	<<< Connection: keep-alive
	<<< Location: https://gtphipsi.org/
	
	^C
	------- dyeproxy statistics -------
	Elapsed time			26 seconds
	# of requests received			3
	# of 200 (OK) responses			1
	# 400 (Bad Request) errors		0
	# 505 (Not Supported) errors	0
	# 403 (Forbidden) errors		0
	# 404 (Not Found) errors		1
	# 501 (Not Implemented) errors	1
