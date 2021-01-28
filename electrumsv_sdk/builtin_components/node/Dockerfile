FROM electrumsvsdk/base_image:latest

# required to flush logs to stdout
ENV PYTHONUNBUFFERED=1

RUN electrumsv-sdk install node
ENTRYPOINT electrumsv-sdk start --inline node
EXPOSE 18332
