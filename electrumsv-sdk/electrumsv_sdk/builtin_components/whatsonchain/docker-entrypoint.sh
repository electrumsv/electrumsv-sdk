#!/usr/bin/env bash

sleep 4
electrumsv-sdk node --rpchost=host.docker.internal --rpcport=18332 generate 1
electrumsv-sdk start --inline whatsonchain;
