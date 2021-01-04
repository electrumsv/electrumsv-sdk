$crtFilePath = ".\config\*.crt"

# import the pfx certificate
Import-PfxCertificate -FilePath $pfxFilePath Cert:\LocalMachine\My -Password $pfxPassword -Exportable

# trust the certificate by importing the pfx certificate into your trusted root
Import-Certificate -FilePath $cerFilePath -CertStoreLocation Cert:\CurrentUser\Root

cp ./config/*.json /app
cd app
dotnet MerchantAPI.APIGateway.Rest.dll