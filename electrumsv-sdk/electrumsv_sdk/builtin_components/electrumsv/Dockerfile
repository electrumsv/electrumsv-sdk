FROM electrumsvsdk/base_image:latest

# required to flush logs to stdout
ENV PYTHONUNBUFFERED=1

RUN electrumsv-sdk install electrumsv
# now reset to create wallet as part of the build (rather than at runtime)
RUN electrumsv-sdk reset electrumsv
CMD electrumsv-sdk start --inline electrumsv
EXPOSE 9999
