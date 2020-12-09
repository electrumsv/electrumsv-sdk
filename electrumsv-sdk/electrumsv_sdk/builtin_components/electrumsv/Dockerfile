FROM electrumsvsdk/base_image:latest

RUN electrumsv-sdk install electrumsv
# now reset to create wallet as part of the build (rather than at runtime)
RUN electrumsv-sdk reset electrumsv
CMD electrumsv-sdk start --inline electrumsv
EXPOSE 9999
