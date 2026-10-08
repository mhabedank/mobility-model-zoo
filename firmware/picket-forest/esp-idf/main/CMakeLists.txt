idf_component_register(SRCS "main.c" "../../c/picket_forest.c"
                       INCLUDE_DIRS "." "../../c" "../../c/generated"
                       REQUIRES can_features esp_timer)
target_compile_options(${COMPONENT_LIB} PRIVATE -O2 -ffp-contract=off)
