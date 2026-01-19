-- Migration 067: Add get_latent_count RPC function
-- This function is a robust way to count atoms whose discovery_epoch_id is in the future
-- compared to the universe's active_epoch_id, directly within the database.

CREATE OR REPLACE FUNCTION get_latent_count(
    p_universe_id UUID,
    p_user_id UUID
)
RETURNS TABLE (
    latent_atom_count BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_active_epoch_id BIGINT;
BEGIN
    -- First, get the active_epoch_id for the given universe, ensuring user ownership
    SELECT u.active_epoch_id INTO v_active_epoch_id
    FROM "Universes" u
    WHERE u.id = p_universe_id AND u.user_id = p_user_id;

    -- If the universe doesn't exist, isn't owned by the user, or has no active epoch, return 0
    IF NOT FOUND OR v_active_epoch_id IS NULL THEN
        RETURN QUERY SELECT 0::BIGINT;
        RETURN;
    END IF;

    -- Count latent atoms: those where discovery_epoch_id is greater than the active epoch
    RETURN QUERY
    SELECT COUNT(a.id)::BIGINT
    FROM "Atoms" a
    WHERE a.universe_id = p_universe_id
      AND a.discovery_epoch_id IS NOT NULL
      AND a.discovery_epoch_id > v_active_epoch_id;
END;
$$;

-- Grant execution rights to the service_role (and any other roles that need it)
GRANT EXECUTE ON FUNCTION get_latent_count(UUID, UUID) TO service_role;
GRANT EXECUTE ON FUNCTION get_latent_count(UUID, UUID) TO authenticated;
