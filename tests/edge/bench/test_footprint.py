"""Model footprint from ELF symbol sizes (feature 021, T031; contracts/records.md "Model footprint")."""

import pytest

from mobility_model_zoo.edge.bench import footprint as fp

# Captured shape of `xtensa-esp32-elf-nm --size-sort -S firmware.elf` (addresses and sizes made up).
NM = """\
3f400010 00000010 r pace_cnn_l3_s
3f400020 00000060 r pace_cnn_l3_m
3f400080 00000180 r pace_cnn_l3_b
3f400200 00000300 R mi_model_pace_cnn
3f400500 00000400 r pace_cnn_layers
3f400900 00001000 r pace_cnn_l0_w
3f401900 00002400 r pace_cnn_test_in
3f402000 00000030 r pace_cnn_test_out
3f403000 00000500 r other_net_l0_w
3f403500 00000040 R mi_model_other_net
400d0000 00000100 t mi_requantize
400d0100 00000800 T mi_invoke
400d0900 00000200 t mi_conv2d
400d0b00 00000080 T mi_crc32_update
400d0b80 00000090 T mi_model_crc32
400d0c00 00000040 t mi_crc_i8_const
3ffb0000 00000008 b mi_scratch
3ffb0010 00000004 d mi_flags
3ffb0100 00002000 B mi_zoo_arena
3ffb2100 00000010 R mi_zoo
400d1000 00000400 T bench_loop
3ffb3000 00000960 b s_line
         00000000 a xtensa.cfg
"""

ARENA, IN, OUT = 4096, 1152, 6


def test_model_footprint_counts_model_data_and_inference_engine():
    syms = fp.parse_nm(NM)
    f = fp.model_footprint(syms, "pace-cnn", ARENA, IN, OUT)
    model = 0x10 + 0x60 + 0x180 + 0x300 + 0x400 + 0x1000 + 0x2400 + 0x30
    engine = 0x100 + 0x800 + 0x200  # CRC helpers, other models, the bench and mi_zoo excluded
    assert f["parts"]["model_constant_data"] == model
    assert f["parts"]["engine_code"] == engine
    assert f["flash_bytes"] == model + engine
    assert f["parts"]["engine_static_data"] == 0x8 + 0x4
    assert f["ram_bytes"] == ARENA + IN + OUT + 0x8 + 0x4


def test_kib_rounds_up_to_a_tenth():
    assert fp.kib(1024) == 1.0
    assert fp.kib(1025) == 1.1
    assert fp.kib(10 * 1024 + 1) == 10.1
    syms = fp.parse_nm(NM)
    f = fp.model_footprint(syms, "pace-cnn", ARENA, IN, OUT)
    assert f["flash_kb"] == fp.kib(f["flash_bytes"]) and f["ram_kb"] == fp.kib(f["ram_bytes"])


def test_missing_model_is_an_error():
    with pytest.raises(ValueError, match="mi_model_pace_cnn"):
        fp.model_footprint(fp.parse_nm("400d0100 00000800 T mi_invoke\n"), "pace-cnn", 1, 1, 1)


def test_nm_tool_only_for_supported_targets(tmp_path, monkeypatch):
    tool = tmp_path / "packages" / "toolchain-xtensa-esp32" / "bin" / "xtensa-esp32-elf-nm"
    tool.parent.mkdir(parents=True)
    tool.write_text("")
    monkeypatch.setenv("PLATFORMIO_CORE_DIR", str(tmp_path))
    assert fp.nm_tool("esp32") == str(tool)
    assert fp.nm_tool(None) is None
    assert fp.nm_tool("rp2040") is None
