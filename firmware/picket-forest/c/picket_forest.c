#include "picket_forest.h"

#include "picket_forest_config.h"
#include "picket_forest_model.h"

/* Defaults for configs generated before the alarm stage existed: one alarm per flagged frame,
 * at most one per second. */
#ifndef PICKET_FOREST_ALARM_K
#define PICKET_FOREST_ALARM_K 1
#define PICKET_FOREST_ALARM_WINDOW_US 0
#define PICKET_FOREST_ALARM_HOLDOFF_US 1000000
#endif

void picket_forest_init(picket_forest_t *ids)
{
    msml_can_reset(&ids->features);
    msml_alarm_init(&ids->alarm, PICKET_FOREST_ALARM_K, PICKET_FOREST_ALARM_WINDOW_US,
                    PICKET_FOREST_ALARM_HOLDOFF_US);
}

float picket_forest_score(picket_forest_t *ids, int64_t ts_us, uint32_t can_id, uint8_t dlc,
                         const uint8_t data[8])
{
    float all[MSML_CAN_N_FEATURES];
    float x[PICKET_FOREST_N_INPUTS];
    float proba[2];

    msml_can_update(&ids->features, ts_us, can_id, dlc, data, all);
    for (int i = 0; i < PICKET_FOREST_N_INPUTS; i++) {
        x[i] = all[picket_forest_input_index[i]];
    }
    picket_forest_model_predict_proba(x, PICKET_FOREST_N_INPUTS, proba, 2);
    return proba[1];
}

int picket_forest_process(picket_forest_t *ids, int64_t ts_us, uint32_t can_id, uint8_t dlc,
                         const uint8_t data[8], float *score_out)
{
    const float s = picket_forest_score(ids, ts_us, can_id, dlc, data);
    if (score_out != NULL) {
        *score_out = s;
    }
    return msml_alarm_update(&ids->alarm, ts_us, s >= PICKET_FOREST_THRESHOLD);
}

float picket_forest_threshold(void)
{
    return PICKET_FOREST_THRESHOLD;
}
