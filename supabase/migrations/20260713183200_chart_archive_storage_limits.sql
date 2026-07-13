-- Bound private chart metadata and JSON snapshots at the database boundary.

alter table public.chart_subjects
  add constraint chart_subjects_birth_place_length
    check (birth_place is null or char_length(birth_place) <= 160),
  add constraint chart_subjects_location_id_length
    check (location_id is null or char_length(location_id) <= 240);

alter table public.metaphysics_charts
  add constraint metaphysics_charts_engine_name_length
    check (char_length(engine_name) <= 80),
  add constraint metaphysics_charts_engine_version_length
    check (char_length(engine_version) <= 40),
  add constraint metaphysics_charts_rules_version_length
    check (char_length(rules_version) <= 80),
  add constraint metaphysics_charts_input_snapshot_size
    check (octet_length(input_snapshot::text) <= 262144),
  add constraint metaphysics_charts_result_snapshot_size
    check (octet_length(result_snapshot::text) <= 2097152);

notify pgrst, 'reload schema';
