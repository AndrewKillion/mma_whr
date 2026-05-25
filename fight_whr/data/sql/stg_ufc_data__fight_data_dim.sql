-- Primary fight extract: staging.stg_ufc_data__fight_data_dim (one row per fight_id).
SELECT
    fighter_a,
    fighter_b,
    fight_date AS date,
    winner,
    _method AS method,
    weightclass
FROM (
    SELECT DISTINCT ON (fight_id)
        fighter_a,
        fighter_b,
        fight_date,
        winner,
        _method,
        weightclass,
        fight_id,
        individual_round
    FROM staging.stg_ufc_data__fight_data_dim
    WHERE fight_date IS NOT NULL
      AND fight_id IS NOT NULL
      AND fighter_a IS NOT NULL
      AND fighter_b IS NOT NULL
      AND winner IN ('A', 'B')
      AND _method IS NOT NULL
      AND _method <> 'OTH'
    ORDER BY fight_id, individual_round DESC
) fights
ORDER BY fight_date;
