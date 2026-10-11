/*
 * picket-forest 0.2.0: calibrated CAN intrusion detector for microcontrollers.
 *
 * Feed every received CAN frame to picket_forest_v2_process() in bus order. Each frame is turned
 * into features relative to the calibration table of this vehicle (picket_forest_table.h, made on
 * the host from benign traffic). The rules on these features decide (count above the calibrated
 * maximum, several unknown IDs, DLC change); the forest score (share of trees voting "attack") is
 * reported as additional information. Flagged frames pass the alarm stage (PICKET_FOREST_ALARM_K flagged frames within PICKET_FOREST_ALARM_WINDOW_US, then a
 * hold-off). It returns 1 when the frame raises an alarm.
 *
 * Requires the generated files picket_forest_model.h, picket_forest_config.h and
 * picket_forest_table.h (see `security can-ids v2 export` / `v2 table`).
 */
#ifndef PICKET_FOREST_V2_H
#define PICKET_FOREST_V2_H

#include <stdint.h>

#include "msml_alarm.h"
#include "msml_cal.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    msml_cal_state_t cal;
    msml_alarm_t alarm;
} picket_forest_v2_t;

void picket_forest_v2_init(picket_forest_v2_t *p);

/* Process one frame. Returns 1 if this frame raises an alarm. score_out (optional) receives the
 * forest score (information); flag_out (optional) receives the rules decision of this frame. */
int picket_forest_v2_process(picket_forest_v2_t *p, int64_t ts_us, uint32_t can_id, uint8_t dlc,
                             const uint8_t data[8], float *score_out, int *flag_out);

#ifdef __cplusplus
}
#endif

#endif /* PICKET_FOREST_V2_H */
