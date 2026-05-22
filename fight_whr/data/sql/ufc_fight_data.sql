-- Primary mma-insights fight extract (raw.ufc_fight_data).
-- One row per fight_id (latest round). Ordered by fight_date for WHR time steps.
SELECT fighter_a, fighter_b, fight_date AS date, winner, method, weightclass
FROM (
    SELECT DISTINCT ON (fight_id)
        fighter_a, fighter_b, fight_date, winner, method, weightclass
    FROM raw.ufc_fight_data
    WHERE fight_date IS NOT NULL
      AND fight_id IS NOT NULL
    ORDER BY fight_id, round DESC
) fights
ORDER BY fight_date;
