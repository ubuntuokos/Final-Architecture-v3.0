ARG BASE_IMAGE
FROM ${BASE_IMAGE}

USER 0
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends squid netcat-openbsd ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /var/spool/squid /var/log/squid \
 && chown -R proxy:proxy /var/spool/squid /var/log/squid
COPY deployment/blackhole/egress/squid.conf /etc/squid/squid.conf
RUN chmod 0444 /etc/squid/squid.conf

USER proxy
EXPOSE 3128
ENTRYPOINT ["/usr/sbin/squid","-N","-f","/etc/squid/squid.conf"]
