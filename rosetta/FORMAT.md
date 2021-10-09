# Custom TLV encoding


## Tags

Tags are multi-byte integers with the lowest 3 bits being the primal type, while the remaining
bits get shifted right (`>> 3`) to become the "index" from the definition.  This makes the 
"timestamp" value in a log (tag `0x08`) actually type `0x00` and index `0x01` matching up with 
definition from the ambiant root file.  Having a lowest order bit of 0x00 means that the value is
to be interpreted as a multi-byte integer.

Tags that are high in the lowest order bit are length prefixed (common of strings)

* `0x08` index 1 with a type of `0x00` - e.g. "timestamp"
* `0x10` index 2 with a type of `0x00` - PropertyDefinition.Index
* `0x18` index 3 with a type of `0x00` - PropertyDefinition.Flags
* `0x22` index 4 with a type of `0x02` - PropertyDefinition.Name
* `0x0A` index 1 with a type of `0x02` - ObjectDefinition
* `0x12` index 2 with a type of `0x02` - PropertyDefinition

Clearly we demonstrate a primordial integer vs a length prefixed sequence

This implies that type `0x02` is some form of sequence

## Multi-byte integers

The AWDD format can encode multi-byte integers in a format similar to ASN.1
(I'm not yet totally convinced this _isn't_ ASN.1 but hey, when have I ever
done protocols the easy way?).

For a multi-byte integer the high order bit (`0x80`) is set on all bytes which are
not the final byte of the integer.  Once all the bytes of the integer are collected,
the high order bit is masked off, (`& 0x7F`) and the remaining 7 bit bytes are bitstring
concatenated to produce the final integer.  This is complicated as the integer is still
little endian though the encoding uses the most-significant-bit in big-endian format
to determine the `int`'s run length.  The completed algorith is in `decode_variable_length_int`
which returns the int and how many bytes were used to encode it.

This also means for integers <= 127 the integer is the same as a single byte uint8

## Tag, optional length, data

Depending on the type of the value, you will encounter a `tag` (itself a multi-byte `int`)
per the above specification with a direct value, or a length prefixed value.

An example:
If the value type is an int, then a variable length int tag, followed by a variable length int
the value

If the value is a string, then a variable length int tag, followed by a variable length `int` `length`
then the bytes of the string.

## Definitions

The definition table is a collection of `ObjectDefinition`s and `EnumDefinition`s

```python
DEFINE_OBJECT_TAG = 0x0A
DEFINE_ENUM_TAG = 0x12
```

An `ObjectDefinition` is either a Class or an Event - they are broadly equal.
A class will be a collection of property definitions where each
definition is a combination of property name, type (primal), flags, and
extensions.

An object definition is `TAG_CLASS_DEFINITION` followed by a length of the object definition.  It is then parsed as a
a TAG_CLASS_NAME and a series of `TAG_PROPERTY_DEFINITION`s which are a length followed by their fields.

```python
TAG_CLASS_DEFINITION = 0x0A # Name of the class or event
TAG_CLASS_NAME = 0x0A # The string defining the class name (optional)
TAG_PROPERTY_DEFINITION = 0x12 # Repeated for each property
```

In the context of a property flags can be `0x00` in the case of a normal scalar property of `0x01` in the case of a
"multi-property" or a property which can occur multiple times.

```python
# Base Property Types - RE still in progress
class PropertyType(IntEnum):
    UNKNOWN = 0x00
    DOUBLE = 0x01
    FLOAT = 0x02
    INTEGER_64 = 0x03
    INTEGER = 0x04
    UNKNOWN_5 = 0x05
    INTEGER_32 = 0x06
    INTEGER_UNSIGNED = 0x07
    UNKNOWN_8 = 0x08
    UNKNOWN_9 = 0x09
    BOOLEAN = 0x0C
    ENUM = 0x0B
    STRING = 0x0D
    BYTES = 0x0E
    PACKED_UINT_32 = 0x15
    UNKNOWN_17 = 0x11
    UNKNOWN_20 = 0x14
    OBJECT = 0x1B

# Basic Property Values (must occur)
TAG_INDEX = 0x08 # This defines the tag for reference
TAG_TYPE = 0x10 # Primal object type (PropertyType)
TAG_FLAGS = 0x18 # PropertyFalgs
TAG_NAME = 0x22 # The name of the property
```
Various base types have extended type information.  For instance a string
property can have a format type of "UUID" and an integer type can have a value
of "Timestamp".  Each of these is specified by a particular tag on the property
definition.

```python
# Extended or optinal values on a property definition
TAG_OBJECT_REFERENCE = 0x28 # The class of the property in the case of a non-primitive, scalar
TAG_STRING_FORMAT = 0x30 # StringFormat
TAG_LIST_ITEM_TYPE = 0x38 # Type of the element in the case of a collection
TAG_ENUM_INDEX = 0x40 # The EnumDefinition this enum references
TAG_INTEGER_FORMAT = 0x48  # Integer type sub-specifier
TAG_EXTENSION = 0x50 # Set to 0x01 if this property is an extension on another class
TAG_EXTENSION_TARGET = 0x60 # The class to extend
```

### Sub-format Specifiers
```python
class PropertyFlags(IntFlag):
    NONE = 0x00
    REPEATED = 0x01

class IntegerFormat(IntEnum):
    TIMESTAMP = 0x01
    TRIGGER_ID = 0x03
    PROFILE_ID = 0x04
    AVERAGE_TIME = 0x15
    TIME_DELTA = 0x16
    TIMEZONE_OFFSET = 0x17
    ASSOCIATED_TIME = 0x18
    PERIOD_IN_HOURS = 0x19
    TIME_OF_DAY = 0x1E
    SAMPLE_TIMESTAMP = 0x1F
    
class StringFormat(IntEnum):
    UNKNOWN = 0x00
    UUID = 0x01
```


An `EnumDefinition` is a class that defines a range of integer values, which can
be either a selection enumeration or a flags style enumeration.  The definition
will include the textual representation of each value.

# Metadata Files

Metadata files are a MAGIC (`AWDM`), a version (`0xXXXXYYYY`) and N (`0xNNNNNNNN`) regions

If N == 0 then you are reading a root manifest and should read until `tag == 0x00000000`

In all cases there should be a `0x00000000` after the region definitions

Regions fall into two broad categories - tag specific and non-tag specific

Region tags are `0xTTTTFFFF` where `TTTT` is type and `FFFF` is number of `uint32` fields (little endian)

```c
struct {
    uint32 magic, // "AWDM"
    uint16 major, // 0x0100 - little endian 1
    uint16 minor, // 0x0100 - little endian 1
    uint32 regions // either region count or 0
}

// N region entries, see below

struct {
    uint32 zero // = 0x00000000
}
```

## Tag specific

```c
struct {
  uint32 tag,
  uint32 offset,
  uint32 size,
  uint32 checksum // assumed
}
```

### Tag `0x02000400` - Structure Table

This is an import or structure table.  In the case of the root table of the root manifest
the contents are identical to the display or definition table (`0x03000400`).

For metadata manifests which extend the root, this file will broadly import from others
and not define the display names of properties etc.

### Tag `0x03000400` - Definition Table

This table of definitions create new objects with new properties that extend the existing
schema. It will contain object definitions, with property definitions as well as enum
definitions.

This table contains class and object definitions designed to "enrich" the definitions from
the `0x02000400` table with additional data for translation into text format.  

## Non-tag specific

```c
struct {
    uint32 offest
    uint32 size
}
```

### Tag `0x04000200` - File Identity

This region defines two values, the UUID of the file as well as it's display name.

This is analogous to a `LC_UUID` in Mach-O

* `0x0A` - String - File UUID
* `0x12` - String - Source File
* `0x18` - Timestamp - Build Time

### Tag `0x05000200` - Root Object Class Definitions

This defines the root ambient classes.  It's only relevant on the root manifest as
it is the only file to define the root object class.  These classes are used by the
properties on the root object defined by `0x02000400`/`0x03000400` where `tag == 0x00`

### Tag `0x06000200` - Extension Points

This region lists all known extension properties.  These must be loaded from their
assocated constituant extension manifests


# Log Files

