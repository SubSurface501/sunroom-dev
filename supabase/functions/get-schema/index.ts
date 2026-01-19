import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { Pool } from "https://deno.land/x/postgres@v0.17.0/mod.ts";

const DATABASE_URL = Deno.env.get("SUPABASE_DB_URL")!;

serve(async (_req) => {
  try {
    const pool = new Pool(DATABASE_URL, 3, true);
    const connection = await pool.connect();
    const result = await connection.queryObject(`
      SELECT
        'CREATE TABLE ' || c.relname || E' (\n' ||
        string_agg(
          '    ' || a.attname || ' ' || pg_catalog.format_type(a.atttypid, a.atttypmod) ||
          CASE WHEN a.attnotnull THEN ' NOT NULL' ELSE '' END ||
          CASE WHEN d.adsrc IS NOT NULL THEN ' DEFAULT ' || d.adsrc ELSE '' END,
          E',\n'
          ORDER BY a.attnum
        ) || E'\n');'
      FROM
        pg_catalog.pg_class c
        JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid
        LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid = c.oid AND d.adnum = a.attnum
      WHERE
        c.relkind = 'r' AND
        c.relnamespace = (SELECT oid FROM pg_catalog.pg_namespace WHERE nspname = 'public') AND
        c.relname = 'waitlist' AND
        a.attnum > 0 AND
        NOT a.attisdropped
      GROUP BY
        c.relname
      ORDER BY
        c.relname;
    `);
    await connection.release();
    return new Response(JSON.stringify(result.rows), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    return new Response(String(err?.message ?? err), { status: 500 });
  }
});