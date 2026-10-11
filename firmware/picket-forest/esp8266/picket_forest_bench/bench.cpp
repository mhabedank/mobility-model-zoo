#include <Arduino.h>


#define TV_STORAGE PROGMEM
#if __has_include("src/picket_forest_v2.h")
/* picket-forest 0.2.0: calibrated features, event decision (feature 010) */
#include "src/picket_forest_v2.h"
#include "src/picket_forest_config.h"
typedef picket_forest_v2_t pf_state_t;
static void pf_init(pf_state_t *p) { picket_forest_v2_init(p); }
static float pf_threshold(void) { return PICKET_FOREST_THRESHOLD; }
static int pf_process(pf_state_t *p, int64_t ts, uint32_t id, uint8_t dlc, const uint8_t *d, float *s)
{
    return picket_forest_v2_process(p, ts, id, dlc, d, s, NULL);
}
#else
#include "src/picket_forest.h"
typedef picket_forest_t pf_state_t;
static void pf_init(pf_state_t *p) { picket_forest_init(p); }
static float pf_threshold(void) { return picket_forest_threshold(); }
static int pf_process(pf_state_t *p, int64_t ts, uint32_t id, uint8_t dlc, const uint8_t *d, float *s)
{
    return picket_forest_process(p, ts, id, dlc, d, s);
}
#endif
#include "src/test_vectors.h"

#ifndef PF_TARGET
#define PF_TARGET "esp8266"
#endif

#ifndef TV_EXPECTED_ALARMS
#define TV_EXPECTED_ALARMS (-1) /* test vectors generated without the alarm stage */
#endif

static pf_state_t s_ids;
static uint32_t s_cycles[TV_N_FRAMES];
static int s_mismatches, s_detected, s_attacks, s_alarms;
static uint32_t s_sum;

static void run_once()
{
    pf_init(&s_ids);
    const float thr = pf_threshold();
    s_mismatches = s_detected = s_attacks = s_alarms = 0;
    for (int i = 0; i < TV_N_FRAMES; i++) {
        tv_frame_t f;
        float expected;
        memcpy_P(&f, &tv_frames[i], sizeof(f));
        memcpy_P(&expected, &tv_expected_score[i], sizeof(expected));
        float s;
        uint32_t t0 = ESP.getCycleCount();
        s_alarms += pf_process(&s_ids, f.ts_us, f.can_id, f.dlc, f.data, &s);
        s_cycles[i] = ESP.getCycleCount() - t0;
        s_mismatches += (s != expected);
        s_attacks += f.label;
        s_detected += f.label && (s >= thr);
        if ((i & 255) == 0) {
            yield(); /* keep the watchdog happy */
        }
    }
}

static int cmp_u32(const void *a, const void *b)
{
    uint32_t x = *(const uint32_t *)a, y = *(const uint32_t *)b;
    return (x > y) - (x < y);
}

void setup()
{
    Serial.begin(115200);
    delay(500);
    run_once(); /* warm-up: fill the flash cache */
    run_once();
    s_sum = 0;
    for (int i = 0; i < TV_N_FRAMES; i++) {
        s_sum += s_cycles[i];
    }
    qsort(s_cycles, TV_N_FRAMES, sizeof(s_cycles[0]), cmp_u32);
}

void loop()
{
    const float mhz = ESP.getCpuFreqMHz();
    Serial.printf("PICKET_FOREST_RESULT {\"target\":\"" PF_TARGET "\",\"cpu_mhz\":%.0f,\"frames\":%d,"
                  "\"score_mismatches\":%d,\"attack_frames\":%d,\"detected\":%d,"
                  "\"alarms\":%d,\"expected_alarms\":%d,"
                  "\"latency_us\":{\"median\":%.2f,\"mean\":%.2f,\"p99\":%.2f,\"max\":%.2f},"
                  "\"state_bytes\":%u,\"free_heap\":%u}\n",
                  mhz, TV_N_FRAMES, s_mismatches, s_attacks, s_detected, s_alarms,
                  TV_EXPECTED_ALARMS,
                  s_cycles[TV_N_FRAMES / 2] / mhz, (float)s_sum / TV_N_FRAMES / mhz,
                  s_cycles[(TV_N_FRAMES * 99) / 100] / mhz, s_cycles[TV_N_FRAMES - 1] / mhz,
                  (unsigned)sizeof(s_ids), (unsigned)ESP.getFreeHeap());
    delay(5000);
}
