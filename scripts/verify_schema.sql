\pset pager off
\pset footer on
\echo 'DATABASE'
SELECT current_user, current_database();
\echo 'TABLES'
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('users', 'link_checks', 'link_results', 'user_sessions')
ORDER BY table_name;
\echo 'ENUMS'
SELECT t.typname, string_agg(e.enumlabel, ',' ORDER BY e.enumsortorder) AS labels
FROM pg_type AS t
JOIN pg_enum AS e ON e.enumtypid = t.oid
JOIN pg_namespace AS n ON n.oid = t.typnamespace
WHERE n.nspname = 'public'
  AND t.typname IN ('user_status', 'link_check_status', 'link_element_type', 'link_visibility')
GROUP BY t.typname
ORDER BY t.typname;
\echo 'COLUMNS'
SELECT table_name, column_name, data_type, udt_name, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('users', 'link_checks', 'link_results', 'user_sessions')
ORDER BY table_name, ordinal_position;
\echo 'CONSTRAINTS'
SELECT conrelid::regclass AS table_name, conname, contype,
       pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid::regclass::text IN ('users', 'link_checks', 'link_results', 'user_sessions')
ORDER BY table_name, conname;
\echo 'INDEXES'
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('users', 'link_checks', 'link_results', 'user_sessions')
ORDER BY tablename, indexname;
\echo 'TRIGGERS'
SELECT event_object_table, trigger_name, action_timing, event_manipulation
FROM information_schema.triggers
WHERE trigger_schema = 'public'
  AND event_object_table IN ('users', 'link_checks', 'link_results', 'user_sessions')
ORDER BY event_object_table, trigger_name;
\echo 'ROW COUNTS'
SELECT 'users' AS table_name, count(*) AS row_count FROM users
UNION ALL SELECT 'link_checks', count(*) FROM link_checks
UNION ALL SELECT 'link_results', count(*) FROM link_results
ORDER BY table_name;
