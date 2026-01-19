# **Vector Search Logic (SQL Functions)**

This file defines the pgvector SQL functions to be created in your Supabase database. These functions are the "power tools" your agents will call via RPC.

**Note:** These functions all rely on Row Level Security (RLS) being enabled and the auth.uid() function being available to secure queries at the database level.

### **1\. get\_rag\_context**

* **Used By:** RetrievalAgent (Step 7\)  
* **Purpose:** To retrieve relevant text chunks from the *entire* library for the ScriptingAgent's "research packet."

CREATE OR REPLACE FUNCTION get\_rag\_context(  
  query\_embedding vector,  
  match\_threshold float,  
  match\_count int  
)  
RETURNS TABLE (content text, source\_id uuid, atom\_id uuid, distance float)  
LANGUAGE sql  
AS $$  
  SELECT  
    text\_chunks.content,  
    text\_chunks.source\_id,  
    text\_chunks.atom\_id,  
    text\_chunks.embedding \<-\> query\_embedding AS distance  
  FROM text\_chunks  
  WHERE  
    text\_chunks.user\_id \= auth.uid()  \-- Enforces RLS  
    AND (text\_chunks.embedding \<-\> query\_embedding) \< match\_threshold  
  ORDER BY  
    distance ASC  
  LIMIT  
    match\_count;  
$$;

### **2\. match\_atoms\_by\_embedding**

* **Used By:** TargetingAgent (Step 5\)  
* **Purpose:** To find the most relevant Atoms that match a user's text query ("Supervised Target").

CREATE OR REPLACE FUNCTION match\_atoms\_by\_embedding(  
  query\_embedding vector,  
  match\_threshold float,  
  match\_count int  
)  
RETURNS TABLE (id uuid, name text, distance float)  
LANGUAGE sql  
AS $$  
  SELECT  
    atoms.id,  
    atoms.name,  
    atoms.embedding \<-\> query\_embedding AS distance  
  FROM atoms  
  WHERE  
    atoms.user\_id \= auth.uid() \-- Enforces RLS  
    AND atoms.status \= 'curated' \-- Only search curated atoms  
    AND (atoms.embedding \<-\> query\_embedding) \< match\_threshold  
  ORDER BY  
    distance ASC  
  LIMIT  
    match\_count;  
$$;

### **3\. get\_cluster\_centroid**

* **Used By:** CartographerAgent & ProspectorAgent (Step 5\)  
* **Purpose:** To calculate the "center point" (average vector) of a "Dense Cluster."

CREATE OR REPLACE FUNCTION get\_cluster\_centroid(  
  atom\_ids uuid\[\]  
)  
RETURNS vector  
LANGUAGE sql  
AS $$  
  SELECT  
    AVG(atoms.embedding)  
  FROM atoms  
  WHERE  
    atoms.user\_id \= auth.uid() \-- Enforces RLS  
    AND atoms.id \= ANY(atom\_ids);  
$$;

### **4\. get\_atom\_distance**

* **Used By:** ProspectorAgent (Step 5\)  
* **Purpose:** A utility to get the semantic distance between two specific Atoms (or centroids).

CREATE OR REPLACE FUNCTION get\_atom\_distance(  
  atom\_a\_id uuid,  
  atom\_b\_id uuid  
)  
RETURNS float  
LANGUAGE sql  
AS $$  
  SELECT  
    a.embedding \<-\> b.embedding AS distance  
  FROM atoms a, atoms b  
  WHERE  
    a.id \= atom\_a\_id AND b.id \= atom\_b\_id  
    AND a.user\_id \= auth.uid() AND b.user\_id \= auth.uid(); \-- Enforces RLS  
$$;  
