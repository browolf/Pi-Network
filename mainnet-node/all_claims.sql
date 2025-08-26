WITH exploded AS (
  SELECT
    cb.id                  AS balance_id,
    cb.amount,
    (elem->>'destination') AS destination,
    (elem->'predicate')    AS predicate,
    ord                    AS rn
  FROM claimable_balances cb
  CROSS JOIN LATERAL jsonb_array_elements(cb.claimants) WITH ORDINALITY AS t(elem, ord)
),
filtered AS (
  SELECT
    e.balance_id,
    e.amount,
    e.destination,
    e.predicate
  FROM exploded e
  WHERE e.destination NOT IN (
    'GBIDYJNTVLYWNMA4WCW2DONEDBTVZ7H6EJT6HEOXTWRZ5KMGDGKBVRIL',
    'GC5RNDCRO6DDM7NZDEMW3RIN5K6AHN6GMWSZ5SAH2TRJLVGQMB2I3BNJ',
    'GAZMNERCV4DTWOWARA6QXPPP4U7PZCISSLM4VDMZHRGPDWYCYKSBJ46V'
  )
),
ranked AS (
  SELECT
    f.balance_id,
    f.amount,
    f.destination,
    f.predicate,
    ROW_NUMBER() OVER (PARTITION BY f.balance_id ORDER BY f.destination) AS rn
  FROM filtered f
)
SELECT
  r.balance_id,
  trim(trailing '.' FROM trim(trailing '0'
       FROM ((r.amount::numeric / 10000000)::numeric(38,7))::text)) AS amount_pi,
  MAX(CASE WHEN r.rn = 1 THEN r.destination END) AS c1,
  MAX(CASE WHEN r.rn = 1 THEN
        COALESCE(
          trim(both '"' from (jsonb_path_query_first(r.predicate, '$.**.rel_before'))::text),
          trim(both '"' from (jsonb_path_query_first(r.predicate, '$.**.abs_before_epoch'))::text)
        )
      END) AS c1pred,
  MAX(CASE WHEN r.rn = 2 THEN r.destination END) AS c2,
  MAX(CASE WHEN r.rn = 2 THEN
        COALESCE(
          trim(both '"' from (jsonb_path_query_first(r.predicate, '$.**.rel_before'))::text),
          trim(both '"' from (jsonb_path_query_first(r.predicate, '$.**.abs_before_epoch'))::text)
        )
      END) AS c2pred
FROM ranked r
GROUP BY r.balance_id, r.amount
ORDER BY r.balance_id;
