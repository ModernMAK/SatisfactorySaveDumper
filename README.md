# Satisfactory Save Dumper
A small tool to extract Satisfactories .sav files and dump their contents.

Little to no linting/filtering is done before dumping to json, making it a REALLY bad idea to dump the raw json (long run times/lots of bloat).

It is recommended to convert the dataclasses to dictionaries (using the provided dataclass2safedictionary to support Satisfactory's MapProperty) and then delete keys that aren't required or unimportant.
