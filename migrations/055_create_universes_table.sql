CREATE TABLE "Universes" (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    name text NOT NULL,
    description text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

ALTER TABLE "Universes" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own universes" ON "Universes"
FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own universes" ON "Universes"
FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own universes" ON "Universes"
FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own universes" ON "Universes"
FOR DELETE USING (auth.uid() = user_id);

-- Optional: Add a unique constraint on (user_id, name) if universe names must be unique per user
-- ALTER TABLE "Universes" ADD CONSTRAINT unique_user_universe_name UNIQUE (user_id, name);
