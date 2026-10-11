/*
 * Host harness of picket-forest 0.2.0: reads frames from a binary file, writes one float forest
 * score per frame and, if a third path is given, one byte per frame that is 1 where the alarm
 * stage raises an alarm. Record layout (little endian, packed): int64 ts_us, uint16 can_id,
 * uint8 dlc, uint8 data[8]. Used by the parity test and by release gate rules 12/13.
 */
#include <stdio.h>
#include <stdlib.h>

#include "picket_forest_v2.h"

int main(int argc, char **argv)
{
    if (argc != 3 && argc != 4) {
        fprintf(stderr, "usage: %s frames.bin scores.bin [alarms.bin]\n", argv[0]);
        return 2;
    }
    FILE *in = fopen(argv[1], "rb");
    FILE *out = fopen(argv[2], "wb");
    FILE *alarms = argc == 4 ? fopen(argv[3], "wb") : NULL;
    if (in == NULL || out == NULL || (argc == 4 && alarms == NULL)) {
        perror("fopen");
        return 1;
    }
    static picket_forest_v2_t p;
    picket_forest_v2_init(&p);
    unsigned char rec[19];
    while (fread(rec, 1, sizeof(rec), in) == sizeof(rec)) {
        int64_t ts = 0;
        for (int i = 7; i >= 0; i--) {
            ts = (ts << 8) | rec[i];
        }
        uint16_t id = (uint16_t)(rec[8] | (rec[9] << 8));
        float s;
        unsigned char a = (unsigned char)picket_forest_v2_process(&p, ts, id, rec[10], &rec[11], &s, NULL);
        fwrite(&s, sizeof(s), 1, out);
        if (alarms != NULL) {
            fwrite(&a, 1, 1, alarms);
        }
    }
    fclose(in);
    fclose(out);
    if (alarms != NULL) {
        fclose(alarms);
    }
    return 0;
}
