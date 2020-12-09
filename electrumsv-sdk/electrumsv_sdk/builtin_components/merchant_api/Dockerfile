FROM electrumsvsdk/base_image:latest

# required to flush logs to stdout
ENV PYTHONUNBUFFERED=1

# settings.conf is modified given environment variables to change the node host to
# host.docker.internal. These are not official environment variable configurations as per
# https://github.com/bitcoin-sv/merchantapi-reference - they are new electrumsv-sdk specific ones.

# These can be overridden by a docker-compose
ENV NODE_HOST=host.docker.internal
ENV NODE_RPC_PORT=18332
ENV NODE_RPC_USERNAME="rpcuser"
ENV NODE_RPC_PASSWORD="rpcpassword"
ENV NODE_ZMQ_PORT=28332
ENV MERCHANT_API_HOST=0.0.0.0
ENV MERCHANT_API_PORT=45111

RUN electrumsv-sdk install merchant_api
ENTRYPOINT electrumsv-sdk start --inline merchant_api
EXPOSE 45111
EXPOSE 28332
