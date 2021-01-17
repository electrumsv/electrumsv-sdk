Merchant API
================
This is a wrapper for the Merchant API (a.k.a mAPI) -
https://github.com/bitcoin-sv/merchantapi-reference and is an integral
part in the shifting paradigm toward "true SPV" applications that can
operate efficiently as bitcoin continues to scale.

Unofficial self-contained binaries have been produced for each platform here:
https://github.com/electrumsv/electrumsv-mAPI/releases/tag/0.0.1

So ordinarily a system installation of the dotnet-sdk would NOT be required
as all dependencies are included in the above .zip files.

However, the path of least resistance for setting up and trusting the
SSL certificate is, in my opinion, to use the built-in dotnet-sdk tooling
rather than work out how to replicate it via custom shell scripts.

If you have followed the instructions at:

- :doc:`start command <../getting-started/installing-the-SDK>` documentation

Then you should be ready to go.

Here are the default settings::

    HTTPSPORT=5051
    CERTIFICATEPASSWORD=YourSecurePassword
    CERTIFICATEFILENAME=localhost.pfx

    QUOTE_EXPIRY_MINUTES=10
    ZMQ_CONNECTION_TEST_INTERVAL_SEC=60
    RESTADMIN_APIKEY=apikey
    DELTA_BLOCKHEIGHT_FOR_DOUBLESPENDCHECK=144
    CLEAN_UP_TX_AFTER_DAYS=3
    CLEAN_UP_TX_PERIOD_SEC=3600
    WIF_PRIVATEKEY=Kz4oGtUm2jbJGmDVHgUxgMppaXNUbcfR3myHxvjVWm7zhrCK3LdW
    MINERID_SERVER_URL=
    MINERID_SERVER_ALIAS=
    MINERID_SERVER_AUTHENTICATION=
    NOTIFICATION_NOTIFICATION_INTERVAL_SEC=60
    NOTIFICATION_INSTANT_NOTIFICATION_TASKS=2
    NOTIFICATION_INSTANT_NOTIFICATIONS_QUEUE_SIZE=1000
    NOTIFICATION_MAX_NOTIFICATIONS_IN_BATCH=100
    NOTIFICATION_SLOW_HOST_THRESHOLD_MS=1000
    NOTIFICATION_INSTANT_NOTIFICATIONS_SLOW_TASK_PERCENTAGE=20
    NOTIFICATION_NO_OF_SAVED_EXECUTION_TIMES=10
    NOTIFICATION_NOTIFICATIONS_RETRY_COUNT=10
    NOTIFICATION_SLOW_HOST_RESPONSE_TIMEOUT_MS=1000
    NOTIFICATION_FAST_HOST_RESPONSE_TIMEOUT_MS=2000

These are hard-coded at this time but I am open to requests to make
them modifiable.

NOTE: The ssl certificate password literally IS the string: "YourSecurePassword".
This is hardcoded and your .pfx certificate file must be created with this
as the password. This is not for production use and so is a decision made
to simplify matters as much as possible.

# Usage:

- Make sure you don't forget to add the node to the Merchant API:

