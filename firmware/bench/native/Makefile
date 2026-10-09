# Host simulator build (no PlatformIO needed).
#   make -C firmware/native            -> build/edge-sim
#   make -C firmware/native CFLAGS="-O2 -DMI_EXCLUDE_SENSOR_AE"  -> without a model
CC ?= cc
HIL_BUILD_ID ?= 0
OUT ?= build
CFLAGS ?= -O2
override CFLAGS += -std=c99 -Wall -Wextra -Werror -Wshadow -Wconversion -Wno-sign-conversion \
          -I../lib/microinfer/src -I../lib/benchapp/src -I../lib/modelzoo/src \
          -DHIL_BUILD_ID=$(HIL_BUILD_ID)

# The model sources are build output (not committed); `edge build` generates them first, a plain
# `make` generates them here.
PYTHON ?= uv run python
MODELZOO = ../lib/modelzoo/src/model_zoo.c
ifeq ($(wildcard $(MODELZOO)),)
$(info generating firmware model sources)
$(shell cd ../../.. && $(PYTHON) -m mobility_model_zoo.edge.bench.reference_models --ensure >&2)
endif

LIB_SRCS = ../lib/microinfer/src/microinfer.c ../lib/benchapp/src/benchapp.c ../lib/modelzoo/src/model_zoo.c
SRCS = $(LIB_SRCS) hal_native.c main.c

$(OUT)/edge-sim: $(SRCS) $(wildcard ../lib/*/src/*.h) Makefile
	@mkdir -p $(OUT)
	$(CC) $(CFLAGS) -o $@ $(SRCS)

clean:
	rm -rf $(OUT)

.PHONY: clean
