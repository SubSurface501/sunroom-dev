-- Update match_atoms to support Date Filtering
drop function if exists match_atoms(vector(768), float, int, text[]);

create or replace function match_atoms (
  query_embedding vector(768),
  match_threshold float,
  match_count int,
  filter_clusters text[] default null,
  filter_start_date timestamp with time zone default null,
  filter_end_date timestamp with time zone default null
)
returns table (
  id uuid,
  name text,
  type text,
  metadata jsonb,
  content text,
  created_at_source timestamp with time zone,
  epoch_label text,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    "Atoms".id,
    "Atoms".name,
    "Atoms".type,
    "Atoms".metadata,
    "Atoms".content,
    "Atoms".created_at_source,
    "Atoms".epoch_label,
    1 - ("Atoms".embedding <=> query_embedding) as similarity
  from "Atoms"
  where 1 - ("Atoms".embedding <=> query_embedding) > match_threshold
  and (
    filter_clusters is null 
    or 
    cardinality(filter_clusters) = 0
    or
    (metadata->>'cluster_name') = any(filter_clusters)
  )
  and (
    filter_start_date is null
    or
    "Atoms".created_at_source >= filter_start_date
  )
  and (
    filter_end_date is null
    or
    "Atoms".created_at_source <= filter_end_date
  )
  order by "Atoms".embedding <=> query_embedding
  limit match_count;
end;
$$;
