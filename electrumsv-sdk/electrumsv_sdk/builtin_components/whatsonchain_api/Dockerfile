FROM electrumsvsdk/base_image:latest

# required to flush logs to stdout
ENV PYTHONUNBUFFERED=1

# settings.conf is modified given environment variables to change the node host to
# host.docker.internal. These are not official environment variable configurations as per
# https://github.com/bitcoin-sv/merchantapi-reference - they are new electrumsv-sdk specific ones.

# These can be overridden by a docker-compose
ENV SERVER_HOST="0.0.0.0"
ENV SERVER_PORT=12121
ENV BITCOIN_NODE_HOST="127.0.0.1"
ENV BITCOIN_NODE_PORT=18332

RUN electrumsv-sdk install whatsonchain_api
ENTRYPOINT electrumsv-sdk start --inline whatsonchain_api
EXPOSE 12121
