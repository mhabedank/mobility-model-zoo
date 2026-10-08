/*
 * picket-forest: frame-level CAN intrusion detector for microcontrollers.
 *
 * Feed every received CAN frame to picket_forest_process() in bus order. It returns 1 when the
 * frame raises an alarm: at least PICKET_FOREST_ALARM_K frames scored above the threshold within
 * PICKET_FOREST_ALARM_WINDOW_US (then alarms are held off for PICKET_FOREST_ALARM_HOLDOFF_US).
 * picket_forest_score() gives the raw per-frame score: the share of trees voting "attack".
 *
 * Requires the generated files picket_forest_model.h and picket_forest_config.h
 * (see `uv run security can-ids forest export`).
 */
#ifndef PICKET_FOREST_H
#define PICKET_FOREST_H

#include <stdint.h>

#include "msml_alarm.h"
#include "msml_can_features.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    msml_can_state_t features;
    msml_alarm_t alarm;
} picket_forest_t;

void picket_forest_init(picket_forest_t *ids);

/* Returns the attack score of this frame (share of trees voting attack). */
float picket_forest_score(picket_forest_t *ids, int64_t ts_us, uint32_t can_id, uint8_t dlc,
                         const uint8_t data[8]);

/* Score the frame and update the alarm stage. Returns 1 if this frame raises an alarm.
 * score_out (optional) receives the frame score. */
int picket_forest_process(picket_forest_t *ids, int64_t ts_us, uint32_t can_id, uint8_t dlc,
                         const uint8_t data[8], float *score_out);

/* Score threshold chosen on validation data. */
float picket_forest_threshold(void);

#ifdef __cplusplus
}
#endif

#endif /* PICKET_FOREST_H */
