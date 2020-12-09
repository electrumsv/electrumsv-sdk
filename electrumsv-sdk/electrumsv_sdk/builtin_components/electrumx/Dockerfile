FROM electrumsvsdk/base_image:latest

# required to flush logs to stdout
ENV PYTHONUNBUFFERED=1

RUN electrumsv-sdk install electrumx
ENTRYPOINT electrumsv-sdk start --inline electrumx
EXPOSE 51001
