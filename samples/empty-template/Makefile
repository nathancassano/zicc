ZICC ?= C:/bin/zicc
PYTHON ?= python
export ZICC_COMPILER := $(ZICC)/bin/zicc.exe
export ZICC_RUNTIME_OBJECT_CACHE ?= 0

ifeq ($(OS),Windows_NT)
SHELL := cmd.exe
.SHELLFLAGS := /d /c
endif

.DELETE_ON_ERROR:
sphere.sfc: main.c snes_regs.h Makefile rom-title.txt $(ZICC)/tools/build-rom.py $(ZICC)/bin/zicc.exe $(ZICC)/bin/romtool.exe $(wildcard $(ZICC)/runtime/*.s)
	$(PYTHON) "$(ZICC)/tools/build-rom.py" -o "$@" "$<"
	"$(ZICC)/bin/romtool.exe" "$@" "$@" rom-title.txt
