CREATE TABLE "Storylines" (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    universe_id uuid REFERENCES "Universes"(id) ON DELETE CASCADE NOT NULL,
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL, -- Denormalize for RLS
    name text NOT NULL,
    summary text,
    is_active boolean DEFAULT TRUE,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

ALTER TABLE "Storylines" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own storylines" ON "Storylines"
FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own storylines" ON "Storylines"
FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own storylines" ON "Storylines"
FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own storylines" ON "Storylines"
FOR DELETE USING (auth.uid() = user_id);
