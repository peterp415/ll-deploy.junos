# Fix `$9$` SNMP Auth Strings on JunOS

Per [IG-8627](https://butr.avast.com/browse/IG-8627), we were seeing the SNMP user authentication secret data change when re-deploying the same configuration.

To fix this, we should store the password _hashes_ in git and configure with e.g.
`authentication-key <hash>` and `privacy-key <hash>`

1. The first time, set the password with `set ... authentication-password <pw>`

       configure
       set snmp v3 usm local-engine user cacti authentication-sha authentication-password "BETTERNOTTELLYOUNOW"
       set snmp v3 usm local-engine user cacti privacy-aes128 privacy-password "REPLYHAZYTRYAGAIN"
       commit check
       commit comment "Set SNMPv3 auth strings using passwords"

2. Get the device configuration for the encrypted `authentication-key` and `privacy-key`

3. Use http://password-decrypt.com/ (or a script) to decode the `$9$` crypted hash string to get the password hash (JunOS calls this a "key")

4. Set the keys on the device with `set ... authentication-key <hash>` and test

       set snmp v3 usm local-engine user cacti authentication-sha authentication-key "<hash>"
       set snmp v3 usm local-engine user cacti privacy-aes128 privacy-key "<hash>"
       commit comment "Set snmp cacti user auth via keys"

5. Store these last set commands in the git configuration files.

The decrypt result (from `show`) appears to change every time the configuration is updated, but the actual password does stay the same.

## Decrypt Tools

http://password-decrypt.com/ can decode the `$9$` hashed things.

So can Perl (see http://blog.stoked-security.com/2011/06/juniper-9-equivalent-of-cisco-type-7.html):

    #!/usr/bin/perl

    use lib '/some/path/Crypt-Juniper-0.02/lib/'
    Use Crypt::Juniper;

    my $hash = $ARGV[0];
    my $secret = juniper_decrypt($hash);

    print "secret: $secret \n";

Using the script is straight forward:

    $ perl juniper-decrypt.pl \$9\$U-iqf36A1cSTzRSreXxDik.Tzn/CuBI
    secret: ju&iper123

Also there is https://github.com/mhite/junosdecode/blob/master/junosdecode.py
