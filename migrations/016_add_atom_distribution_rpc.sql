-- Function to get atom distribution over time
drop function if exists get_atom_distribution(uuid, text[]);

create or replace function get_atom_distribution(
  query_user_id uuid,
  filter_clusters text[] default null
)
returns table (
  month text,
  count bigint
)
language plpgsql
as $$
begin
  return query
  select
    to_char(date_trunc('month', created_at_source), 'YYYY-MM') as month,
    count(*) as count
  from "Atoms"
  where user_id = query_user_id
  and (
    filter_clusters is null
    or
    cardinality(filter_clusters) = 0
    or
    (metadata->>'cluster_name') = any(filter_clusters)
  )
  group by 1
  order by 1;
end;
$$;
