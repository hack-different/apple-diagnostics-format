# AWDD Log Format
ASN1 encoded custom tags


## Common Tags (root AWDD tags - others added via metadata .bin files)

Here "length prefixed string" means after the tag a variable length integer is encoded specifying the number
of bytes after the integer contain characters in the string.  There is no null terminating byte

* 0x08 - variable length int "timestamp" - unix epoch format
* 0x20 - boolean "anonymous" - at root
* 0x28 - variable length int "deviceConfigId" - commonly 2 bytes
* 0x30 - variable length int "investigationId" - commonly "0"
* 0x3A - length prefixed string - "model"
* 0x42 - length prefixed string - "softwareBuild"
* 0x4A - length prefixed string - "firmwareVersion"
* 0x31 - length prefixed string - "buildtype"
* 0x2D - variable length integer - 2s complement signed
* 0x68 - variable length integer - "metric_file_type" - commonly "1"
* 0x7A - sequence (tag + variable length int for subsequence length) - root node "metrics"

### In the context of a "metrics" sequence (0x7A from above)

* 0x20 - variable length int - timestamp - unix epoch "triggerTime"
* 0x28 - variable length int - "triggerId"
* 0x30 - variable length int - "profileId"

Any tag of over one byte is defined in a metadata file

A metrics will contain N(0..*) subsequences defined by metadata files, each having a tag of over one byte, and
containing a variable length int specifying the subresource length (length_value + length_bytes + tag) == total for tag



# Metadata Files

First 4 bytes are magic value "AWDM"
* uint16_t major
* uint16_t minor
* uint32_t number of bytes in tag (excluding prefix)
* 0x02 - tag header?
* 0x04 - number of fields?
* uint32_t - prefix
* uint32_t - size of header
* uint32_t - size of header table in bytes
* uint32_t - checksum?
* 0x03 - tag dispaly table?
* 0x04 - number of fields?
* uint32_t - prefix
* uint32_t - offset to display table
* uint32_t - size of display table
* uint32_t - checksum?
* 0x04 - tag footer?
* 0x02 - footer fields?
* uint32_t - footer offset
* uint32_t - footer size
* uint32_t - 0x00 reserved?

file size should equal sizeof(header) + sizeof(table) + sizeof(display_table) + sizeof(footer)

## Header Table




## Display Table

Table begins with tag 0x0A - sequence with variable length int for size

each "row" is a 0x12 tagged (variable length encoded) string representing each "row"

### Row format

0x08 - variable length int - tagID (add prefix from header to get tag)
0x10 - subsequence (variable length int encoded) - display info
0x18 - "flags"?
0x22 - display name - string with variable length int encoded length
0x38 - "parent id"?
0x60 - flags?


## Footer

0x0A - tag footer - sequence - variable length int encoded after

0x12 - tag  - bitstring - length encoded after - variable length int - display name

0x18 - tag - timestamp - varaible length int