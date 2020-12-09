FROM electrumsvsdk/base_image:latest

# required to flush logs to stdout
ENV PYTHONUNBUFFERED=1

RUN electrumsv-sdk install whatsonchain

# environment variables will be overridden at runtime if set in docker-compose
ENV RPC_HOST=host.docker.internal
ENV ELECTRUMX_HOST=host.docker.internal

RUN apt-get update && apt-get install -y dos2unix

RUN dos2unix /electrumsv-sdk/electrumsv-sdk/electrumsv_sdk/builtin_components/whatsonchain/docker-entrypoint.sh
RUN chmod +x /electrumsv-sdk/electrumsv-sdk/electrumsv_sdk/builtin_components/whatsonchain/docker-entrypoint.sh
ENTRYPOINT [ "/electrumsv-sdk/electrumsv-sdk/electrumsv_sdk/builtin_components/whatsonchain/docker-entrypoint.sh" ]
EXPOSE 3002
