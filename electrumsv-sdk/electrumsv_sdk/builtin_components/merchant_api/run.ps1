# This does not work...
#$crtFilePath = ".\config\*.crt"
#Import-PfxCertificate -FilePath $pfxFilePath Cert:\LocalMachine\My -Password $pfxPassword -Exportable
#Import-Certificate -FilePath $cerFilePath -CertStoreLocation Cert:\CurrentUser\Root

cp ./config/*.json /app
cd app
dotnet MerchantAPI.APIGateway.Rest.dll
