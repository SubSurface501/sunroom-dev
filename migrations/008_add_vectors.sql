-- Enable pgvector extension
create extension if not exists vector;

-- Add embedding column to Atoms if it doesn't exist
-- We assume 768 dimensions for Gemini text-embedding-004
alter table "Atoms" 
add column if not exists embedding vector(768);

-- Create an index for faster querying (IVFFlat is good for speed/recall balance)
-- Note: Needs sufficient data to be effective, but good to have.
-- We'll use a simple index for now.
create index if not exists atoms_embedding_idx on "Atoms" using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

-- REMOVED: match_atoms function definition (implementing vector search client-side)
