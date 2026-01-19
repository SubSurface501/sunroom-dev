import os  
import httpx  
from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks  
from fastapi.responses import RedirectResponse  
from pydantic import BaseModel, Field  
from typing import List, Optional  
from supabase import create\_client, Client  
from gotrue.models import User  
from celery import Celery

\# Import the task definitions from the agents file  
\# (This assumes api\_server.py and agents/tasks.py are in the same directory/module)  
from agents.tasks import (  
    process\_source,  
    batch\_fetch\_transcripts,  
    enrich\_atom,  
    synthesize\_wikipage\_body,  
    index\_atom,  
    generate\_script,  
    run\_proactive\_discovery  
)  
\# Import the embedding model to be used by the TargetingAgent  
from agents.tasks import embedding\_model, gemini\_model, prompts

\# \---  
\# CONFIGURATION & INITIALIZATION  
\# \---

SUPABASE\_URL \= os.environ.get("SUPABASE\_URL")  
SUPABASE\_KEY \= os.environ.get("SUPABASE\_KEY") \# Use the anon key for client-side auth  
SUPABASE\_SERVICE\_KEY \= os.environ.get("SUPABASE\_SERVICE\_KEY") \# Use service key for admin tasks  
GOOGLE\_CLIENT\_ID \= os.environ.get("GOOGLE\_CLIENT\_ID")  
GOOGLE\_CLIENT\_SECRET \= os.environ.get("GOOGLE\_CLIENT\_SECRET")  
\# This is the \*public\* URL of this API server, for the OAuth callback  
API\_BASE\_URL \= os.environ.get("API\_BASE\_URL", "http://localhost:8000")

app \= FastAPI(title="Sunroom API")

\# Initialize Supabase client  
\# We create a new client for each request to get the user's auth context  
def get\_supabase(request: Request) \-\> Client:  
    token \= request.headers.get("Authorization", "").replace("Bearer ", "")  
    if not token:  
        raise HTTPException(status\_code=401, detail="Missing Authorization header")  
     
    \# Creates a client with the user's token  
    return create\_client(SUPABASE\_URL, SUPABASE\_KEY, options={  
        "headers": {"Authorization": f"Bearer {token}"}  
    })

\# Dependency to get the authenticated user  
async def get\_current\_user(supabase: Client \= Depends(get\_supabase)) \-\> User:  
    try:  
        user\_response \= supabase.auth.get\_user()  
        if not user\_response or not user\_response.user:  
            raise HTTPException(status\_code=401, detail="Invalid authentication credentials")  
        return user\_response.user  
    except Exception:  
        raise HTTPException(status\_code=401, detail="Invalid authentication credentials")

\# Admin client for server-to-server tasks  
supabase\_admin \= create\_client(SUPABASE\_URL, SUPABASE\_SERVICE\_KEY)

\# \---  
\# 1\. AUTHENTICATION & INTEGRATIONS (OAuth 2.0)  
\# \---

@app.get("/api/v1/auth/youtube/start")  
async def auth\_youtube\_start(user: User \= Depends(get\_current\_user)):  
    """  
    Starts the OAuth 2.0 flow.  
    Generates a Google consent URL for the user to visit.  
    """  
    GOOGLE\_AUTH\_URL \= "https://accounts.google.com/o/oauth2/v2/auth"  
    REDIRECT\_URI \= f"{API\_BASE\_URL}/api/v1/auth/youtube/callback"  
    SCOPE \= "https://www.googleapis.com/auth/youtube.readonly"  
     
    auth\_url \= (  
        f"{GOOGLE\_AUTH\_URL}?"  
        f"client\_id={GOOGLE\_CLIENT\_ID}&"  
        f"redirect\_uri={REDIRECT\_URI}&"  
        f"response\_type=code&"  
        f"scope={SCOPE}&"  
        f"access\_type=offline&" \# Ask for a refresh token  
        f"prompt=consent&"  
        f"state={user.id}" \# Pass the user\_id as state  
    )  
    return {"auth\_url": auth\_url}

@app.get("/api/v1/auth/youtube/callback")  
async def auth\_youtube\_callback(state: str, code: str, request: Request):  
    """  
    Handles the redirect back from Google after user consent.  
    Exchanges the 'code' for a 'refresh\_token' and saves it.  
    """  
    user\_id \= state  
    REDIRECT\_URI \= f"{API\_BASE\_URL}/api/v1/auth/youtube/callback"  
    TOKEN\_URL \= "https://oauth2.googleapis.com/token"  
     
    \# 1\. Exchange code for tokens  
    async with httpx.AsyncClient() as client:  
        token\_response \= await client.post(TOKEN\_URL, data={  
            "client\_id": GOOGLE\_CLIENT\_ID,  
            "client\_secret": GOOGLE\_CLIENT\_SECRET,  
            "code": code,  
            "grant\_type": "authorization\_code",  
            "redirect\_uri": REDIRECT\_URI  
        })  
         
    if token\_response.status\_code \!= 200:  
        raise HTTPException(status\_code=400, detail=f"Failed to exchange token: {token\_response.text}")  
         
    token\_data \= token\_response.json()  
    refresh\_token \= token\_data.get("refresh\_token")  
    scopes \= token\_data.get("scope", "").split(" ")  
     
    if not refresh\_token:  
        raise HTTPException(status\_code=400, detail="No refresh token provided. Did you already connect this account?")

    \# 2\. Encrypt the token (CRITICAL)  
    \# Here we call a Supabase RPC function to use pgsodium  
    \# (Assuming you created \`encrypt\_token\` in your migration)  
    \# encrypted\_token\_response \= supabase\_admin.rpc('encrypt\_token', {'token': refresh\_token}).execute()  
    \# encrypted\_token \= encrypted\_token\_response.data  
     
    \# \--- Placeholder for encryption \---  
    \# In a real app, \*NEVER\* store this as plaintext.  
    print("WARNING: Storing refresh token as plaintext. Implement encryption.")  
    encrypted\_token \= refresh\_token.encode('utf-8') \# Placeholder  
    \# \--- End Placeholder \---

    \# 3\. Save to User\_Integrations table  
    (  
        supabase\_admin.table("User\_Integrations")  
        .upsert({  
            "user\_id": user\_id,  
            "service\_name": "youtube",  
            "refresh\_token": encrypted\_token,  
            "scopes": scopes  
        }, on\_conflict="user\_id")  
        .execute()  
    )  
     
    \# 4\. Redirect user back to the frontend settings page  
    \# (This URL should be an env variable)  
    FRONTEND\_SETTINGS\_URL \= os.environ.get("FRONTEND\_URL", "http://localhost:3000") \+ "/settings"  
    return RedirectResponse(FRONTEND\_SETTINGS\_URL)

\# \---  
\# 2\. CORE ENDPOINTS (Sources, Atoms, Wikipages)  
\# \---

class SourceIngest(BaseModel):  
    title: str  
    author: Optional\[str\] \= None  
    source\_url: Optional\[str\] \= None  
    raw\_text: Optional\[str\] \= None  
    file\_upload\_id: Optional\[str\] \= None

@app.post("/api/v1/sources", status\_code=202)  
async def ingest\_source(source: SourceIngest, user: User \= Depends(get\_current\_user)):  
    """  
    Ingests a new source (file or text).  
    Triggers the 'process\_source' agent.  
    """  
    source\_data \= source.dict()  
    source\_data\['user\_id'\] \= user.id  
     
    try:  
        new\_source \= supabase\_admin.table("Sources").insert(source\_data).execute().data\[0\]  
        \# Trigger background agent  
        process\_source.delay(source\_id=new\_source\['id'\], user\_id=user.id)  
        return {"message": "Source ingestion started", "source\_id": new\_source\['id'\]}  
    except Exception as e:  
        raise HTTPException(status\_code=500, detail=str(e))

class YouTubeBatchIngest(BaseModel):  
    playlist\_ids: Optional\[List\[str\]\] \= None

@app.post("/api/v1/sources/youtube\_batch", status\_code=202)  
async def ingest\_youtube\_batch(batch: YouTubeBatchIngest, user: User \= Depends(get\_current\_user)):  
    """  
    Triggers the 'batch\_fetch\_transcripts' agent for the user.  
    """  
    \# 1\. Check if user has a YouTube integration  
    integration \= supabase\_admin.table("User\_Integrations").select("id").eq("user\_id", user.id).eq("service\_name", "youtube").single().execute().data  
    if not integration:  
        raise HTTPException(status\_code=400, detail="No YouTube account connected. Please connect in Settings.")  
         
    \# 2\. Trigger background agent  
    batch\_fetch\_transcripts.delay(user\_id=user.id, playlist\_ids=batch.playlist\_ids)  
    return {"message": "YouTube transcript import started"}

@app.get("/api/v1/atoms")  
async def get\_atoms\_by\_status(status: str, supabase: Client \= Depends(get\_supabase)):  
    """  
    Gets all atoms for the user matching a status (e.g., 'discovered').  
    """  
    if status not in \['discovered', 'curated', 'archived'\]:  
        raise HTTPException(status\_code=400, detail="Invalid status")  
     
    \# RLS policy on the 'Atoms' table handles user\_id matching  
    atoms \= supabase.table("Atoms").select("\*").eq("status", status).execute().data  
    return atoms

class EnrichAtoms(BaseModel):  
    atom\_ids: List\[str\]

@app.post("/api/v1/atoms/enrich", status\_code=202)  
async def enrich\_atoms\_batch(data: EnrichAtoms, user: User \= Depends(get\_current\_user)):  
    """  
    Triggers the 'enrich\_atom' agent for a list of atoms.  
    """  
    for atom\_id in data.atom\_ids:  
        \# TODO: Add check to ensure user owns these atoms  
        enrich\_atom.delay(atom\_id=atom\_id, user\_id=user.id)  
    return {"message": f"Enrichment started for {len(data.atom\_ids)} atoms"}

@app.post("/api/v1/wikipages/{atom\_id}/synthesize\_body", status\_code=202)  
async def synthesize\_body(atom\_id: str, user: User \= Depends(get\_current\_user)):  
    """  
    Triggers the 'synthesize\_wikipage\_body' agent.  
    """  
    \# TODO: Add check to ensure user owns this atom  
    synthesize\_wikipage\_body.delay(atom\_id=atom\_id, user\_id=user.id)  
    return {"message": "Wikipage body synthesis started"}

class WikipageUpdate(BaseModel):  
    summary: str  
    body: Optional\[str\] \= None  
    type: Optional\[str\] \= None

@app.put("/api/v1/wikipages/{atom\_id}", status\_code=200)  
async def update\_wikipage(atom\_id: str, data: WikipageUpdate, user: User \= Depends(get\_current\_user)):  
    """  
    Approves/updates a Wikipage and triggers the 'index\_atom' agent.  
    """  
    \# TODO: Add check to ensure user owns this atom  
    try:  
        \# 1\. Update the Wikipage  
        (  
            supabase\_admin.table("Wikipages")  
            .upsert(data.dict(), on\_conflict="atom\_id")  
            .eq("atom\_id", atom\_id) \# RLS would handle this, but admin client needs explicit check  
            .execute()  
        )  
         
        \# 2\. Update the Atom status to 'curated'  
        supabase\_admin.table("Atoms").update({"status": "curated"}).eq("id", atom\_id).execute()  
         
        \# 3\. Trigger the background indexing agent  
        index\_atom.delay(atom\_id=atom\_id, user\_id=user.id)  
         
        return {"message": "Wikipage approved and indexing started"}  
    except Exception as e:  
        raise HTTPException(status\_code=500, detail=str(e))

\# \---  
\# 3\. DISCOVERY & SCRIPTING ENDPOINTS  
\# \---

@app.get("/api/v1/discovery/trailheads")  
async def get\_trailheads(supabase: Client \= Depends(get\_supabase)):  
    """  
    Fetches the pre-generated 'Natural Trailheads'.  
    """  
    \# This is a simple read, RLS handles security  
    trailheads \= supabase.table("Trailheads").select("\*").order("created\_at", desc=True).limit(20).execute().data  
    return trailheads

@app.get("/api/v1/discovery/search")  
async def search\_supervised\_target(q: str, user: User \= Depends(get\_current\_user)):  
    """  
    This is the 'TargetingAgent' (Synchronous).  
    Finds atoms matching the user's query.  
    """  
    if not q:  
        raise HTTPException(status\_code=400, detail="Query 'q' is required")  
         
    \# 1\. Embed the user's query  
    query\_embedding \= embedding\_model.embed\_content(  
        q,  
        task\_type="RETRIEVAL\_QUERY"  
    )\['embedding'\]\['values'\]  
     
    \# 2\. Call the vector search RPC function  
    matching\_atoms \= supabase\_admin.rpc("match\_atoms\_by\_embedding", {  
        "query\_embedding": query\_embedding,  
        "match\_threshold": 0.5, \# (Tune this value)  
        "match\_count": 5  
    }).execute().data  
     
    \# 3\. Format as a "Trailhead" object  
    atom\_names \= \[a\['name'\] for a in matching\_atoms\]  
    atom\_ids \= \[a\['id'\] for a in matching\_atoms\]  
     
    trailhead \= {  
        "title": f"Research: {q}",  
        "insight": f"Based on your query, here are the top 5 most relevant Atoms from your library: {', '.join(atom\_names)}.",  
        "suggested\_topic": f"A script based on '{q}'.",  
        "type": "target",  
        "related\_atom\_ids": atom\_ids  
    }  
    return \[trailhead\] \# Return as a list to match the UI spec

class ScriptCreate(BaseModel):  
    trailhead\_id: Optional\[str\] \= None  
    atom\_ids: Optional\[List\[str\]\] \= None  
    topic: Optional\[str\] \= None \# For "search" generated scripts

@app.post("/api/v1/scripts", status\_code=202)  
async def create\_script(data: ScriptCreate, user: User \= Depends(get\_current\_user)):  
    """  
    Triggers the 'generate\_script' agent.  
    """  
    if not data.atom\_ids and not data.trailhead\_id:  
        raise HTTPException(status\_code=400, detail="Must provide 'atom\_ids' or 'trailhead\_id'")  
         
    atom\_ids \= data.atom\_ids  
    topic \= data.topic  
     
    if data.trailhead\_id:  
        \# If a trailhead is used, get its atoms and topic  
        trailhead \= supabase\_admin.table("Trailheads").select("related\_atom\_ids, title").eq("id", data.trailhead\_id).single().execute().data  
        atom\_ids \= trailhead\['related\_atom\_ids'\]  
        topic \= trailhead\['title'\]  
         
    \# 1\. Create the placeholder script in the DB  
    new\_script \= supabase\_admin.table("Scripts").insert({  
        "user\_id": user.id,  
        "title": topic or "New Script",  
        "status": "generating"  
    }).execute().data\[0\]  
    script\_id \= new\_script\['id'\]  
     
    \# 2\. Link the atoms to the script  
    links \= \[{"script\_id": script\_id, "atom\_id": atom\_id} for atom\_id in atom\_ids\]  
    supabase\_admin.table("Scripts\_to\_Atoms").insert(links).execute()  
     
    \# 3\. Trigger the background agent  
    generate\_script.delay(  
        script\_id=script\_id,  
        user\_id=user.id,  
        atom\_ids=atom\_ids,  
        topic\_name=topic  
    )  
     
    return {"message": "Script generation started", "script\_id": script\_id}

@app.get("/api/v1/scripts/{script\_id}")  
async def get\_script(script\_id: str, supabase: Client \= Depends(get\_supabase)):  
    """  
    Fetches a script by ID.  
    Used by the UI for polling.  
    """  
    script \= supabase.table("Scripts").select("\*").eq("id", script\_id).single().execute().data  
    if not script:  
        raise HTTPException(status\_code=404, detail="Script not found")  
    return script  
