# **Database Schema (Supabase/PostgreSQL)**

This document defines the core data models.

## **1\. Core Tables**

* `Sources` (Unchanged)  
* `Atoms` (Unchanged)  
* `Wikipages` (Unchanged)  
* `Scripts` (Unchanged)  
* `text_chunks` (Unchanged)

## **2\. Relational (Join) Tables**

* `Atoms_to_Sources` (Unchanged)  
* `Scripts_to_Atoms` (Unchanged)

## **3\. NEW: Authentication & Integrations Table**

This new table is required for the OAuth 2.0 flow. It securely stores the credentials needed to act on the user's behalf.

### **`User_Integrations`**

| Column | Type | Description |
| ----- | ----- | ----- |
| `id` | `UUID` | **Primary Key.** |
| `user_id` | `UUID` | **Foreign Key.** Links to `auth.users` table. |
| `service_name` | `TEXT` | **(e.g., "youtube")** Identifies the service. |
| `refresh_token` | `TEXT` | **(Encrypted)** The user's OAuth refresh token. **MUST be encrypted** using `pgsodium` or equivalent before saving. |
| `scopes` | `TEXT[]` | The array of permissions granted (e.g., `["https://www.googleapis.com/auth/youtube.readonly"]`). |
| `created_at` | `TIMESTAMPTZ` | When the integration was first created. |
| `updated_at` | `TIMESTAMPTZ` | When the token was last refreshed or updated. |

**Critical Security Note:** The `refresh_token` is a permanent key to the user's account (within the granted scopes). It must **NEVER** be stored as plaintext. You will use Supabase's `pgsodium` extension to encrypt this field at the database level.

