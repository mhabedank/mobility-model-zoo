# Bench protocol (version 1)

Line-based over the serial interface (115200 baud, 8N1).

* Host → device: `#<id> <COMMAND> [arg …]\n`
* Device → host: `@{json}\n`. All other lines (bootloader output, crash dumps) are log
  and are stored by the bench in `logs/<board>.log`.
* Every response contains `"id"` (the request ID) and `"ok"`; on errors also `"err"`.
* After every start the device sends `@{"evt":"boot", "fw", "build", "target", "reset_reason", "models"}`.
  If this event arrives while the host is waiting for a response, the host reports an
  **unexpected restart** (`DeviceResetDetected`, e.g. caused by the watchdog, an exception or a
  brown-out) together with the last log lines.

| Command | Response fields |
|---|---|
| `PING` | `pong`, `uptime_ms` |
| `INFO` | `fw`, `proto`, `build`, `target`, `chip`, `uid`, `framework`, `engine`, `cpu_mhz`, `has_cycles`, `free_heap`, `min_free_heap`, `arena`, `line_max`, `models`, `reset_reason`, `uptime_ms`, `inferences` |
| `MODELS` | `models: [{idx, name, in, out, layers, arena, params, macs, crc, tests}]` |
| `INFER <model> <hex>` | `out` (hex, int8), `us`, `cycles`, `in_crc` (CRC32 of the received input) |
| `BENCH <model> [n=10] [warmup=1]` | `n`, `us_min/max/avg/total`, `cyc_min/max/avg`, `macs`, `stable`, `heap_before/after`, `min_free_heap` |
| `SELFTEST <model>` | `passed`, `total`, `first_fail`, `crc_ok`, `us_total` (embedded golden vectors) |
| `VERIFY <model>` | `crc`, `expected`, `match` (CRC of the weights, read from flash), `us` |
| `MEM` | `free_heap`, `min_free_heap`, `arena`, `static_bufs` |
| `ECHO <hex>` | `len`, `data`, `crc` (link test) |
| `RESET` | `resetting`, then restart |

`<model>` is the name or index. Lines longer than `line_max` are rejected with
`{"id":0,"ok":false,"err":"line too long"}`.

Example:

```
#3 INFER can_ids_mlp 00112233…            (32 bytes = 64 hex characters)
@{"id":3,"ok":true,"model":"can_ids_mlp","out":"7f81","us":412,"cycles":32950,"in_crc":"1a2b3c4d"}
```
