#!/bin/sh
set -eu
mkdir -p /tmp/client_body /tmp/proxy /tmp/fastcgi /tmp/uwsgi /tmp/scgi
exec nginx -g 'daemon off;'
