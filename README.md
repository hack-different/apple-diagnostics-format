# awdd_decode
Ability to decode Apple Wireless Diagnostics Daemon files

## Hand decoded ASN1 data in `rosetta`

## The metadata for each tag is in the iDevice root FS

`/System/Library/AWD/Metadata`


# Credits

* Rick Mark did a ton of hex editor decoding and created a naieve implementation that worked to decode the initial metadata
* @nicolas17 discovered that the encoding was based on protobuf simplifying the implemntation greatly
