# Copyright 2018 Autodesk, Inc.  All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license agreement
# provided at the time of installation or download, or which otherwise accompanies
# this software in either electronic or hard copy form.
#

import re
import argparse
import urlparse
import BaseHTTPServer
import json
import ssl
import logging
import subprocess

import sg_jira

DESCRIPTION = """
A simple web app frontend to the SG Jira bridge.
"""

CSS_TEMPLATE = """
        <style>
            body {
                margin: 0;
                background-color: #eee;
                font-family: Arial, Helvetica, sans-serif;
            }
            h1 {
                background-color: whitesmoke;
                color: #00BAFF;
                border-radius: 5px;
                padding: 5 5 5 15px;
                border-bottom: 1px solid #ddd;
            }
            .content { margin: 0 0 15px 15px; }
            .error { margin: 0 0 15px 15px; }
            .details { margin: 40px 0 15px 15px; }
            h2 { margin-bottom: 10px; }
            p { margin-top: 10px; }
        </style>
"""

HMTL_TEMPLATE = """
    <head>
        <title>SG Jira Bridge: %s</title>
        {style}
    </head>
    <body>
        <h1>SG Jira Bridge</h1>
        <div class="content">
            <h2>%s</h2>
            <p>%s</p>
        </div>
    </body>
</html>
""".format(style=CSS_TEMPLATE)

# We overriding the default html error template to render errors to the user.
# This template *requires* the following format tokens:
# - %(code)d - for the response code
# - %(explain)s - for the short explanation of the response code
# - %(message)s - for a detailed message about the error
HTML_ERROR_TEMPLATE = """
    <head>
        <title>SG Jira Bridge Error %(code)d: %(message)s</title>
        {style}
    </head>
    <body>
        <h1>SG Jira Bridge</h1>
        <div class="error">
            <h2>Error %(code)d</h2>
            <p>%(explain)s</p>
        </div>
        <div class="details">
            <p><strong>Details: </strong> <pre>%(message)s</pre></p>
        </div>
    </body>
""".format(style=CSS_TEMPLATE)

# Please note that we can't use __name__ here as it would be __main__
logger = logging.getLogger("webapp")


def get_sg_jira_bridge_version():
    """
    Helper to extract a version number for the sg-jira-bridge module.

    This will attenmpt to extract the version number from git if installed from
    a cloned repo. If a version is unable to be determined, or the process
    fails for any reason, we return "dev"

    :returns: A major.minor.patch[.sub] version string or "dev".
    """
    # Note: if you install from a cloned git repository
    # (e.g. pip install ./tk-core), the version number
    # will be picked up from the most recently added tag.
    try:
        version_git = subprocess.check_output(["git", "describe", "--abbrev=0"]).rstrip()
        return version_git
    except Exception:
        # Blindly ignore problems. Git might be not available, or the user may
        # have installed via a zip archive, etc...
        pass
        
    return "dev"


class Server(BaseHTTPServer.HTTPServer):
    """
    A web server
    """
    def __init__(self, settings, *args, **kwargs):
        # Note: BaseHTTPServer.HTTPServer is not a new style class so we can't use
        # super here.
        BaseHTTPServer.HTTPServer.__init__(self, *args, **kwargs)
        self._sg_jira = sg_jira.Bridge.get_bridge(settings)

    def sync_in_jira(self, *args, **kwargs):
        """
        Just pass the given parameters to the SG Jira Brige method.
        """
        return self._sg_jira.sync_in_jira(*args, **kwargs)

    def sync_in_shotgun(self, *args, **kwargs):
        """
        Just pass the given parameters to the SG Jira Brige method.
        """
        return self._sg_jira.sync_in_shotgun(*args, **kwargs)

    @property
    def sync_settings_names(self):
        """
        Return the list of sync settings this server handles.
        """
        return self._sg_jira.sync_settings_names


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  
    # Inject the version of sg-jira-bridge into server_version for the headers.
    server_version = "sg-jira-bridge/%s %s" % (
        get_sg_jira_bridge_version(), 
        BaseHTTPServer.BaseHTTPRequestHandler.server_version
    )
    # BaseHTTPServer Class variable that stores the HTML template for error 
    # pages. Override the default error page template with our own.
    error_message_format = HTML_ERROR_TEMPLATE

    def post_response(self, response_code, message, content=None):
        """
        Convenience method for handling the response

        Handles sending the response, setting headers, and writing any
        content in the expected order. Sets appropriate headers including 
        content length which is required by HTTP/1.1.
        
        :param int response_code: Standard HTTP response code sent in headers.
        :param str message: Message to accompany response code in headers.
        :param str content: Optional content to return as content in the 
            response. This is typically html displayed in a browser. 
        """
        # NOTE: All responses must:
        #   - send the response first.
        #   - then, if there is some data, call end_headers to add a blank line.
        #   - then write the data, if any, with self.wfile.write
        self.send_response(response_code, message)

        content_len = 0
        if content:
            content_len = len(content)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", content_len)
        # TODO: Ideally we use the default functionality of HTTP/1.1 where
        # keep-alive is True (no header needed). However, for some reason, 
        # this currently blocks new connections for 60 seconds (likely the 
        # default keep-alive timeout). So for now we explicitly close the 
        # connection with the header below to ensure things run smoothly.
        # Once the issue has been resolved, we can remove this header. 
        self.send_header("Connection", "close")
        self.end_headers()
        if content:
            self.wfile.write(content)

    def do_GET(self):
        """
        Handle a GET request.
        """
        # Extract path components from the path, ignore leading '/' and
        # discard empty values coming from '/' at the end or multiple
        # contiguous '/'.
        path_parts = [x for x in self.path[1:].split("/") if x]
        if not path_parts:
            self.post_response(
                200, 
                "The server is alive",
                HMTL_TEMPLATE % (
                    "The server is alive",
                    "The server is alive",
                    ""
                )
            )
            return

        # Return a correct error for browser favicon requests in order to 
        # reduce confusing log messages that look bad but aren't.  
        if len(path_parts) == 1 and path_parts[0] == "favicon.ico":
            self.send_error(404)
            return
        if len(path_parts) < 2:
            self.send_error(400, "Invalid request path %s" % self.path)
            return
        if path_parts[0] == "sg2jira":
            title = "Shotgun to Jira"
        elif path_parts[0] == "jira2sg":
            title = "Jira to Shotgun"
        else:
            self.send_error(400, "Invalid action %s" % path_parts[0])
            return
        settings_name = path_parts[1]
        if settings_name not in self.server.sync_settings_names:
            self.send_error(400, "Invalid settings name %s" % settings_name)
            return
 
        # Success, send a basic html page.
        self.post_response(
            200,
            "Syncing with %s settings." % settings_name,
            HMTL_TEMPLATE % (
                title,
                title,
                "Syncing with %s settings." % settings_name
            )
        )

    def do_POST(self):
        """
        Handle a POST request.

        Post url paths need to have the form::

          sg2jira/Settings name[/SG Entity type/SG Entity id]
          jira2sg/Settings name/Jira Resource type/Jira Resource key

        If the SG Entity is not specified in the path, it must be specified in
        the provided payload.
        """
        try:
            direction = None
            settings_name = None
            entity_type = None
            entity_key = None
            parsed = urlparse.urlparse(self.path)
            # Extract path components from the path, ignore leading '/' and
            # discard empty values coming from '/' at the end or multiple
            # contiguous '/'.
            path_parts = [x for x in parsed.path[1:].split("/") if x]
            if len(path_parts) == 4:
                direction, settings_name, entity_type, entity_key = path_parts
            elif len(path_parts) == 2:
                direction, settings_name = path_parts
            else:
                self.send_error(400, "Invalid request path %s" % self.path)
                return

            # Extract additional query parameters.
            # What they could be is still TBD, may be things like `dry_run=1`?
            parameters = {}
            if parsed.query:
                parameters = urlparse.parse_qs(parsed.query, True, True)
            # Read the body to get the payload.
            content_type = self.headers.getheader("content-type")
            # Check the content type, if not set we assume json.
            # We can have a charset just after the content type, e.g.
            # application/json; charset=UTF-8.
            if content_type and not re.search(r"\s*application/json\s*;?", content_type):
                self.send_error(
                    400,
                    "Invalid content-type %s, it must be 'application/json'" % content_type
                )
                return
            content_len = int(self.headers.getheader("content-length", 0))
            body = self.rfile.read(content_len)
            payload = {}
            if body:
                payload = json.loads(body)

            # Basic routing: extract the synch direction and additional values
            # from the path.
            if direction == "sg2jira":
                if not entity_type or not entity_key:
                    # We need to retrieve this from the payload.
                    entity_type = payload.get("entity_type")
                    entity_key = payload.get("entity_id")
                if not entity_type or not entity_key:
                    self.send_error(
                        400,
                        "Invalid request payload %s, unable to retrieve "
                        "a Shotgun Entity type and its id." % (payload)
                    )
                    return
                # We could have a str or int here depending on how it was sent.
                try: 
                    entity_key = int(entity_key)
                except ValueError:
                    self.send_error(
                        400,
                        "Invalid Shotgun %s id %s, it must be a number." % (
                            entity_type,
                            entity_key,
                        )
                    )
                    return

                self.server.sync_in_jira(
                    settings_name,
                    entity_type,
                    int(entity_key),
                    event=payload,
                    **parameters
                )
            elif direction == "jira2sg":
                if not entity_type or not entity_key:
                    # We can't retrieve this easily from the webhook payload without
                    # hard coding a list of supported resource types, so we require
                    # it to be specified in the path for the time being.
                    self.send_error(
                        400,
                        "Invalid request path %s, it must include a Jira resource "
                        "type and its key" % self.path
                    )
                    return
                # Settings name/Jira Resource type/Jira Resource key.
                self.server.sync_in_shotgun(
                    settings_name,
                    entity_type,
                    entity_key,
                    event=payload,
                    **parameters
                )
            else:
                self.send_error(
                    400,
                    "Invalid request path %s, don't know how to handle %s" % (
                        self.path,
                        direction
                    )
                )
                return
            self.post_response(200, "POST request successful")
        except Exception as e:
            self.send_error(500, e.message)
            logger.debug(e, exc_info=True)

    def log_message(self, format, *args):
        """
        Override :class:`BaseHTTPServer.BaseHTTPRequestHandler` method to use a
        standard logger.

        :param str format: A format string, e.g. '%s %s'.
        :param args: Arbitrary list of arguments to use with the format string.
        """
        message = "%s - %s - %s" % (self.client_address[0], self.path, format % args)
        logger.info(message)

    def log_error(self, format, *args):
        """
        Override :class:`BaseHTTPServer.BaseHTTPRequestHandler` method to use a
        standard logger.

        :param str format: A format string, e.g. '%s %s'.
        :param args: Arbitrary list of arguments to use with the format string.
        """
        message = "%s - %s - %s" % (self.client_address[0], self.path, format % args)
        logger.error(message)


def run_server(port, settings, keyfile=None, certfile=None):
    """
    Run the server until a shutdown is requested.

    :param int port: A port number to listen to.
    :param str settings: Path to settings file.
    :param str keyfile: Optional path to a PEM key file to run in HTTPS mode.
    :param str certfile:  Optional path to a PEM certificate file to run in HTTPS mode.
    """
    httpd = Server(
        settings,
        ("localhost", port), RequestHandler
    )
    if keyfile and certfile:
        # Activate HTTPS.
        httpd.socket = ssl.wrap_socket(
            httpd.socket,
            keyfile=keyfile,
            certfile=certfile,
            server_side=True
        )
    httpd.serve_forever()


def main():
    """
    Retrieve command line arguments and start the server.
    """
    parser = argparse.ArgumentParser(
        description=DESCRIPTION
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9090,
        help="The port number to listen to.",
    )
    parser.add_argument(
        "--settings",
        help="Full path to settings file.",
        required=True
    )
    parser.add_argument(
        "--ssl_context",
        help="A key and certificate file pair to run the server in HTTPS mode.",
        nargs=2,
    )

    args = parser.parse_args()

    keyfile = None
    certfile = None
    if args.ssl_context:
        keyfile, certfile = args.ssl_context

    run_server(
        port=args.port,
        settings=args.settings,
        keyfile=keyfile,
        certfile=certfile,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print "Shutting down..."
