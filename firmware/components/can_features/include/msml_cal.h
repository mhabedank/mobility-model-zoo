/*
 * Vehicle-calibrated CAN frame features and event decision (picket-forest 0.2.0, feature 010).
 *
 * A calibration table, learned on the host from benign traffic of one vehicle, describes every
 * known CAN ID: median interval, count window, the largest frame count seen in that window, DLC.
 * msml_cal_update() turns each received frame into MSML_CAL_N_FEATURES features relative to the
 * table; msml_cal_event() applies the event-level decision on top of a model's frame flag.
 *
 * Frame counts use 8 time buckets per ID (window / 8 each): count = frames of the ID in the
 * current and the 7 previous buckets. All times are integer microseconds; ratios are rounded to
 * 1/256 so that host and device give identical values. State: about 40 bytes per table ID plus
 * about 1.6 KB for the bus; no state for unknown IDs.
 */
#ifndef MSML_CAL_H
#define MSML_CAL_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MSML_CAL_N_FEATURES 10
#define MSML_CAL_BUCKETS 8
#define MSML_CAL_W_BUS 256
#define MSML_CAL_W_BUS_LONG 2048
#define MSML_CAL_UNKNOWN_RING 64
#define MSML_CAL_MAX_SPAN_US 2000000
#define MSML_CAL_LOG_CAP 8.0
#ifndef MSML_CAL_MAX_IDS
#define MSML_CAL_MAX_IDS 128
#endif

typedef struct {
    uint32_t id;        /* CAN ID; the table is sorted by id */
    uint32_t period_us; /* median benign interval, 0 if fewer than 5 benign frames */
    uint32_t window_us; /* count window: max(250 ms, 4 periods) */
    uint16_t max_count; /* largest benign count in the window */
    uint8_t dlc;        /* most frequent benign DLC */
} msml_cal_entry_t;

typedef struct {
    const msml_cal_entry_t *entries;
    uint16_t n;
    float bus_rate; /* benign frames per second */
} msml_cal_table_t;

typedef struct {
    int64_t last_us;
    int64_t bucket; /* index of the current bucket (ts_us / (window_us / 8)) */
    uint16_t counts[MSML_CAL_BUCKETS];
    uint8_t data[8];
    uint8_t seen;
    int64_t flag_us[2]; /* last two model flags of this ID (event decision) */
    uint8_t n_flags;
} msml_cal_id_state_t;

typedef struct {
    const msml_cal_table_t *table;
    msml_cal_id_state_t ids[MSML_CAL_MAX_IDS];
    int64_t bus_us[MSML_CAL_W_BUS]; /* timestamps of the last W_BUS frames */
    uint32_t n_frames;
    int64_t unk_us[MSML_CAL_UNKNOWN_RING]; /* last unknown-ID frames: time and frame index */
    uint32_t unk_idx[MSML_CAL_UNKNOWN_RING];
    uint8_t unk_head;
    uint8_t unk_filled;
    int last_entry; /* table index of the last frame, -1 if unknown */
} msml_cal_state_t;

void msml_cal_init(msml_cal_state_t *s, const msml_cal_table_t *table);

/* Features of one frame (in bus order); x receives MSML_CAL_N_FEATURES floats:
 * known_id, log_dt_period, log_count_ratio, count_excess, dlc_changed_cal, hamming, bytes_changed,
 * unknown_count, unknown_count_long, log_bus_rate. */
void msml_cal_update(msml_cal_state_t *s, int64_t ts_us, uint32_t can_id, uint8_t dlc,
                     const uint8_t data[8], float x[MSML_CAL_N_FEATURES]);

/* Event decision for the frame last passed to msml_cal_update: 1 if the frame is flagged.
 * model_flag: the model flagged this frame. confirm: model flags of the ID needed in its window
 * before the episode spreads (1 or 2); margin: the count must exceed the calibrated maximum by
 * this share (0.25 = 25 %). Also flags the fuzzing state (several unknown IDs). */
int msml_cal_event(msml_cal_state_t *s, int64_t ts_us, const float x[MSML_CAL_N_FEATURES],
                   int model_flag, int confirm, double margin);

#ifdef __cplusplus
}
#endif

#endif /* MSML_CAL_H */
