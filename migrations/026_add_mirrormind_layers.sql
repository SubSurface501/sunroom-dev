-- 1. SEMANTIC MEMORY (The Narrative)
-- Stores distilled summaries of user thought over time (MirrorMind 2.2.2)
CREATE TABLE IF NOT EXISTS semantic_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    time_window VARCHAR(20) CHECK (time_window IN ('monthly', 'yearly')),
    window_start DATE NOT NULL,
    window_end DATE NOT NULL,
    summary_text TEXT NOT NULL, 
    evolution_insight TEXT, -- "How did thinking shift from the previous window?"
    embedding vector(1536), -- For Semantic Scoping retrieval
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. PERSONA PROFILE (The Cognitive Core)
-- Stores the stable "Voice" and "Mind Map" (MirrorMind 2.2.3)
CREATE TABLE IF NOT EXISTS persona_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    core_concepts JSONB, -- { "entropy": 0.95, "urbanism": 0.82 }
    stylistic_attributes JSONB, -- { "tone": "academic", "reasoning": "inductive" }
    system_prompt_cache TEXT, -- Pre-compiled system prompt to save latency
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_user_profile UNIQUE (user_id)
);

-- 3. DOMAIN CACHE (The External World)
-- Caches external concepts found via OpenAlex so we don't spam their API
CREATE TABLE IF NOT EXISTS domain_concepts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255), -- OpenAlex ID
    concept_name TEXT,
    definition TEXT,
    embedding vector(1536),
    related_concepts JSONB, -- Adjacency list for the external graph
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE semantic_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE persona_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_concepts ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can CRUD their own semantic memories" ON semantic_memories USING (auth.uid() = user_id);
CREATE POLICY "Users can CRUD their own persona profile" ON persona_profiles USING (auth.uid() = user_id);
-- Domain concepts are public/shared reference data, but for now let's allow read for all authenticated
CREATE POLICY "Authenticated users can read domain concepts" ON domain_concepts FOR SELECT USING (auth.role() = 'authenticated');
-- In a real scenario, a service role would write to this. For MVP, allow authenticated users to insert (lazy load triggers)
CREATE POLICY "Authenticated users can insert domain concepts" ON domain_concepts FOR INSERT WITH CHECK (auth.role() = 'authenticated');