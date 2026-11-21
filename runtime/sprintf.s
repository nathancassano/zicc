; Assemble the existing formatter with a bounded RAM output sink
STRING_FORMAT=1
.ifndef CALC
CALC=1
.endif
.export _sprintf, _snprintf
.include "console.s"
