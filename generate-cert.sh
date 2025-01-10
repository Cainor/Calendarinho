#!/bin/bash
mkdir -p ssl
docker run --rm -v $(pwd)/ssl:/certs alpine/openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /certs/private.key -out /certs/certificate.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
