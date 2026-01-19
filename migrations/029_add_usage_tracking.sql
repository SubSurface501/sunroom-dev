-- migrations/029_add_usage_tracking.sql

-- 1. Create the Tiers Table
CREATE TABLE IF NOT EXISTS tiers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE, -- 'Archivist', 'Creator', 'Studio'
    price_monthly DECIMAL(10, 2) NOT NULL,
    
    -- Limits (NULL indicates Unlimited)
    doc_ingest_limit INT,               -- Number of files (PDF, MD, CSV)
    audio_video_seconds_limit INT,      -- Total duration in seconds (1 hour = 3600)
    synthesis_generation_limit INT,     -- Number of 'Deep Synthesis' outputs (Volumes)
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Create User Subscriptions (The link between User and Tier)
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE, -- Assuming Supabase auth
    tier_id INT REFERENCES tiers(id),
    
    cycle_start_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    cycle_end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    
    stripe_subscription_id VARCHAR(100), -- For future integration
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id) -- One active sub per user ideally
);

-- 3. Create Usage Logs ( The Ledger )
CREATE TABLE IF NOT EXISTS usage_logs (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    project_id UUID REFERENCES projects(id), -- Optional: track usage per project
    
    activity_type VARCHAR(50) NOT NULL, -- 'INGEST_DOC', 'PROCESS_MEDIA', 'GENERATE_VOLUME'
    quantity_used INT DEFAULT 1,        -- 1 doc, 600 seconds, 1 volume
    
    metadata JSONB DEFAULT '{}',        -- Store filename, duration, tokens used
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Update Sources to support cost calculation
ALTER TABLE "Sources" 
ADD COLUMN IF NOT EXISTS media_duration_seconds INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS file_size_mb DECIMAL(10, 2) DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS is_processed BOOLEAN DEFAULT FALSE;

-- 5. SEED DATA: The Sun Room Pricing Strategy
INSERT INTO tiers (name, price_monthly, doc_ingest_limit, audio_video_seconds_limit, synthesis_generation_limit)
VALUES 
    -- Tier 1: The Archivist ($49/mo, 50 docs, 5 hours audio, 2 outputs)
    ('Archivist', 49.00, 50, 18000, 2),
    
    -- Tier 2: The Creator ($129/mo, Unlimited docs, 20 hours media, 10 outputs)
    ('Creator', 129.00, NULL, 72000, 10),
    
    -- Tier 3: The Studio ($349/mo, Unlimited docs, 60 hours media, Unlimited outputs)
    ('Studio', 349.00, NULL, 216000, NULL)
ON CONFLICT (name) DO NOTHING;