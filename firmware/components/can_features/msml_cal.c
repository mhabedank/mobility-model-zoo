#include "msml_cal.h"

#include <math.h>
#include <stddef.h>
#include <string.h>

#define MIN_WINDOW_US 250000

static float q_log2(double num, double den)
{
    /* log2(num / den) rounded to 1/256 and clipped to +-LOG_CAP; non-finite -> +LOG_CAP */
    double r = log2(num / den);
    if (!isfinite(r)) {
        return (float)MSML_CAL_LOG_CAP;
    }
    r = floor(r * 256.0 + 0.5) / 256.0;
    if (r > MSML_CAL_LOG_CAP) {
        r = MSML_CAL_LOG_CAP;
    } else if (r < -MSML_CAL_LOG_CAP) {
        r = -MSML_CAL_LOG_CAP;
    }
    return (float)r;
}

static int find(const msml_cal_table_t *t, uint32_t id)
{
    int lo = 0, hi = (int)t->n - 1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        uint32_t v = t->entries[mid].id;
        if (v == id) {
            return mid;
        }
        if (v < id) {
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }
    return -1;
}

void msml_cal_init(msml_cal_state_t *s, const msml_cal_table_t *table)
{
    memset(s, 0, sizeof(*s));
    s->table = table;
    s->last_entry = -1;
}

static int64_t floor_div(int64_t a, int64_t b)
{
    int64_t q = a / b;
    return (a % b != 0 && ((a < 0) != (b < 0))) ? q - 1 : q;
}

static uint32_t unknown_count(const msml_cal_state_t *s, int64_t ts_us, uint32_t window)
{
    /* unknown-ID frames among the last `window` frames (this one included) within MAX_SPAN */
    uint32_t c = 0;
    for (int k = 0; k < s->unk_filled; k++) {
        int i = (s->unk_head + MSML_CAL_UNKNOWN_RING - 1 - k) % MSML_CAL_UNKNOWN_RING;
        if (s->n_frames - s->unk_idx[i] >= window || ts_us - s->unk_us[i] >= MSML_CAL_MAX_SPAN_US) {
            break;
        }
        c++;
    }
    return c;
}

void msml_cal_update(msml_cal_state_t *s, int64_t ts_us, uint32_t can_id, uint8_t dlc,
                     const uint8_t data[8], float x[MSML_CAL_N_FEATURES])
{
    const msml_cal_table_t *t = s->table;
    int e = find(t, can_id);
    s->last_entry = e;
    for (int i = 0; i < MSML_CAL_N_FEATURES; i++) {
        x[i] = 0.0f;
    }
    x[1] = (float)MSML_CAL_LOG_CAP;
    if (e >= 0) {
        const msml_cal_entry_t *c = &t->entries[e];
        msml_cal_id_state_t *st = &s->ids[e];
        x[0] = 1.0f;
        if (st->seen && c->period_us > 0) {
            x[1] = q_log2((double)(ts_us - st->last_us), (double)c->period_us);
        }
        /* bucketed count over the current and the 7 previous buckets */
        const int64_t bw = c->window_us / MSML_CAL_BUCKETS;
        const int64_t b = floor_div(ts_us, bw);
        if (!st->seen) {
            memset(st->counts, 0, sizeof(st->counts));
        } else if (b != st->bucket) {
            int64_t shift = b - st->bucket;
            for (int64_t k = 1; k <= shift && k <= MSML_CAL_BUCKETS; k++) {
                st->counts[(((st->bucket + k) % MSML_CAL_BUCKETS) + MSML_CAL_BUCKETS) % MSML_CAL_BUCKETS] = 0;
            }
        }
        st->bucket = b;
        uint16_t *slot = &st->counts[((b % MSML_CAL_BUCKETS) + MSML_CAL_BUCKETS) % MSML_CAL_BUCKETS];
        if (*slot < 0xFFFF) {
            (*slot)++;
        }
        uint32_t count = 0;
        for (int k = 0; k < MSML_CAL_BUCKETS; k++) {
            count += st->counts[k];
        }
        x[2] = q_log2((double)count + 1.0, (double)c->max_count + 1.0);
        x[3] = (float)((int32_t)count - (int32_t)c->max_count);
        x[4] = dlc != c->dlc ? 1.0f : 0.0f;
        if (st->seen) {
            int ham = 0, changed = 0;
            for (int i = 0; i < 8; i++) {
                uint8_t d = (uint8_t)(data[i] ^ st->data[i]);
                changed += d != 0;
                while (d) {
                    ham += d & 1u;
                    d >>= 1;
                }
            }
            x[5] = (float)ham;
            x[6] = (float)changed;
        }
        memcpy(st->data, data, 8);
        st->last_us = ts_us;
        st->seen = 1;
    } else {
        s->unk_us[s->unk_head] = ts_us;
        s->unk_idx[s->unk_head] = s->n_frames;
        s->unk_head = (uint8_t)((s->unk_head + 1) % MSML_CAL_UNKNOWN_RING);
        if (s->unk_filled < MSML_CAL_UNKNOWN_RING) {
            s->unk_filled++;
        }
    }
    x[7] = (float)unknown_count(s, ts_us, MSML_CAL_W_BUS);
    x[8] = (float)unknown_count(s, ts_us, MSML_CAL_W_BUS_LONG);
    /* bus rate over the last W_BUS frames */
    if (s->n_frames >= MSML_CAL_W_BUS) {
        int64_t back = s->bus_us[s->n_frames % MSML_CAL_W_BUS];
        int64_t span = ts_us - back;
        x[9] = q_log2((double)MSML_CAL_W_BUS * 1e6 / (double)span, (double)t->bus_rate);
    }
    s->bus_us[s->n_frames % MSML_CAL_W_BUS] = ts_us;
    s->n_frames++;
}

int msml_cal_event(msml_cal_state_t *s, int64_t ts_us, const float x[MSML_CAL_N_FEATURES],
                   int model_flag, int confirm, double margin)
{
    int flagged = model_flag ? 1 : 0;
    const int e = s->last_entry;
    if (e >= 0) {
        msml_cal_id_state_t *st = &s->ids[e];
        const int64_t win = (int64_t)s->table->entries[e].window_us;
        if (model_flag) {
            st->flag_us[1] = st->flag_us[0];
            st->flag_us[0] = ts_us;
            if (st->n_flags < 2) {
                st->n_flags++;
            }
        } else {
            const int over = x[3] > 0.0f && (double)x[2] > log2(1.0 + margin);
            int confirmed = st->n_flags >= confirm;
            if (confirmed && confirm >= 2) {
                confirmed = st->flag_us[0] - st->flag_us[1] <= win;
            }
            if (over && confirmed && ts_us - st->flag_us[0] <= win) {
                flagged = 1;
            }
        }
    }
    if (x[7] >= 3.0f || x[8] >= 8.0f) {
        flagged = 1;
    }
    return flagged;
}

#ifdef MSML_CAL_HOST
#include <stdlib.h>

/* Host helper (ctypes): features and, if model_flags is given, event flags for n frames. */
int msml_cal_batch(const msml_cal_entry_t *entries, uint16_t n_entries, float bus_rate,
                   const int64_t *ts_us, const uint32_t *ids, const uint8_t *dlc,
                   const uint8_t *data, size_t n, float *x, const uint8_t *model_flags,
                   int confirm, double margin, uint8_t *event)
{
    msml_cal_table_t table = {entries, n_entries, bus_rate};
    msml_cal_state_t *s = malloc(sizeof(*s));
    if (s == NULL || n_entries > MSML_CAL_MAX_IDS) {
        free(s);
        return 1;
    }
    msml_cal_init(s, &table);
    for (size_t i = 0; i < n; i++) {
        float *xi = &x[i * MSML_CAL_N_FEATURES];
        msml_cal_update(s, ts_us[i], ids[i], dlc[i], &data[i * 8], xi);
        if (model_flags != NULL && event != NULL) {
            event[i] = (uint8_t)msml_cal_event(s, ts_us[i], xi, model_flags[i], confirm, margin);
        }
    }
    free(s);
    return 0;
}
#endif
