#include "picket_forest_v2.h"

#include "picket_forest_config.h"
#include "picket_forest_model.h"
#include "picket_forest_table.h"

static const msml_cal_table_t table = {picket_forest_table_entries, PICKET_FOREST_TABLE_N,
                                       PICKET_FOREST_BUS_RATE};

void picket_forest_v2_init(picket_forest_v2_t *p)
{
    msml_cal_init(&p->cal, &table);
    msml_alarm_init(&p->alarm, PICKET_FOREST_ALARM_K, PICKET_FOREST_ALARM_WINDOW_US,
                    PICKET_FOREST_ALARM_HOLDOFF_US);
}

int picket_forest_v2_process(picket_forest_v2_t *p, int64_t ts_us, uint32_t can_id, uint8_t dlc,
                             const uint8_t data[8], float *score_out, int *flag_out)
{
    float x[MSML_CAL_N_FEATURES];
    float proba[2];

    msml_cal_update(&p->cal, ts_us, can_id, dlc, data, x);
    picket_forest_model_predict_proba(x, MSML_CAL_N_FEATURES, proba, 2);
    const int flag = msml_cal_event(&p->cal, ts_us, x, proba[1] >= PICKET_FOREST_THRESHOLD,
                                    PICKET_FOREST_CONFIRM, PICKET_FOREST_MARGIN);
    if (score_out != NULL) {
        *score_out = proba[1];
    }
    if (flag_out != NULL) {
        *flag_out = flag;
    }
    return msml_alarm_update(&p->alarm, ts_us, flag);
}
