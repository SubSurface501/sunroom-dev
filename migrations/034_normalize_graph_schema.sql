-- Migration: 034_normalize_graph_schema.sql
-- Description: Normalizes StoryVolumes JSON graph into Nodes, Edges, and Branches tables for granular control and 'Git for Stories'.

-- 1. Nodes Table (The Narrative Beats)
create table if not exists "Nodes" (
  id uuid primary key default uuid_generate_v4(),
  volume_id uuid references "StoryVolumes"(id) on delete cascade not null,
  
  -- Core Content
  title text not null,
  type text default 'narrative_beat', -- e.g., 'root', 'bottleneck', 'divergence', 'choice'
  content jsonb default '{}'::jsonb,  -- Stores summary, full_text, novelty_score, user_feedback, etc.
  
  -- Context Engine Support
  context_snapshot text, -- A compressed 'Story So Far' summary up to this point. 
                         -- Calculated and stored at creation to speed up future branching.
  
  -- Metadata
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 2. Edges Table (The Connections)
create table if not exists "Edges" (
  id uuid primary key default uuid_generate_v4(),
  volume_id uuid references "StoryVolumes"(id) on delete cascade not null,
  
  source_node_id uuid references "Nodes"(id) on delete cascade not null,
  target_node_id uuid references "Nodes"(id) on delete cascade not null,
  
  type text default 'direct', -- e.g., 'direct', 'causal', 'thematic'
  label text, -- The "Choice Label" (e.g., "Open the Door") displayed on the connection
  
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  
  -- Prevent duplicate edges between same nodes
  unique(source_node_id, target_node_id)
);

-- 3. Branches Table (The Timelines / "Git Branch")
create table if not exists "Branches" (
  id uuid primary key default uuid_generate_v4(),
  volume_id uuid references "StoryVolumes"(id) on delete cascade not null,
  
  name text not null, -- e.g., 'main', 'timeline_b', 'draft_1'
  head_node_id uuid references "Nodes"(id), -- Pointer to the latest node in this branch
  parent_branch_id uuid references "Branches"(id), -- For tracking where a branch diverged from
  divergence_point_node_id uuid references "Nodes"(id), -- The node where the fork happened
  
  is_active boolean default true,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 4. RLS Policies (Inherit from Volume ownership)
alter table "Nodes" enable row level security;
alter table "Edges" enable row level security;
alter table "Branches" enable row level security;

-- Nodes Policy
create policy "Users can view nodes of volumes they can view"
  on "Nodes" for select
  using (
    exists (
      select 1 from "StoryVolumes" v
      where v.id = "Nodes".volume_id
      and (v.user_id = auth.uid() or v.project_id in (select project_id from project_members where user_id = auth.uid()))
    )
  );

create policy "Users can insert nodes to volumes they own/collaborate on"
  on "Nodes" for insert
  with check (
    exists (
      select 1 from "StoryVolumes" v
      where v.id = "Nodes".volume_id
      and (v.user_id = auth.uid() or v.project_id in (select project_id from project_members where user_id = auth.uid()))
    )
  );

-- Edges Policy
create policy "Users can view edges of volumes they can view"
  on "Edges" for select
  using (
    exists (
      select 1 from "StoryVolumes" v
      where v.id = "Edges".volume_id
      and (v.user_id = auth.uid() or v.project_id in (select project_id from project_members where user_id = auth.uid()))
    )
  );

create policy "Users can insert edges to volumes they own/collaborate on"
  on "Edges" for insert
  with check (
    exists (
      select 1 from "StoryVolumes" v
      where v.id = "Edges".volume_id
      and (v.user_id = auth.uid() or v.project_id in (select project_id from project_members where user_id = auth.uid()))
    )
  );

-- Branches Policy
create policy "Users can view branches of volumes they can view"
  on "Branches" for select
  using (
    exists (
      select 1 from "StoryVolumes" v
      where v.id = "Branches".volume_id
      and (v.user_id = auth.uid() or v.project_id in (select project_id from project_members where user_id = auth.uid()))
    )
  );

create policy "Users can modify branches of volumes they own/collaborate on"
  on "Branches" for all
  using (
    exists (
      select 1 from "StoryVolumes" v
      where v.id = "Branches".volume_id
      and (v.user_id = auth.uid() or v.project_id in (select project_id from project_members where user_id = auth.uid()))
    )
  );

-- Indexes for Performance
create index if not exists idx_nodes_volume on "Nodes"(volume_id);
create index if not exists idx_edges_volume on "Edges"(volume_id);
create index if not exists idx_edges_source on "Edges"(source_node_id);
create index if not exists idx_edges_target on "Edges"(target_node_id);
create index if not exists idx_branches_volume on "Branches"(volume_id);
