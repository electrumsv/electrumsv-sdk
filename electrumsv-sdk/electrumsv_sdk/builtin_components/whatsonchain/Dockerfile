FROM electrumsvsdk/base_image:latest

# required to flush logs to stdout
ENV PYTHONUNBUFFERED=1

RUN electrumsv-sdk install whatsonchain

# environment variables will be overridden at runtime if set in docker-compose
ENV RPC_HOST=host.docker.internal
ENV ELECTRUMX_HOST=host.docker.internal

RUN apt-get update && apt-get install -y dos2unix

# RPC request to node to generate a single block for initial state of whatsonchain explorer
COPY docker-entrypoint.sh /
RUN dos2unix /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT [ "/docker-entrypoint.sh"]
EXPOSE 3002
