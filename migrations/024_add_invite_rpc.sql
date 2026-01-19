-- Secure RPC to lookup user ID by email
-- SECURITY DEFINER allows this function to access auth.users even if the API role cannot
-- This bridges the gap between public schema and auth schema safely.

CREATE OR REPLACE FUNCTION get_user_id_by_email(user_email TEXT)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  target_user_id UUID;
BEGIN
  SELECT id INTO target_user_id
  FROM auth.users
  WHERE email = user_email;
  
  RETURN target_user_id;
END;
$$;
