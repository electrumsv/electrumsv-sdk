FROM electrumsvsdk/base_image:latest

RUN electrumsv-sdk install node
ENTRYPOINT electrumsv-sdk start --inline node
EXPOSE 18332
