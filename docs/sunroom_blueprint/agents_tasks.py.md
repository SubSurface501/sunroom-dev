import json  
import re  
import os  
import google.generativeai as genai  
from supabase import create\_client, Client  
from celery import Celery  
import numpy as np  
from sklearn.cluster import HDBSCAN  
from pdfminer.high\_level import extract\_text  
import nltk  
import io

\# \--- Google API Imports \---  
from google.oauth2.credentials import Credentials  
from googleapiclient.discovery import build  
from googleapiclient.errors import HttpError  
from googleapiclient.http import MediaIoBaseDownload

\# \--- Local Imports \---  
\# Assumes a 'prompts.py' file is in the same directory  
import prompts

\# \---  
\# CLIENT & APP INITIALIZATION  
\# \---  
SUPABASE\_URL \= os.environ.get("SUPABASE\_URL")  
SUPABASE\_KEY \= os.environ.get("SUPABASE\_SERVICE\_KEY")  
GEMINI\_API\_KEY \= os.environ.get("GEMINI\_API\_KEY")  
CELERY\_BROKER\_URL \= os.environ.get("CELERY\_BROKER\_URL")  
GOOGLE\_CLIENT\_ID \= os.environ.get("GOOGLE\_CLIENT\_ID")  
GOOGLE\_CLIENT\_SECRET \= os.environ.get("GOOGLE\_CLIENT\_SECRET")

\# Initialize Celery App  
app \= Celery('sunroom\_agents', broker=CELERY\_BROKER\_URL)

\# Initialize Supabase Admin Client  
\# This client runs on the backend with full service\_key privileges  
db: Client \= create\_client(SUPABASE\_URL, SUPABASE\_KEY)

\# Initialize Gemini Client  
genai.configure(api\_key=GEMINI\_API\_KEY)  
\# Create persistent model instances  
gemini\_model \= genai.GenerativeModel('gemini-1.5-pro-latest')  
embedding\_model \= genai.GenerativeModel('text-embedding-004') \# Use gemini-2.5-flash-preview-09-2025 ?

\# \---  
\# AGENT HELPER FUNCTIONS  
\# \---

def \_get\_youtube\_service(user\_id: str):  
    """  
    Securely fetches and refreshes a user's OAuth token  
    and returns an authenticated YouTube API service client.  
    """  
    \# 1\. Fetch the encrypted token from the database  
    integration\_data \= db.table("User\_Integrations").select("refresh\_token").eq("user\_id", user\_id).eq("service\_name", "youtube").single().execute().data  
    if not integration\_data:  
        raise Exception("No YouTube integration found for this user.")

    \# 2\. Decrypt the refresh token  
    \# CRITICAL: This requires a Supabase RPC function that uses pgsodium.  
    \# We are assuming \`decrypt\_token\` function exists in your DB.  
    \# encrypted\_token\_bytes \= integration\_data\['refresh\_token'\]  
    \# decrypted\_token \= db.rpc('decrypt\_token', {'token': encrypted\_token\_bytes}).execute().data  
      
    \# \--- Placeholder for decryption \---  
    \# This is insecure and for placeholder logic only.  
    \# Replace with pgsodium RPC call.  
    try:  
        decrypted\_token \= integration\_data\['refresh\_token'\].decode('utf-8')  
    except Exception:  
        decrypted\_token \= integration\_data\['refresh\_token'\]  
    \# \--- End Placeholder \---

    \# 3\. Create Google credentials from the refresh token  
    creds \= Credentials(  
        None, \# No access token, we will refresh  
        refresh\_token=decrypted\_token,  
        token\_uri="https://oauth2.googleapis.com/token",  
        client\_id=GOOGLE\_CLIENT\_ID,  
        client\_secret=GOOGLE\_CLIENT\_SECRET,  
        scopes=\["https://www.googleapis.com/auth/youtube.readonly"\]  
    )  
      
    \# 4\. Refresh the token if it's expired (handled automatically by the client library)  
      
    \# 5\. Build and return the authenticated service  
    return build('youtube', 'v3', credentials=creds)

def \_get\_text\_from\_file(storage\_path: str, user\_id: str) \-\> str:  
    """Downloads a file from Supabase storage and extracts text."""  
    try:  
        \# 1\. Download file from storage  
        \# Note: Bucket name 'sources' is assumed  
        file\_bytes \= db.storage.from\_("sources").download(path=storage\_path)  
          
        \# 2\. Extract text based on file type  
        if storage\_path.lower().endswith('.pdf'):  
            with io.BytesIO(file\_bytes) as pdf\_file:  
                return extract\_text(pdf\_file)  
        elif storage\_path.lower().endswith('.txt'):  
            return file\_bytes.decode('utf-8')  
        else:  
            print(f"Unsupported file type: {storage\_path}")  
            return ""  
    except Exception as e:  
        print(f"Error extracting text from file {storage\_path}: {e}")  
        return ""

def \_find\_atom\_candidates(text: str) \-\> list\[str\]:  
    """Uses NLTK or spaCy to find potential concepts."""  
    \# This is a placeholder. A real implementation would use  
    \# NLTK's part-of-speech tagging and chunking to find  
    \# multi-word noun phrases.  
    \# e.g., nltk.pos\_tag(nltk.word\_tokenize(text))  
      
    \# Simple regex for capitalized phrases (very basic)  
    candidates \= re.findall(r'(\[A-Z\]\[a-z\]+(?:\\s+\[A-Z\]\[a-z\]+)\*)', text)  
    common\_words \= {"like and subscribe", "thanks for watching", "um", "uh"}  
      
    \# Basic filtering  
    filtered \= \[  
        c.strip() for c in candidates   
        if len(c.strip()) \> 3 and c.strip().lower() not in common\_words  
    \]  
    return list(set(filtered)) \# Return unique candidates

def \_chunk\_text(text: str, chunk\_size: int \= 512, overlap: int \= 50\) \-\> list\[str\]:  
    """Breaks text into overlapping chunks for embedding."""  
    \# This uses a simple sliding window  
    chunks \= \[\]  
    start \= 0  
    while start \< len(text):  
        end \= start \+ chunk\_size  
        chunks.append(text\[start:end\])  
        start \+= (chunk\_size \- overlap)  
    return chunks

def \_run\_generative\_model(prompt: str, is\_json: bool \= False) \-\> str:  
    """Helper to run Gemini and handle retries/errors."""  
    try:  
        \# TODO: Implement exponential backoff for 429 errors  
        generation\_config \= {}  
        if is\_json:  
            generation\_config\["response\_mime\_type"\] \= "application/json"  
              
        response \= gemini\_model.generate\_content(  
            prompt,  
            generation\_config=generation\_config  
        )  
        return response.text  
    except Exception as e:  
        print(f"Gemini API error: {e}")  
        return "" \# Return empty string on failure

\# \---  
\# AGENT DEFINITIONS (CELERY TASKS)  
\# \---

\# \--- STAGE 1 & 2: INGESTION & CURATION \---

@app.task(name="batch\_fetch\_transcripts")  
def batch\_fetch\_transcripts(user\_id: str, playlist\_ids: list\[str\] \= None):  
    """  
    MODIFIED: \`TranscriptAgent\` (The API Client)  
    Uses the official YouTube Data API v3 to download transcripts.  
    """  
    try:  
        youtube\_service \= \_get\_youtube\_service(user\_id)  
    except Exception as e:  
        print(f"Failed to get YouTube service for user {user\_id}: {e}")  
        return f"Failed: Could not authenticate user with Google. {e}"

    video\_ids\_to\_fetch \= \[\]  
      
    if playlist\_ids:  
        \# 1\. Get video IDs from all specified playlists  
        for playlist\_id in playlist\_ids:  
            try:  
                next\_page\_token \= None  
                while True:  
                    pl\_request \= youtube\_service.playlistItems().list(  
                        part='contentDetails',  
                        playlistId=playlist\_id,  
                        maxResults=50,  
                        pageToken=next\_page\_token  
                    )  
                    pl\_response \= pl\_request.execute()  
                      
                    video\_ids \= \[item\['contentDetails'\]\['videoId'\] for item in pl\_response.get('items', \[\])\]  
                    video\_ids\_to\_fetch.extend(video\_ids)  
                      
                    next\_page\_token \= pl\_response.get('nextPageToken')  
                    if not next\_page\_token:  
                        break  
            except Exception as e:  
                print(f"Error fetching playlist {playlist\_id}: {e}")  
    else:  
        \# TODO: Add logic to fetch \*all\* videos from user's channel if no playlist is specified  
        print("No playlist IDs provided. Import logic skipped.")

    processed\_count \= 0  
    for video\_id in list(set(video\_ids\_to\_fetch)): \# Process unique IDs  
        try:  
            \# 1\. Get Video Title  
            video\_response \= youtube\_service.videos().list(  
                part="snippet",  
                id=video\_id  
            ).execute()  
              
            if not video\_response.get('items'):  
                print(f"Video {video\_id} not found or private.")  
                continue  
            video\_title \= video\_response\['items'\]\[0\]\['snippet'\]\['title'\]  
              
            \# 2\. Get Caption ID  
            caption\_list \= youtube\_service.captions().list(  
                part="snippet",  
                videoId=video\_id  
            ).execute()  
              
            \# Find the best available caption (e.g., manual 'en' \> ASR 'en')  
            caption\_id \= None  
            best\_caption \= None  
            for item in caption\_list.get('items', \[\]):  
                lang \= item\['snippet'\]\['language'\]  
                kind \= item\['snippet'\]\['trackKind'\]  
                if lang.startswith('en'):  
                    if kind \== 'standard': \# Prefer manual captions  
                        best\_caption \= item  
                        break  
                    elif not best\_caption: \# Fallback to ASR  
                        best\_caption \= item  
              
            if not best\_caption:  
                print(f"No suitable 'en' transcript found for video {video\_id}")  
                continue  
              
            caption\_id \= best\_caption\['id'\]

            \# 3\. Download the Transcript  
            request \= youtube\_service.captions().download(  
                id=caption\_id,  
                tfmt='srt' \# 'srt' or 'vtt' are common text formats  
            )  
              
            fh \= io.BytesIO()  
            downloader \= MediaIoBaseDownload(fh, request)  
            done \= False  
            while done is False:  
                status, done \= downloader.next\_chunk()

            transcript\_text \= fh.getvalue().decode('utf-8')  
              
            \# 4\. Clean the SRT/VTT file (remove timestamps and sequence numbers)  
            cleaned\_text \= re.sub(r'^\\d+\\n', '', transcript\_text, flags=re.MULTILINE)  
            cleaned\_text \= re.sub(r'\\d{2}:\\d{2}:\\d{2},\\d{3} \--\> \\d{2}:\\d{2}:\\d{2},\\d{3}\\n', '', cleaned\_text, flags=re.MULTILINE)  
            cleaned\_text \= re.sub(r'\\n+', ' ', cleaned\_text).strip()

            \# 5\. Create the Source in the DB  
            source\_data \= {  
                "user\_id": user\_id,  
                "title": video\_title,  
                "raw\_text": cleaned\_text,  
                "source\_url": f"https://www.youtube.com/watch?v={video\_id}"  
            }  
            response \= db.table("Sources").insert(source\_data).execute()  
            new\_source\_id \= response.data\[0\]\['id'\]  
              
            \# 6\. Trigger the next agent  
            process\_source.delay(source\_id=new\_source\_id, user\_id=user\_id)  
            processed\_count \+= 1  
              
        except HttpError as e:  
            \# This is a common, non-fatal error  
            if 'captionsDisabled' in str(e):  
                print(f"Captions disabled for video {video\_id}.")  
            else:  
                print(f"HTTP error processing video {video\_id}: {e}")  
        except Exception as e:  
            print(f"General error on video {video\_id}: {e}")  
            pass  
      
    return f"Successfully processed and queued {processed\_count} videos."

@app.task(name="process\_source")  
def process\_source(source\_id: str, user\_id: str):  
    """  
    Agent Workflow: ParserAgent \-\> TokenizerAgent \-\> CullAgent  
    This is the first task in the ingestion assembly line.  
    """  
    try:  
        \# 1\. PARSER AGENT (Logic)  
        source \= db.table("Sources").select("\*").eq("id", source\_id).single().execute().data  
        if not source:  
            print(f"Source {source\_id} not found.")  
            return

        raw\_text \= source.get('raw\_text', '')  
        if source.get('storage\_path') and not raw\_text:  
            raw\_text \= \_get\_text\_from\_file(source\['storage\_path'\], user\_id)  
            db.table("Sources").update({"raw\_text": raw\_text}).eq("id", source\_id).execute()

        \# 2\. TOKENIZER AGENT (Logic)  
        atom\_candidates \= \_find\_atom\_candidates(raw\_text)

        \# 3\. CULL AGENT (Logic)  
        \# Load stop-list (e.g., from a file or DB table)  
        STOP\_LIST \= {"like and subscribe", "thanks for watching", "um", "uh", "click the link", "patreon"}  
        clean\_atoms \= \[name for name in atom\_candidates if name.lower() not in STOP\_LIST\]

        \# Create "Discovered" Atoms and link them to the Source  
        atom\_records \= \[{"name": name, "status": "discovered", "user\_id": user\_id} for name in clean\_atoms\]  
        created\_atoms \= db.table("Atoms").upsert(atom\_records, on\_conflict="name, user\_id").execute().data

        \# Create links  
        atom\_links \= \[{"atom\_id": atom\['id'\], "source\_id": source\_id} for atom in created\_atoms\]  
        db.table("Atoms\_to\_Sources").insert(atom\_links).execute()

        print(f"Source {source\_id} processed. {len(created\_atoms)} atoms discovered.")

    except Exception as e:  
        print(f"Error processing source {source\_id}: {e}")  
        \# Add error logging to DB

@app.task(name="enrich\_atom")  
def enrich\_atom(atom\_id: str, user\_id: str):  
    """  
    Agent: EnrichmentAgent  
    Called by the API when user clicks "Batch Process".  
    """  
    try:  
        atom \= db.table("Atoms").select("name").eq("id", atom\_id).eq("user\_id", user\_id).single().execute().data  
        if not atom:  
            return

        \# 2\. Construct Prompt (from our defined prompt engineering)  
        prompt \= prompts.ENRICHMENT\_PROMPT \+ atom\['name'\]

        \# 3\. Call Gemini API  
        response\_json\_str \= \_run\_generative\_model(prompt, is\_json=True)  
        response\_json \= json.loads(response\_json\_str)

        \# 4\. Save to Wikipage  
        db.table("Wikipages").upsert({  
            "atom\_id": atom\_id,  
            "summary": response\_json.get("summary"),  
            "type": response\_json.get("type")  
        }).execute()

        print(f"Atom {atom\_id} enriched.")

    except Exception as e:  
        print(f"Error enriching atom {atom\_id}: {e}")

@app.task(name="synthesize\_wikipage\_body")  
def synthesize\_wikipage\_body(atom\_id: str, user\_id: str):  
    """  
    Agent: BodySynthesizerAgent  
    Called by the API on \[✨ Synthesize\] button click.  
    """  
    try:  
        \# 1\. Get Atom name  
        atom \= db.table("Atoms").select("name").eq("id", atom\_id).eq("user\_id", user\_id).single().execute().data  
        if not atom:  
            return  
          
        \# 2\. Find all sources that mention this Atom  
        links \= db.table("Atoms\_to\_Sources").select("source\_id").eq("atom\_id", atom\_id).execute().data  
        source\_ids \= \[link\['source\_id'\] for link in links\]  
          
        if not source\_ids:  
            return "No sources found for this atom."  
              
        \# 3\. Get raw text from those sources  
        sources\_text \= db.table("Sources").select("raw\_text").in\_("id", source\_ids).execute().data  
          
        \# 4\. Perform a "pseudo-RAG" to find relevant snippets  
        \# (This is a simplified version. A real RAG would use the \`text\_chunks\` table)  
        full\_text\_corpus \= "\\n\\n".join(\[s\['raw\_text'\] for s in sources\_text\])  
          
        \# (Simplified: just find all sentences mentioning the atom)  
        sentences \= nltk.sent\_tokenize(full\_text\_corpus)  
        context\_snippets \= \[s for s in sentences if re.search(r'\\b' \+ re.escape(atom\['name'\]) \+ r'\\b', s, re.IGNORECASE)\]  
          
        if not context\_snippets:  
            return "No specific mentions found in sources."  
              
        context\_bundle \= "\\n".join(context\_snippets\[:20\]) \# Limit context size  
          
        \# 5\. Call Gemini API  
        prompt \= prompts.BODY\_SYNTHESIZER\_PROMPT.format(  
            topic=atom\['name'\],  
            context=context\_bundle  
        )  
        synthesized\_body \= \_run\_generative\_model(prompt)  
          
        \# 6\. Save to Wikipage body  
        db.table("Wikipages").update({"body": synthesized\_body}).eq("atom\_id", atom\_id).execute()  
          
        print(f"Wikipage body synthesized for Atom {atom\_id}.")  
          
    except Exception as e:  
        print(f"Error synthesizing wikipage body for atom {atom\_id}: {e}")

@app.task(name="index\_atom")  
def index\_atom(atom\_id: str, user\_id: str):  
    """  
    Agent: IndexerAgent  
    Triggered when an Atom's status changes to "curated".  
    """  
    try:  
        \# 1\. Get Atom's Wikipage content  
        wikipage \= db.table("Wikipages").select("summary, body").eq("atom\_id", atom\_id).single().execute().data  
        if not wikipage:  
            return

        atom\_summary \= wikipage.get('summary', '')  
        atom\_body \= wikipage.get('body', '')

        \# 2\. Create and embed chunks for RAG  
        text\_to\_chunk \= f"{atom\_summary}\\n\\n{atom\_body}"  
        text\_chunks \= \_chunk\_text(text\_to\_chunk)  
          
        if not text\_chunks:  
            print(f"No text to chunk for atom {atom\_id}")  
            return

        \# Get embeddings for all chunks in one batch  
        embeddings\_response \= embedding\_model.embed\_content(  
            text\_chunks,   
            task\_type="RETRIEVAL\_DOCUMENT"  
        )  
        chunk\_embeddings \= embeddings\_response\['embedding'\]\['values'\]

        chunk\_records \= \[  
            {  
                "user\_id": user\_id,  
                "atom\_id": atom\_id,  
                "content": chunk,  
                "embedding": embedding  
            } for chunk, embedding in zip(text\_chunks, chunk\_embeddings)  
        \]  
        db.table("text\_chunks").insert(chunk\_records).execute()

        \# 3\. Create and save the main Atom embedding (for discovery)  
        \# We use the summary as the "main" representation  
        atom\_embedding\_response \= embedding\_model.embed\_content(  
            atom\_summary,  
            task\_type="RETRIEVAL\_DOCUMENT"  
        )  
        atom\_embedding \= atom\_embedding\_response\['embedding'\]\['values'\]\[0\]

        db.table("Atoms").update({"embedding": atom\_embedding}).eq("id", atom\_id).execute()

        print(f"Atom {atom\_id} indexed.")  
    except Exception as e:  
        print(f"Error indexing atom {atom\_id}: {e}")

\# \---  
\# \--- STAGE 3: DISCOVERY (PROACTIVE) \---  
\# \---

@app.task(name="run\_proactive\_discovery")  
def run\_proactive\_discovery(user\_id: str):  
    """  
    Agent Workflow: Cartographer \-\> Prospector \-\> Novelty \-\> Trailhead  
    This is the main "discovery" pipeline, run nightly or via a button.  
    """  
    try:  
        \# 1\. CARTOGRAPHER AGENT (Logic)  
        atoms \= db.table("Atoms").select("id, embedding, name").eq("user\_id", user\_id).eq("status", "curated").execute().data  
          
        \# Filter out atoms without embeddings  
        atoms\_with\_embeddings \= \[a for a in atoms if a.get('embedding')\]  
        if len(atoms\_with\_embeddings) \< 10: \# Need enough atoms to cluster  
            print("Not enough curated atoms to run discovery.")  
            return

        embeddings \= np.array(\[atom\['embedding'\] for atom in atoms\_with\_embeddings\])  
          
        \# Run clustering  
        clusterer \= HDBSCAN(min\_cluster\_size=3, min\_samples=1, metric='cosine')  
        labels \= clusterer.fit\_predict(embeddings)

        clusters \= {}  \# {label: \[{"id": atom\_id, "name": atom\_name}, ...\]}  
        outliers \= \[\]  \# \[{"id": atom\_id, "name": atom\_name}, ...\]  
          
        for atom, label in zip(atoms\_with\_embeddings, labels):  
            atom\_info \= {"id": atom\['id'\], "name": atom\['name'\]}  
            if label \== \-1:  
                outliers.append(atom\_info)  
            else:  
                if label not in clusters: clusters\[label\] \= \[\]  
                clusters\[label\].append(atom\_info)

        \# 2\. PROSPECTOR AGENT (Logic)  
        \# Find "Surprising Bridges"  
          
        \# Get cluster centroids  
        cluster\_centroids \= {}  
        for label, atom\_list in clusters.items():  
            cluster\_atom\_ids \= \[a\['id'\] for a in atom\_list\]  
            cluster\_centroids\[label\] \= {  
                "vector": db.rpc("get\_cluster\_centroid", {"atom\_ids": cluster\_atom\_ids}).execute().data,  
                "name": f"Cluster on {atom\_list\[0\]\['name'\]}" \# Simple name  
            }

        \# Find bridges (outliers that connect two distant clusters)  
        bridges \= \[\]  
        for outlier in outliers:  
            outlier\_vec \= db.table("Atoms").select("embedding").eq("id", outlier\['id'\]).single().execute().data\['embedding'\]  
              
            \# Find 2 closest clusters to this outlier  
            distances \= \[\]  
            for label, centroid in cluster\_centroids.items():  
                dist \= np.linalg.norm(np.array(outlier\_vec) \- np.array(centroid\['vector'\])) \# Euclidean distance  
                distances.append((dist, label, centroid\['name'\]))  
              
            distances.sort()  
              
            if len(distances) \< 2:  
                continue  
                  
            cluster\_a\_label \= distances\[0\]\[1\]  
            cluster\_b\_label \= distances\[1\]\[1\]  
              
            \# Check if the two clusters are "far apart"  
            vec\_a \= cluster\_centroids\[cluster\_a\_label\]\['vector'\]  
            vec\_b \= cluster\_centroids\[cluster\_b\_label\]\['vector'\]  
            cluster\_dist \= np.linalg.norm(np.array(vec\_a) \- np.array(vec\_b))  
              
            \# (Heuristic: "Surprising" if clusters are farther apart than outlier is to them)  
            if cluster\_dist \> (distances\[0\]\[0\] \+ distances\[1\]\[0\]):  
                bridges.append({  
                    "outlier\_atom": outlier,  
                    "cluster\_a": cluster\_centroids\[cluster\_a\_label\],  
                    "cluster\_b": cluster\_centroids\[cluster\_b\_label\],  
                    "related\_atom\_ids": \[outlier\['id'\], clusters\[cluster\_a\_label\]\[0\]\['id'\], clusters\[cluster\_b\_label\]\[0\]\['id'\]\] \# Sample IDs  
                })

        \# 3\. TRAILHEAD AGENT (Logic)  
        new\_trailheads \= \[\]  
        for bridge in bridges:  
            prompt\_data \= {  
                "cluster\_1": bridge\['cluster\_a'\]\['name'\],  
                "cluster\_2": bridge\['cluster\_b'\]\['name'\],  
                "bridge\_atom": bridge\['outlier\_atom'\]\['name'\]  
            }  
            prompt \= prompts.TRAILHEAD\_PROMPT \+ json.dumps(prompt\_data)  
              
            response\_json\_str \= \_run\_generative\_model(prompt, is\_json=True)  
            if response\_json\_str:  
                response\_json \= json.loads(response\_json\_str)  
                new\_trailheads.append({  
                    "user\_id": user\_id,  
                    "title": response\_json.get("title"),  
                    "insight": response\_json.get("insight"),  
                    "suggested\_topic": response\_json.get("suggested\_topic"),  
                    "type": "bridge",  
                    "related\_atom\_ids": bridge\['related\_atom\_ids'\]  
                })  
          
        \# TODO: Add logic for NoveltyAgent (scoring dense clusters)  
          
        \# 4\. Save new Trailheads to DB  
        if new\_trailheads:  
            \# Clear old trailheads  
            db.table("Trailheads").delete().eq("user\_id", user\_id).eq("type", "bridge").execute()  
            \# Insert new ones  
            db.table("Trailheads").insert(new\_trailheads).execute()

        print(f"Proactive discovery complete for {user\_id}. Found {len(new\_trailheads)} bridges.")

    except Exception as e:  
        print(f"Error during proactive discovery for {user\_id}: {e}")

\# \---  
\# \--- STAGE 3: SCRIPTING & GENERATION PIPELINE \---  
\# \---

@app.task(name="generate\_script")  
def generate\_script(script\_id: str, user\_id: str, atom\_ids: list\[str\], topic\_name: str):  
    """  
    Agent Workflow: Retrieval \-\> Scripting \-\> Citation  
    This is the main "scripting" pipeline.  
    """  
    try:  
        \# 1\. RETRIEVAL AGENT (Logic)  
          
        \# Get average embedding for the topic  
        atom\_embeddings \= db.table("Atoms").select("embedding").in\_("id", atom\_ids).execute().data  
        topic\_embedding \= np.mean(\[a\['embedding'\] for a in atom\_embeddings\], axis=0).tolist()

        \# Call our SQL function to get RAG context from \`text\_chunks\`  
        rag\_context\_chunks \= db.rpc("get\_rag\_context", {  
            "query\_embedding": topic\_embedding,  
            "match\_threshold": 0.5, \# (Tune this)  
            "match\_count": 25 \# (More context for a full script)  
        }).execute().data

        \# Format context for the prompt, mapping tags to real titles  
        context\_bundle \= ""  
        source\_id\_map \= {} \# {tag: "Full Title"}  
          
        \# Get all source and atom titles in one go  
        all\_source\_ids \= list(set(\[c\['source\_id'\] for c in rag\_context\_chunks if c\['source\_id'\]\]))  
        all\_atom\_ids \= list(set(\[c\['atom\_id'\] for c in rag\_context\_chunks if c\['atom\_id'\]\]))  
          
        sources \= db.table("Sources").select("id, title").in\_("id", all\_source\_ids).execute().data  
        atoms\_db \= db.table("Atoms").select("id, name").in\_("id", all\_atom\_ids).execute().data  
          
        for s in sources: source\_id\_map\[s\['id'\]\] \= s\['title'\]  
        for a in atoms\_db: source\_id\_map\[a\['id'\]\] \= f"Notes on '{a\['name'\]}'"  
          
        for chunk in rag\_context\_chunks:  
            \# Use source\_id or atom\_id as the unique tag  
            tag \= chunk\['source\_id'\] or chunk\['atom\_id'\]  
            if tag in source\_id\_map:  
                context\_bundle \+= f"\[cite: {tag}\] {chunk\['content'\]}\\n\\n"  
              
        if not context\_bundle:  
            raise Exception("No RAG context found for this topic.")

        \# 2\. SCRIPTING AGENT (Logic)  
        script\_prompt \= prompts.SCRIPTING\_PROMPT.format(  
            topic=topic\_name,  
            context=context\_bundle  
        )  
        script\_with\_tags \= \_run\_generative\_model(script\_prompt)

        \# 3\. CITATION AGENT (Logic)  
        \# Replace all machine tags with human-readable titles  
        final\_script \= script\_with\_tags  
        for tag, title in source\_id\_map.items():  
            \# Escape special regex chars in tag (like UUID hyphens)  
            escaped\_tag \= re.escape(str(tag))  
            \# Use a regex to replace to ensure we get the full tag  
            final\_script \= re.sub(  
                r'\\\[cite:\\s\*' \+ escaped\_tag \+ r'\\s\*\\\]',   
                f"\[{title}\]",   
                final\_script  
            )

        \# 4\. Save to Database  
        db.table("Scripts").update({  
            "content": final\_script,  
            "title": topic\_name,  
            "status": "complete"  
        }).eq("id", script\_id).execute()

        print(f"Script {script\_id} generated successfully.")  
      
    except Exception as e:  
        print(f"Error generating script {script\_id}: {e}")  
        db.table("Scripts").update({"status": "failed", "content": str(e)}).eq("id", script\_id).execute()  
