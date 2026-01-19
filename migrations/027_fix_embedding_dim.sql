
ALTER TABLE semantic_memories ALTER COLUMN embedding TYPE vector(768);
ALTER TABLE domain_concepts ALTER COLUMN embedding TYPE vector(768);
