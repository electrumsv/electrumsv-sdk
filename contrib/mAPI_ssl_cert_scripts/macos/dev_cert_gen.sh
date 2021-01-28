#
# To use a different password than the default delete the 'export OPENSSL_PW...' line and set your
# own password for OPENSSL_PW as an environment variable
#
export OPENSSL_PW=YourSecurePassword
touch temp_pw.txt
echo $OPENSSL_PW > temp_pw.txt

echo "Generating certificate for SSL..."
openssl req -config localhost.conf -new -x509 -sha256 -newkey rsa:2048 -nodes -keyout localhost.key -days 3650 -out localhost.crt
openssl pkcs12 -export -out localhost.pfx -inkey localhost.key -in localhost.crt -password pass:$OPENSSL_PW

echo "Trusting the certificate for SSL..."

# Trust the certificate for SSL
mkdir -p $HOME/.pki/nssdb
certutil -d sql:$HOME/.pki/nssdb -N -f temp_pw.txt
pk12util -d sql:$HOME/.pki/nssdb -i localhost.pfx -w temp_pw.txt -k temp_pw.txt
# Trust a self-signed server certificate
certutil -d sql:$HOME/.pki/nssdb -A -t "P,," -n 'dev cert' -i localhost.crt -f temp_pw.txt
rm temp_pw.txt
