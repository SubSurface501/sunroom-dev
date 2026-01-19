-- Migration to add Full-Text Search (Sparse Index) to Atoms table

-- 1. Add tsvector column
ALTER TABLE "Atoms" ADD COLUMN IF NOT EXISTS content_search tsvector;

-- 2. Create index for performance
CREATE INDEX IF NOT EXISTS atoms_content_search_idx ON "Atoms" USING GIN (content_search);

-- 3. Create function to update tsvector
CREATE OR REPLACE FUNCTION atoms_tsvector_trigger() RETURNS trigger AS $$
BEGIN
  new.content_search :=
    setweight(to_tsvector('english', coalesce(new.name, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(new.content, '')), 'B');
  return new;
END
$$ LANGUAGE plpgsql;

-- 4. Create trigger
DROP TRIGGER IF EXISTS tsvectorupdate ON "Atoms";
CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
    ON "Atoms" FOR EACH ROW EXECUTE PROCEDURE atoms_tsvector_trigger();

-- 5. Backfill existing data
UPDATE "Atoms" SET content_search =
    setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(content, '')), 'B');

-- 6. RPC for Sparse Search
CREATE OR REPLACE FUNCTION match_atoms_full_text(
    query_text text,
    match_count int,
    filter_user_id uuid DEFAULT NULL,
    filter_project_id uuid DEFAULT NULL
) RETURNS TABLE (
    id uuid,
    name text,
    content text,
    rank float4
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id,
        a.name,
        a.content,
        ts_rank(a.content_search, websearch_to_tsquery('english', query_text))::float4 as rank
    FROM "Atoms" a
    WHERE
        (filter_user_id IS NULL OR a.user_id = filter_user_id)
        -- AND (filter_project_id IS NULL OR ...) -- Project logic omitted for brevity in hybrid MVP
        AND a.content_search @@ websearch_to_tsquery('english', query_text)
    ORDER BY rank DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
