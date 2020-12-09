FROM electrumsvsdk/base_image:latest

RUN electrumsv-sdk install whatsonchain

# environment variables will be overridden at runtime if set in docker-compose
ENV RPC_HOST=host.docker.internal
ENV ELECTRUMX_HOST=host.docker.internal
CMD electrumsv-sdk start --inline whatsonchain
EXPOSE 3002
