#!/bin/bash

# adapted from merchant api src/Deploy/build.sh

read -r VERSIONPREFIX<version_mapi.txt

git remote update
git pull
git status -uno

COMMITID=$(git rev-parse --short HEAD)

APPVERSIONMAPI="$VERSIONPREFIX-$COMMITID"

echo "***************************"
echo "***************************"
echo "Building docker image for MerchantAPI version $APPVERSIONMAPI"

mkdir -p Build

sed s/{{VERSION}}/$VERSIONPREFIX/ < template-docker-compose.yml > Build/docker-compose.yml

cp template.env Build/.env

docker build  --build-arg APPVERSION=$APPVERSIONMAPI -t bitcoinsv/mapi:$VERSIONPREFIX -f ../MerchantAPI/APIGateway/APIGateway.Rest/Dockerfile ..

docker save bitcoinsv/mapi:$VERSIONPREFIX > Build/merchantapiapp.tar
