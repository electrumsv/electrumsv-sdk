#!/usr/bin/env bash

sleep 4
electrumsv-sdk node --id=node1 generate 1
electrumsv-sdk start --inline whatsonchain;
